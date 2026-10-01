"""Offline UI contract and workflows. Fresh mock repository per test."""
from html.parser import HTMLParser
from io import BytesIO
from zipfile import ZipFile
import pytest
from fastapi.testclient import TestClient
from web.app import create_app
from web.mock_data import mock_repository
from web.schema import PROJECT_FIELDS, MEMBER_FIELDS, SETTINGS_FIELDS
from web.services import document_state, president, committee


class Controls(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.controls = []
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        if tag in ('input', 'select', 'textarea'):
            self.controls.append(dict(attrs))


@pytest.fixture
def client():
    with TestClient(create_app()) as client:
        yield client


PAGES = ['/', '/projects', '/projects/new', '/projects/demo', '/projects/demo/details',
         '/projects/demo/members', '/projects/demo/members/new', '/projects/demo/members/m1',
         '/projects/demo/members/m1/edit', '/projects/demo/committee', '/projects/demo/documents']


@pytest.mark.parametrize('path', PAGES)
def test_screens_render(client, path):
    response = client.get(path)
    assert response.status_code == 200
    assert 'Legal Document Manager' in response.text
    assert 'text/html' in response.headers['content-type']


@pytest.mark.parametrize('path', PAGES)
def test_only_certificate_date_and_no_duplicate_person_aliases(client, path):
    controls = Controls(client.get(path).text).controls
    forbidden = {'document_date', 'noc_document_date', 'consent_document_date', 'affidavit_date',
                 'registration_date', 'meeting_date', 'today', 'recipient_name', 'signatory_name',
                 'applicant_name', 'applicant_address', 'registration_no', 'CERT_NO', 'RERA', 'PROJECT'}
    assert not forbidden.intersection(c.get('name') for c in controls)
    assert all(c.get('name') == 'completion_certificate_date' for c in controls if c.get('type') == 'date')
    assert all(c.get('name') == 'completion_certificate_date' for c in controls if 'date' in c.get('name', ''))


def test_canonical_forms_exactly_once(client):
    for path, fields in [('details', (*PROJECT_FIELDS, *SETTINGS_FIELDS)), ('members/m1/edit', MEMBER_FIELDS), ('documents', ())]:
        names = [c.get('name') for c in Controls(client.get('/projects/demo/' + path).text).controls]
        assert set(names) == {f.key for f in fields} | ({'designation'} if path == 'members/m1/edit' else set())
        assert all(names.count(f.key) == 1 for f in fields)
    controls = Controls(client.get('/projects/new').text).controls
    cert = next(c for c in controls if c.get('name') == 'completion_certificate_date')
    assert cert['value'] == ''


def test_committee_references_only_existing_members(client):
    page = client.get('/projects/demo/members').text
    assert '<section id="committee"' in page
    assert '<th scope="col">Designation</th>' in page
    assert 'name="designation"' in page
    assert 'name="designation"' not in client.get('/projects/demo/details').text
    controls = Controls(client.get('/projects/demo/committee').text).controls
    assert {'member_id', 'designation'} <= {c.get('name') for c in controls}
    project = client.app.state.repository.get('demo')
    assert len(project.members) == len(project.committee_members) == 5
    assert all(set(a) == {'member_id', 'designation'} for a in project.committee_members)


def test_search_and_empty_states(client):
    assert 'No projects found' in client.get('/projects?q=missing').text
    assert 'No members found' in client.get('/projects/demo/members?q=missing').text
    assert 'परीक्षण सदस्य एक' in client.get('/projects/demo/members?q=001').text
    # Member search filters the member list; committee controls still list all members.
    assert 'परीक्षण सदस्य दो' not in client.get('/projects/demo/members?q=001').text.split('<section id="committee"')[0]


def test_create_and_update_project(client):
    response = client.post('/projects/new', data={'project_name': 'TEST New', 'association_name': 'TEST Society'})
    assert response.status_code == 200
    project_id = str(response.url).split('/projects/')[1].split('?')[0]
    project = client.app.state.repository.get(project_id)
    assert project.details['completion_certificate_date'] == ''
    assert not project.members
    assert 'Missing Data' in client.get(f'/projects/{project_id}/documents').text
    values = {**project.details, 'completion_certificate_date': '2025-02-30'}
    assert client.post(f'/projects/{project_id}/details', data=values).status_code == 422
    assert client.app.state.repository.get(project_id).details['completion_certificate_date'] == ''
    values['completion_certificate_date'] = '2025-02-28'
    assert client.post(f'/projects/{project_id}/details', data=values).status_code == 200


def test_member_edit_propagates_to_committee_and_signers(client):
    member = client.app.state.repository.get('demo').members['m1']
    response = client.post('/projects/demo/members/m1/edit', data={**member, 'member_name': 'TEST Updated', 'plot_no': '00026'})
    assert response.status_code == 200
    project = client.app.state.repository.get('demo')
    assert president(project) == 'TEST Updated'
    assert committee(project)[0]['plot_no'] == '00026'
    assert 'TEST Updated' in client.get('/projects/demo/details').text
    assert 'Applicant and signatory: <strong>TEST Updated</strong>' in response.text
    assert all(set(a) == {'member_id', 'designation'} for a in project.committee_members)


def test_member_validation_and_add(client):
    assert client.post('/projects/demo/members/new', data={'member_name': 'TEST', 'age': '121'}).status_code == 422
    response = client.post('/projects/demo/members/new', data={'member_name': '<script>TEST</script>', 'age': '30'})
    assert response.status_code == 200
    assert '&lt;script&gt;TEST&lt;/script&gt;' in response.text
    assert len(client.app.state.repository.get('demo').members) == 6
    assert 'Missing Data' in response.text


def test_committee_president_unique_and_members_scoped(client):
    assert client.post('/projects/demo/committee', data={'member_id': 'm2', 'designation': 'अध्यक्ष'}).status_code == 422
    assert client.post('/projects/demo/committee', data={'member_id': 'unknown', 'designation': 'सदस्य'}).status_code == 404
    assert client.post('/projects/demo/committee', data={'member_id': 'm2', 'designation': 'unknown'}).status_code == 422
    client.post('/projects/demo/committee/m1/remove')
    assert client.post('/projects/demo/committee', data={'member_id': 'm2', 'designation': 'अध्यक्ष'}).status_code == 200
    project = client.app.state.repository.get('demo')
    assert president(project) == project.members['m2']['member_name']
    assert 'm1' in project.members
    assert len(project.committee_members) == 4


def test_download_generation_bulk_and_regeneration(client):
    response = client.post('/projects/demo/documents/noc/generate')
    assert response.headers['content-disposition'].startswith('attachment;')
    assert 'word/document.xml' in ZipFile(BytesIO(response.content)).namelist()
    assert 'Regenerate' in client.get('/projects/demo/documents').text
    assert client.app.state.repository.get('demo').generated == {'noc'}
    client.post('/projects/demo/documents/noc/generate')
    assert client.app.state.repository.get('demo').generated == {'noc'}
    response = client.post('/projects/demo/members/generate', data={'kind': 'affidavit'})
    assert response.headers['content-type'] == 'application/zip'
    assert len(ZipFile(BytesIO(response.content)).namelist()) == 5
    client.post('/projects/demo/members/generate', data={'kind': 'consent'})
    assert client.app.state.repository.get('demo').generated == {'noc'} | {f'{kind}:m{i}' for kind in ('affidavit', 'consent') for i in range(1, 6)}


def test_missing_data_and_invalid_bulk_do_not_generate(client):
    client.post('/projects/demo/committee/m1/remove')
    response = client.post('/projects/demo/documents/noc/generate')
    assert 'Cannot generate' in response.text
    assert not client.app.state.repository.get('demo').generated
    assert client.post('/projects/demo/members/generate', data={'kind': 'affidavit', 'member_id': ['m2', 'other-project-member']}).status_code == 400
    assert not client.app.state.repository.get('demo').generated
    assert 'need more data' in client.post('/projects/demo/members/generate', data={'kind': 'consent'}).text
    assert client.post('/projects/demo/documents/consent/generate').status_code == 404


def test_settings_and_readiness_invalidation(client):
    client.post('/projects/demo/documents/noc/generate')
    project = client.app.state.repository.get('demo')
    response = client.post('/projects/demo/details', data={**project.details, **project.settings, 'consent_place': '', 'member_count': '2'})
    assert response.status_code == 200
    project = client.app.state.repository.get('demo')
    assert not project.generated
    assert document_state(project, 'consent', project.members['m1'])['status'] == 'Missing Data'
    assert document_state(project, 'form_a')['status'] == 'Missing Data'


def test_app_instances_and_repository_reads_are_isolated():
    repo = mock_repository()
    project = repo.get('demo')
    project.details['project_name'] = 'unsaved'
    assert repo.get('demo').details['project_name'] != 'unsaved'
    app1, app2 = create_app(), create_app()
    project = app1.state.repository.get('demo')
    project.generated.add('noc')
    app1.state.repository.save(project)
    assert not app2.state.repository.get('demo').generated


def test_static_assets_and_not_found(client):
    assert client.get('/static/vendor/bootstrap.min.css').status_code == 200
    assert client.get('/static/app.css').status_code == 200
    assert client.get('/projects/unknown').status_code == 404
    assert client.get('/projects/demo/members/unknown').status_code == 404


def test_ui_does_not_use_desktop_processing_or_output_storage():
    import ast
    from pathlib import Path
    forbidden = {'processor', 'sheets_service', 'config_manager', 'desktop'}
    for path in Path('web').rglob('*.py'):
        for node in ast.walk(ast.parse(path.read_text())):
            modules = [node.module or ''] if isinstance(node, ast.ImportFrom) else [a.name for a in node.names] if isinstance(node, ast.Import) else []
            assert not forbidden.intersection(m.split('.')[0] for m in modules)


def test_project_details_save_both_groups_and_preserve_members(client):
    before = client.app.state.repository.get('demo')
    data = {**before.details, **before.settings, 'project_name': 'Updated project',
            'affidavit_execution_place': '  इंदौर  ', 'member_count': '11'}
    response = client.post('/projects/demo/details', data=data)
    assert response.status_code == 200
    after = client.app.state.repository.get('demo')
    assert after.details['project_name'] == 'Updated project'
    assert after.settings['affidavit_execution_place'] == 'इंदौर'
    assert after.settings['member_count'] == '11'
    assert after.members == before.members
    assert after.committee_members == before.committee_members
    assert 'value="इंदौर"' in response.text
    assert 'value="11"' in response.text


def test_project_details_invalid_settings_save_neither_group(client):
    before = client.app.state.repository.get('demo')
    response = client.post('/projects/demo/details', data={**before.details, **before.settings,
        'project_name': 'Unsaved project', 'member_count': 'invalid'})
    assert response.status_code == 422
    after = client.app.state.repository.get('demo')
    assert after == before
    assert 'value="Unsaved project"' in response.text
    assert 'value="invalid"' in response.text


def test_create_project_with_document_details(client):
    response = client.post('/projects/new', data={'project_name': 'New', 'association_name': 'Society',
        'consent_place': 'इंदौर', 'member_count': '11'})
    assert response.status_code == 200
    project_id = response.url.path.rsplit('/', 1)[-1]
    project = client.app.state.repository.get(project_id)
    assert project.settings['consent_place'] == 'इंदौर'
    assert project.settings['member_count'] == '11'
    names = [c.get('name') for c in Controls(client.get('/projects/new').text).controls]
    assert set(names) == {f.key for f in (*PROJECT_FIELDS, *SETTINGS_FIELDS)}


def test_edit_member_designation_is_prefilled_and_saved(client):
    assert 'value="अध्यक्ष" selected' in client.get('/projects/demo/members/m1/edit').text
    before = client.app.state.repository.get('demo')
    response = client.post('/projects/demo/members/m2/edit', data={**before.members['m2'], 'designation': 'सचिव'})
    assert response.status_code == 200
    after = client.app.state.repository.get('demo')
    assert next(a['designation'] for a in after.committee_members if a['member_id'] == 'm2') == 'सचिव'
    assert 'value="सचिव" selected' in client.get('/projects/demo/members/m2/edit').text
    assert after.members == before.members


def test_edit_member_invalid_designation_preserves_record(client):
    before = client.app.state.repository.get('demo')
    response = client.post('/projects/demo/members/m2/edit', data={**before.members['m2'],
        'member_name': 'Unsaved name', 'designation': 'अध्यक्ष'})
    assert response.status_code == 422
    assert client.app.state.repository.get('demo') == before
    assert 'value="अध्यक्ष" selected' in response.text


def test_member_designation_can_be_added_and_removed(client):
    response = client.post('/projects/demo/members/new', data={'member_name': 'New committee member', 'designation': 'सदस्य'})
    assert response.status_code == 200
    member_id = response.url.path.rsplit('/', 1)[-1]
    project = client.app.state.repository.get('demo')
    assert {'member_id': member_id, 'designation': 'सदस्य'} in project.committee_members
    assert client.post(f'/projects/demo/members/{member_id}/edit', data={**project.members[member_id], 'designation': ''}).status_code == 200
    after = client.app.state.repository.get('demo')
    assert member_id in after.members
    assert all(a['member_id'] != member_id for a in after.committee_members)


def test_all_member_generation_ignores_search_filter(client):
    response = client.get('/projects/demo/members?q=missing')
    assert not any(c.get('type') == 'checkbox' for c in Controls(response.text).controls)
    assert 'Generate Affidavits for All Members' in response.text
    response = client.post('/projects/demo/members/generate?q=missing', data={'kind': 'affidavit'})
    assert response.headers['content-type'] == 'application/zip'
    assert len(ZipFile(BytesIO(response.content)).namelist()) == 5
    assert client.app.state.repository.get('demo').generated == {f'affidavit:m{i}' for i in range(1, 6)}


def test_all_member_generation_stops_for_incomplete_or_empty_members(client):
    repo = client.app.state.repository
    project = repo.get('demo')
    project.members['m3']['father_name'] = ''
    repo.save(project)
    response = client.post('/projects/demo/members/generate', data={'kind': 'affidavit'})
    assert '1 member(s) need more data' in response.text
    assert not repo.get('demo').generated
    project.members.clear()
    project.committee_members.clear()
    repo.save(project)
    response = client.post('/projects/demo/members/generate', data={'kind': 'affidavit'})
    assert 'Add members before generating documents' in response.text
    assert not repo.get('demo').generated


def test_developer_person_company_and_address_save_independently(client):
    repo = client.app.state.repository
    project = repo.get('demo')
    values = {**project.details, **project.settings, 'developer_name': 'TEST Person',
              'developer_company': 'TEST Firm', 'developer_address': 'TEST Office'}
    assert client.post('/projects/demo/details', data=values).status_code == 200
    saved = repo.get('demo')
    for key in ('developer_name', 'developer_company', 'developer_address'):
        assert saved.details[key] == values[key]
    assert document_state(saved, 'noc')['status'] == 'Ready'
    saved.details['developer_company'] = ''
    assert document_state(saved, 'noc')['status'] == 'Missing Data'
    assert document_state(saved, 'affidavit', saved.members['m1'])['status'] == 'Ready'


@pytest.mark.parametrize('kind', ['noc', 'registration', 'by_law', 'form_a'])
def test_project_downloads_are_rendered_docx(client, kind):
    response = client.post(f'/projects/demo/documents/{kind}/generate')
    assert response.status_code == 200
    assert response.headers['content-disposition'].endswith('.docx')
    assert response.headers['cache-control'] == 'no-store'
    with ZipFile(BytesIO(response.content)) as archive:
        xml = archive.read('word/document.xml').decode()
    assert '{{' not in xml
    assert 'TEST Sample Residents Association' in xml


@pytest.mark.parametrize('kind', ['affidavit', 'consent'])
def test_member_zip_contains_personalized_word_files(client, kind):
    response = client.post('/projects/demo/members/generate', data={'kind': kind})
    with ZipFile(BytesIO(response.content)) as archive:
        assert len(set(archive.namelist())) == 5
        for filename, member in zip(archive.namelist(), client.app.state.repository.get('demo').members.values()):
            with ZipFile(BytesIO(archive.read(filename))) as document:
                xml = document.read('word/document.xml').decode()
            assert member['member_name'] in xml
            assert '{{' not in xml


def test_render_failure_does_not_mark_documents_generated(client, monkeypatch):
    from models import RowError
    def fail(*args):
        raise RowError('DOCX rendering failed.')
    monkeypatch.setattr('web.downloads.render_document', fail)
    for path, data in [('documents/noc/generate', {}), ('members/generate', {'kind': 'affidavit'})]:
        response = client.post('/projects/demo/' + path, data=data)
        assert 'Cannot generate' in response.text
        assert 'content-disposition' not in response.headers
        assert not client.app.state.repository.get('demo').generated


def test_affidavit_requires_member_designation(client):
    client.post('/projects/demo/committee/m2/remove')
    response = client.post('/projects/demo/members/generate', data={'kind': 'affidavit'})
    assert 'need more data' in response.text
    assert not client.app.state.repository.get('demo').generated


@pytest.mark.parametrize('count', [2, 3, 4])
def test_form_a_minimum_three_committee_members(client, count):
    repo = client.app.state.repository
    project = repo.get('demo')
    project.committee_members = project.committee_members[:count]
    project.settings['member_count'] = str(count)
    repo.save(project)
    response = client.post('/projects/demo/documents/form_a/generate')
    if count >= 3:
        assert response.headers['content-disposition'].endswith('.docx')
        from docx import Document
        document = Document(BytesIO(response.content))
        assert all(len(table.rows) - 1 == count for table in document.tables[1:])
    else:
        assert '3–11 committee assignments' in response.text
        assert not repo.get('demo').generated
    assert '5–11 committee assignments' in document_state(project, 'consent', project.members['m1'])['missing']
