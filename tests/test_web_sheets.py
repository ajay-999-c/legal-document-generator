"""Offline Sheets transport contract, failure behavior, and live-mode UI flows."""
from copy import deepcopy
from html.parser import HTMLParser
import pytest
from fastapi.testclient import TestClient
from web.app import create_app
from web.mock_data import mock_repository
from web.repository import Project, RepositoryError, ConflictError
from web.sheets_repository import SheetsProjectRepository, TABLES, encode


class FakeBook:
    def __init__(self):
        self.sheets = {'Legacy Responses': {'properties': {'title': 'Legacy Responses', 'sheetId': 1,
                       'gridProperties': {'rowCount': 100, 'columnCount': 3}}, 'rows': [['UNCHANGED', '026', '=SUM(A1)']]}}
        self.calls = []
        self.fail_write = False
        self.fail_read = False
        self.apply_then_fail = False

    def fetch_sheet_metadata(self, params=None):
        if self.fail_read:
            raise OSError('private cloud details must not leak')
        names = self.sheets
        if params and params.get('ranges'):
            names = [value.split("'!")[0][1:] for value in params['ranges']]
        result = []
        for name in names:
            sheet = self.sheets[name]
            value = {'properties': deepcopy(sheet['properties'])}
            if params and params.get('includeGridData'):
                value['data'] = [{'startRow': 0, 'rowData': [
                    {'values': [{'userEnteredValue': cell if isinstance(cell, dict) else {'stringValue': cell}} for cell in row]}
                    for row in sheet['rows']]}]
            result.append(value)
        return {'sheets': result}

    def batch_update(self, body):
        self.calls.append(deepcopy(body))
        if self.fail_write:
            raise OSError('private cloud details must not leak')
        for request in body['requests']:
            if 'addSheet' in request:
                props = deepcopy(request['addSheet']['properties'])
                self.sheets[props['title']] = {'properties': props, 'rows': []}
            elif 'updateCells' in request:
                update = request['updateCells']
                target = next(s for s in self.sheets.values() if s['properties']['sheetId'] == update['range']['sheetId'])
                index = update['range']['startRowIndex']
                while len(target['rows']) <= index:
                    target['rows'].append([])
                target['rows'][index] = [c['userEnteredValue']['stringValue'] for c in update['rows'][0]['values']]
            elif 'appendDimension' in request:
                update = request['appendDimension']
                target = next(s for s in self.sheets.values() if s['properties']['sheetId'] == update['sheetId'])
                target['properties']['gridProperties']['rowCount'] += update['length']
        if self.apply_then_fail:
            raise OSError('response lost')
        return {}


@pytest.fixture
def storage():
    book = FakeBook()
    repo = SheetsProjectRepository(lambda: book)
    repo.initialize()
    return book, repo


def test_lazy_startup_and_explicit_initialization():
    book = FakeBook()
    repo = SheetsProjectRepository(lambda: book)
    assert not book.calls
    with pytest.raises(RepositoryError, match='not initialized'):
        repo.list()
    assert not book.calls
    old = deepcopy(book.sheets['Legacy Responses'])
    assert repo.initialize() == list(TABLES)
    assert len(book.calls) == 1
    assert repo.list() == []
    assert repo.initialize() == []
    assert len(book.calls) == 1
    assert book.sheets['Legacy Responses'] == old


def test_roundtrip_restart_and_literal_identifiers(storage):
    book, repo = storage
    project = mock_repository().get('demo')
    project.members['m1']['plot_no'] = '00026/1'
    project.members['m1']['member_name'] = '=NOT_A_FORMULA'
    project.details['completion_certificate_date'] = '2025-01-15'
    repo.save(project)
    assert project.revision
    fresh = SheetsProjectRepository(lambda: book).get('demo')
    assert encode(fresh) == encode(project)
    assert fresh.members['m1']['plot_no'] == '00026/1'
    assert fresh.members['m1']['mobile'] == '0000000001'
    assert book.sheets['Legacy Responses']['rows'] == [['UNCHANGED', '026', '=SUM(A1)']]
    assert all('formulaValue' not in str(call) for call in book.calls)


