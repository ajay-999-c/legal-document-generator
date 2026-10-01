"""Historical imports are explicitly reviewed and never mutate response sheets."""
from copy import deepcopy
from fastapi.testclient import TestClient
import pytest
from web.app import create_app
from web.repository import InMemoryProjectRepository, Project, RepositoryError
from web.legacy_import import SourceRow, group_candidates, build_plan, LegacySource, CONTRACT


def row(kind='affidavit', number=2, **values):
    return SourceRow(kind, kind+' Responses', number,
        {'project_name':'TEST Previous', 'association_name':'TEST Association', **values}, '%m/%d/%Y')


def basic_rows():
    return [row(name='TEST Member',father_name='TEST Father',age='35',address='TEST Address',plot_no='026',
                developer_name='TEST Developer',completion_certificate_date='01/15/2025',city='TEST City'),
            row('consent',applicant_name='TEST Member',applicant_address='TEST Address',plot_no='026',
                place='TEST City',member_1_name='TEST Member',member_1_designation='अध्यक्ष'),
            row('form_a_registration',management_committee_address='TEST Location',member_count='5.0',
                committee_member_1_name='TEST Member',committee_member_1_plot_no='026',
                committee_member_1_mobile='0000000001',committee_member_1_designation='अध्यक्ष')]


class FakeSource:
    def __init__(self,rows): self.rows=rows
    def read(self): return group_candidates(self.rows),[]


@pytest.fixture
def flow():
    repo=InMemoryProjectRepository()
    app=create_app(repo)
    source=FakeSource(basic_rows())
    app.state.legacy_source=source
    with TestClient(app) as client:
        yield client,repo,source


def post_data(candidate):
    plan=build_plan(candidate)
    return {**plan['project'].details, **plan['project'].settings, '_source_revision':candidate.fingerprint}


def test_contract_matches_unchanged_adapter_headings():
    from document_registry import SPECS
    assert CONTRACT == {key:[{'key':f.parameter,'headings':[f.heading,*f.aliases]} for f in spec.fields] for key,spec in SPECS.items()}


def test_group_exact_identity_and_unambiguous_bylaw():
    rows=[row(),row('consent',project_name=' test   previous '),
          row('by_law',association_address='Address',work_area='Area')]
    candidates=group_candidates(rows)
    assert len(candidates)==1 and len(candidates[0].rows)==3
    rows.append(row('registration',project_name='Different Project'))
    candidates=group_candidates(rows)
    assert len(candidates)==2
    assert all(not any(r.kind=='by_law' for r in c.rows) for c in candidates)


def test_build_plan_shared_members_committee_and_dates():
    candidate=group_candidates(basic_rows())[0]
    plan=build_plan(candidate);project=plan['project']
    assert len(project.members)==1
    member=next(iter(project.members.values()))
    assert member['plot_no']=='026' and member['mobile']=='0000000001'
    assert member['father_name']=='TEST Father'
    assert project.committee_members==[{'member_id':member['member_id'],'designation':'अध्यक्ष'}]
    assert project.details['completion_certificate_date']=='2025-01-15'
    assert project.settings['member_count']=='5'
    assert project.settings['consent_place']=='TEST City'
    assert not project.generated


def test_conflicts_left_blank_with_evidence():
    rows=basic_rows()+[row(number=8,name='TEST Member',plot_no='026',father_name='Different Father',developer_name='Other Developer')]
    plan=build_plan(group_candidates(rows)[0])
    assert plan['project'].details['developer_name']==''
    assert len(plan['conflicts']['developer_name'])==2
    assert next(iter(plan['project'].members.values()))['father_name']==''
    assert any('Different Father' in w for w in plan['warnings'])


def test_name_only_ambiguous_member_not_attached_to_wrong_plot():
    rows=[row(name='Same',plot_no='01'),row(number=3,name='Same',plot_no='02'),
          row('consent',member_1_name='Same',member_1_designation='अध्यक्ष')]
    plan=build_plan(group_candidates(rows)[0])
    assert len(plan['project'].members)==3
    assert not plan['project'].committee_members
    assert plan['warnings']


def test_conflicting_or_invalid_rosters_not_silently_chosen():
    rows=basic_rows()
    rows[-1].values['committee_member_1_designation']='सचिव'
    assert not build_plan(group_candidates(rows)[0])['project'].committee_members
    rows[-1].values['committee_member_1_designation']='Unrecognised'
    assert not build_plan(group_candidates(rows)[0])['project'].committee_members


def test_no_legal_dates_or_derived_person_fields_imported():
    rows=[row('noc',recipient_name='Wrong Recipient',signatory_name='Wrong President',developer_company='Correct Developer',document_date='2025-01-01'),
          row(name='Correct Member',plot_no='026',age='999',completion_certificate_date='bad date')]
    plan=build_plan(group_candidates(rows)[0]);p=plan['project']
    assert p.details['developer_company']=='Correct Developer'
    assert p.details['developer_name']==''
    assert p.details['completion_certificate_date']==''
    assert next(iter(p.members.values()))['age']==''
    assert len(p.members)==1 and not p.committee_members
    assert all('date' not in key for key in p.settings)
    assert 'recipient_name' not in p.details and 'signatory_name' not in p.details