def test_atomic_aggregate_update_preserves_other_projects(storage):
    book, repo = storage
    first = mock_repository().get('demo')
    repo.save(first)
    second = Project('other', {'project_name': 'Other', 'association_name': 'Other Society'})
    repo.save(second)
    before = encode(repo.get('other'))
    count = len(book.calls)
    project = repo.get('demo')
    project.details['project_name'] = 'Changed'
    project.members['m1']['mobile'] = '0000000000'
    project.committee_members = project.committee_members[1:]
    repo.save(project)
    assert len(book.calls) == count + 1
    assert len({r['updateCells']['range']['sheetId'] for r in book.calls[-1]['requests'] if 'updateCells' in r}) == 3
    assert encode(repo.get('other')) == before
    assert len(repo.get('demo').committee_members) == 4
    assert len(repo.get('demo').members) == 5


def test_optimistic_conflict(storage):
    book, repo = storage
    repo.save(mock_repository().get('demo'))
    old = repo.get('demo')
    new = repo.get('demo')
    new.members['m1']['member_name'] = 'Changed elsewhere'
    repo.save(new)
    count = len(book.calls)
    old.details['project_name'] = 'Stale edit'
    with pytest.raises(ConflictError):
        repo.save(old)
    assert len(book.calls) == count
    assert repo.get('demo').details['project_name'] != 'Stale edit'


def test_simulated_generation_never_writes_sheet(storage):
    book, repo = storage
    repo.save(mock_repository().get('demo'))
    project = repo.get('demo')
    count = len(book.calls)
    project.generated.add('affidavit:m1')
    repo.save(project)
    assert len(book.calls) == count
    assert repo.get('demo').generated == {'affidavit:m1'}
    assert not SheetsProjectRepository(lambda: book).get('demo').generated


@pytest.mark.parametrize('table,mutate', [
    ('UI Projects', lambda rows: rows[0].__setitem__(0, 'wrong_header')),
    ('UI Projects', lambda rows: rows.append(rows[1][:])),
    ('UI Members', lambda rows: rows[1].__setitem__(0, 'missing-project')),
    ('UI Members', lambda rows: rows[1].__setitem__(2, {'formulaValue': '=1+1'})),
    ('UI Members', lambda rows: rows[1].__setitem__(5, {'numberValue': 26})),
    ('UI Committee', lambda rows: rows[1].__setitem__(1, 'missing-member')),
    ('UI Committee', lambda rows: rows[2].__setitem__(2, 'अध्यक्ष')),
    ('UI Committee', lambda rows: rows[2].__setitem__(3, '1')),
])
def test_corrupt_storage_blocks_writes(storage, table, mutate):
    book, repo = storage
    repo.save(mock_repository().get('demo'))
    project = repo.get('demo')
    count = len(book.calls)
    mutate(book.sheets[table]['rows'])
    with pytest.raises(RepositoryError):
        repo.save(project)
    assert len(book.calls) == count


def test_write_failure_not_retried_or_reported_as_success(storage):
    book, repo = storage
    book.fail_write = True
    count = len(book.calls)
    with pytest.raises(RepositoryError, match='may have completed') as exc:
        repo.save(mock_repository().get('demo'))
    assert len(book.calls) == count + 1
    assert 'private' not in str(exc.value)
    assert repo.list() == []


def test_lost_response_does_not_duplicate_project(storage):
    book, repo = storage
    project = mock_repository().get('demo')
    book.apply_then_fail = True
    with pytest.raises(RepositoryError):
        repo.save(project)
    book.apply_then_fail = False
    assert len(repo.list()) == 1
    count = len(book.calls)
    with pytest.raises(ConflictError):
        repo.save(project)
    assert len(book.calls) == count


def test_read_failure_does_not_fall_back_to_mock(storage):
    book, repo = storage
    book.fail_read = True
    with TestClient(create_app(repo)) as client:
        response = client.get('/projects')
        assert response.status_code == 503
        assert 'Sample Gardens' not in response.text
        assert 'private cloud' not in response.text