def test_discover_review_load_and_repeat(flow):
    client,repo,source=flow
    candidate=source.read()[0][0]
    assert 'Load Previous Project' in client.get('/projects').text
    listing=client.get('/projects/load')
    assert listing.status_code==200 and candidate.project_name in listing.text
    assert 'No previous projects found' in client.get('/projects/load?q=absent').text
    preview=client.get('/projects/load/'+candidate.key)
    assert preview.status_code==200 and 'TEST Member' in preview.text
    assert repo.list()==[]
    response=client.post('/projects/load/'+candidate.key,data=post_data(candidate))
    assert response.status_code==200 and 'Previous project loaded' in response.text
    assert len(repo.list())==1
    loaded=repo.get(candidate.project_id)
    loaded.details['developer_name']='Edited after import';repo.save(loaded)
    response=client.post('/projects/load/'+candidate.key,data=post_data(candidate))
    assert response.status_code==200 and 'already loaded' in response.text
    assert len(repo.list())==1 and repo.get(candidate.project_id).details['developer_name']=='Edited after import'
    assert 'Open loaded project' in client.get('/projects/load').text


def test_stale_sources_block_import(flow):
    client,repo,source=flow
    candidate=source.read()[0][0];data=post_data(candidate)
    source.rows[0].values['developer_name']='Updated after preview'
    response=client.post('/projects/load/'+candidate.key,data=data)
    assert response.status_code==409 and not repo.list()


def test_existing_manual_project_opened_without_overwrite(flow):
    client,repo,source=flow
    candidate=source.read()[0][0]
    repo.save(Project('manual',{'project_name':candidate.project_name,'association_name':candidate.association_name}))
    response=client.get('/projects/load/'+candidate.key)
    assert '/projects/manual' in str(response.url)
    assert len(repo.list())==1


def test_import_validation_and_no_writes_on_invalid_input(flow):
    client,repo,source=flow
    candidate=source.read()[0][0];data=post_data(candidate)
    data['completion_certificate_date']='invalid'
    assert client.post('/projects/load/'+candidate.key,data=data).status_code==422
    assert not repo.list()
    assert client.get('/projects/load/missing').status_code==404


def test_import_form_only_certificate_date(flow):
    from tests.test_web_ui import Controls
    client,repo,source=flow;candidate=source.read()[0][0]
    controls=Controls(client.get('/projects/load/'+candidate.key).text).controls
    assert [c['name'] for c in controls if c.get('type')=='date']==['completion_certificate_date']
    forbidden={'signatory_name','document_date','meeting_date','recipient_name','applicant_name'}
    assert not forbidden.intersection(c.get('name') for c in controls)


def test_demo_has_clear_unavailable_message():
    with TestClient(create_app()) as client:
        assert 'available in Google Sheets mode' in client.get('/projects/load').text


class ReadOnlyBook:
    def __init__(self,duplicate=False):
        self.calls=[]
        fields=CONTRACT['affidavit']
        self.headers=[f['headings'][0] for f in fields]
        vals={'project_name':'TEST Previous','association_name':'TEST Association','name':'TEST Name','plot_no':'026'}
        self.row=[vals.get(f['key'],'') for f in fields]
        if duplicate:
            self.headers.append(self.headers[0])
    def fetch_sheet_metadata(self):
        return {'sheets':[{'properties':{'title':'Actual Affidavit Tab','sheetId':71,'gridProperties':{'rowCount':1000,'columnCount':40}}}]}
    def values_get(self,a1,params):
        self.calls.append(a1)
        assert params['valueRenderOption']=='FORMATTED_VALUE'
        if a1.endswith('!1:1'):return {'values':[self.headers]}
        return {'values':[self.row]}
    def batch_update(self,*args):
        raise AssertionError('Legacy source must never write')


def test_source_metadata_bound_formatted_reads():
    from threading import RLock
    from types import SimpleNamespace
    book=ReadOnlyBook();repo=SimpleNamespace(book=book,_lock=RLock())
    candidates,warnings=LegacySource(repo,{'affidavit':{'worksheet_name':'Actual Affidavit Tab','input_date_format':'%m/%d/%Y'}}).read()
    assert len(candidates)==1 and candidates[0].rows[0].values['plot_no']=='026'
    assert book.calls==["'Actual Affidavit Tab'!1:1","'Actual Affidavit Tab'!A2:AN1000"]


def test_ambiguous_source_headers_block_import():
    from threading import RLock
    from types import SimpleNamespace
    repo=SimpleNamespace(book=ReadOnlyBook(True),_lock=RLock())
    with pytest.raises(RepositoryError,match='ambiguous column'):
        LegacySource(repo,{'affidavit':{'worksheet_name':'Actual Affidavit Tab','input_date_format':'%m/%d/%Y'}}).read()


def test_import_matches_unique_project_name_even_if_association_differs(flow):
    client, repo, source = flow
    candidate = source.read()[0][0]
    repo.save(Project('manual', {'project_name': '  ' + candidate.project_name.upper() + '  ',
                                'association_name': 'Saved association'}))
    response = client.post('/projects/load/' + candidate.key, data=post_data(candidate))
    assert '/projects/manual' in str(response.url)
    assert len(repo.list()) == 1
    assert repo.get('manual').details['association_name'] == 'Saved association'