def test_grows_only_owned_table(storage):
    book, repo = storage
    book.sheets['UI Projects']['properties']['gridProperties']['rowCount'] = 1
    repo.save(Project('one', {'project_name': 'One', 'association_name': 'Society'}))
    assert book.sheets['UI Projects']['properties']['gridProperties']['rowCount'] == 2
    assert book.sheets['Legacy Responses']['properties']['gridProperties']['rowCount'] == 100


def test_sheets_ui_save_conflict_and_generation_forms(storage):
    book, repo = storage
    repo.save(mock_repository().get('demo'))
    with TestClient(create_app(repo)) as client:
        project = repo.get('demo')
        html = client.get('/projects/demo/documents').text
        assert 'GOOGLE SHEETS' in html
        assert f'name="_revision" value="{project.revision}"' in html
        count = len(book.calls)
        assert client.post('/projects/demo/documents/noc/generate', data={'_revision': project.revision}).status_code == 200
        assert len(book.calls) == count
        assert client.post('/projects/demo/details', data=project.details).status_code == 409
        response = client.post('/projects/demo/details', data={**project.details, 'project_name': 'Saved in Sheets', '_revision': project.revision})
        assert response.status_code == 200
        assert repo.get('demo').details['project_name'] == 'Saved in Sheets'
        assert client.post('/projects/demo/details', data={**project.details, '_revision': project.revision}).status_code == 409


def test_sheet_reference_fields_have_revision_and_no_aliases(storage):
    _, repo = storage
    repo.save(mock_repository().get('demo'))
    with TestClient(create_app(repo)) as client:
        for suffix in ('details','members','members/new','members/m1','members/m1/edit','committee','documents'):
            html=client.get('/projects/demo/'+suffix).text
            if suffix == 'members/m1':
                assert '<form method="post"' not in html
            else:
                assert 'name="_revision"' in html
            for forbidden in ('recipient_name','signatory_name','document_date','applicant_name'):
                assert f'name="{forbidden}"' not in html


def test_unified_project_details_save_and_stale_revision(storage):
    from fastapi.testclient import TestClient
    from web.app import create_app
    book, repo = storage
    repo.save(mock_repository().get('demo'))
    before = repo.get('demo')
    data = {**before.details, **before.settings, '_revision': before.revision,
            'project_name': 'Unified project', 'member_count': '11'}
    with TestClient(create_app(repo)) as client:
        assert client.post('/projects/demo/details', data=data).status_code == 200
        after = repo.get('demo')
        assert after.details['project_name'] == 'Unified project'
        assert after.settings['member_count'] == '11'
        assert after.members == before.members
        assert after.committee_members == before.committee_members
        calls = len(book.calls)
        assert client.post('/projects/demo/details', data={**data, 'member_count': '12'}).status_code == 409
        assert len(book.calls) == calls
        assert repo.get('demo').settings['member_count'] == '11'


def test_tehsil_accepts_former_sheet_header_and_preserves_value(storage):
    book, repo = storage
    column = TABLES['UI Projects'].index('tehsil')
    book.sheets['UI Projects']['rows'][0][column] = 'authority_location'
    project = mock_repository().get('demo')
    project.details['tehsil'] = 'राऊ'
    repo.save(project)
    loaded = repo.get(project.project_id)
    assert loaded.details['tehsil'] == 'राऊ'
    assert 'authority_location' not in loaded.details
    assert book.sheets['UI Projects']['rows'][0][column] == 'authority_location'


def test_tehsil_populates_existing_document_placeholders():
    from documents.affidavit import SPEC as affidavit
    from documents.registration import SPEC as registration
    for spec, placeholder in ((affidavit, 'AUTHORITY_LOCATION'), (registration, 'authority_location')):
        values = {field.parameter: 'test' for field in spec.fields}
        values['tehsil'] = 'राऊ'
        assert spec.context_builder(values)[placeholder] == 'राऊ'
        field = next(f for f in spec.fields if f.parameter == 'tehsil')
        assert field.heading == 'Tehsil / तहसील'
        assert 'Authority Location / सक्षम प्राधिकारी का स्थान' in field.aliases
