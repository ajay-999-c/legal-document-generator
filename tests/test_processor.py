from dataclasses import replace
import pytest
import processor
from models import SetupError, RowError
from processor import run_batch
from document_registry import SPECS
from tests.helpers import FakeSheet, values

@pytest.mark.parametrize('key',list(SPECS))
def test_statuses_physical_rows_second_run(settings,key):
    records=[values(key),None,{**values(key),'processing_status':' eRrOr '},*[{**values(key),'processing_status':s} for s in ('PROCESSING','GENERATED','other')]]
    sheet=FakeSheet(key,records); original=[list(row) for row in sheet.data]; events=[]
    result=run_batch(settings,key,worksheet=sheet,progress=events.append)
    assert result.counts['generated']==2 and result.counts['skipped']==4
    assert [r.row_number for r in result.rows]==[2,3,4,5,6,7] and len(events)==6
    assert len(list(settings.documents[key].output_dir.glob('*.docx')))==2
    assert run_batch(settings,key,worksheet=sheet).counts['generated']==0
    boundary=len(sheet.headers)-4
    for before,after in zip(original,sheet.data): assert before[:boundary]==after[:boundary]
    for other,config in settings.documents.items():
        if other!=key: assert not config.output_dir.exists()

def test_selected_rows_dry_run(settings,tmp_path):
    sheet=FakeSheet(records=[values('noc'),None,values('noc')])
    preview=run_batch(settings,'noc',rows=[4],dry_run=True,worksheet=sheet)
    assert preview.counts['would_generate']==1 and not sheet.writes
    assert not settings.documents['noc'].output_dir.exists() and not list(tmp_path.rglob('*.docx'))
    actual=run_batch(settings,'noc',rows=[4],worksheet=sheet)
    assert [r.row_number for r in actual.rows]==[4] and sheet.data[1][-4]==''
    assert all('4' in item['range'] for request in sheet.writes for item in request)
    assert run_batch(settings,'noc',rows=[4],worksheet=sheet).counts['skipped']==1

@pytest.mark.parametrize('change',['value','status','header'])
def test_row_change(settings,change):
    sheet=FakeSheet()
    def modify(fake,number):
        if change=='value': fake.data[1][1]='changed'
        elif change=='status': fake.data[1][-4]='GENERATED'
        else: fake.data[0][1]='changed heading'
    sheet.before_read=modify
    result=run_batch(settings,'noc',worksheet=sheet)
    assert result.counts['changed']==1 and not sheet.writes

def test_recheck_failure_never_mutates(settings):
    sheet=FakeSheet()
    def fail(*args): raise OSError('read failed')
    sheet.before_read=fail
    assert run_batch(settings,'noc',worksheet=sheet).counts['failed']==1
    assert not sheet.writes

@pytest.mark.parametrize('problem',['header','operational_duplicate','template','destination','rows'])
def test_preflight_before_mutation(settings,tmp_path,problem):
    sheet=FakeSheet()
    if problem=='header': sheet.data[0][1]='wrong'
    if problem=='operational_duplicate': sheet.data[0].append('processing_status')
    if problem=='template': settings=replace(settings,documents={**settings.documents,'noc':replace(settings.documents['noc'],template_path=tmp_path/'missing.docx')})
    if problem=='destination':
        path=settings.documents['noc'].output_dir; path.parent.mkdir(parents=True); path.write_text('not a directory', encoding='utf-8')
    with pytest.raises(SetupError): run_batch(settings,'noc',rows=[200] if problem=='rows' else None,worksheet=sheet)
    assert not sheet.writes

def test_unrelated_template(settings,tmp_path):
    settings=replace(settings,documents={**settings.documents,'consent':replace(settings.documents['consent'],template_path=tmp_path/'absent.docx')})
    assert run_batch(settings,'noc',worksheet=FakeSheet()).counts['generated']==1

@pytest.mark.parametrize('failure',['validation','render','save'])
def test_row_failure_continues(settings,monkeypatch,failure):
    bad=values('noc'); bad['recipient_name']=''
    sheet=FakeSheet(records=[bad if failure=='validation' else values('noc'),values('noc')])
    if failure!='validation':
        method='render_bytes' if failure=='render' else 'save_atomic'; real=getattr(processor,method); calls=[]
        def fail_once(*args,**kwargs):
            calls.append(1)
            if len(calls)==1: raise RowError('Synthetic operation failed.')
            return real(*args,**kwargs)
        monkeypatch.setattr(processor,method,fail_once)
    result=run_batch(settings,'noc',worksheet=sheet)
    assert result.counts['failed']==1 and result.counts['generated']==1
    assert sheet.data[1][-4]=='ERROR' and sheet.data[2][-4]=='GENERATED'
    assert len(sheet.data[1][-1])<=settings.error_message_max_length

@pytest.mark.parametrize('also_error',[False,True])
def test_saved_status_failure(settings,also_error):
    sheet=FakeSheet(); sheet.fail_statuses={'GENERATED'}|({'ERROR'} if also_error else set())
    result=run_batch(settings,'noc',worksheet=sheet); row=result.rows[0]
    assert result.counts['generated']==0 and result.counts['sync_failed']==1 and row.saved_path.is_file()
    assert len(row.synchronization_errors)==(2 if also_error else 1)
    assert sheet.data[1][-4]==('PROCESSING' if also_error else 'ERROR') and not result.successful

def test_uncertain_claim(settings):
    sheet=FakeSheet(); sheet.fail_statuses={'PROCESSING'}
    result=run_batch(settings,'noc',worksheet=sheet)
    assert result.counts['sync_failed']==1 and not sheet.writes and result.rows[0].saved_path is None

def test_error_sync_failure(settings):
    data=values('noc'); data['recipient_name']=''
    sheet=FakeSheet(records=[data]); sheet.fail_statuses={'ERROR'}
    result=run_batch(settings,'noc',worksheet=sheet)
    assert result.counts['failed']==1 and result.rows[0].synchronization_errors

def test_dry_run_invalid_trailing_blanks(settings):
    data=values('noc'); data['signatory_role']=''; data['project_name']=''
    sheet=FakeSheet(records=[data]); sheet.data[1]=sheet.data[1][:-5]
    assert run_batch(settings,'noc',dry_run=True,worksheet=sheet).counts['invalid']==1 and not sheet.writes

def test_status_positions_not_hardcoded(settings):
    sheet=FakeSheet()
    for i,row in enumerate(sheet.data): sheet.data[i]=row[-4:]+row[:-4]
    sheet.headers=sheet.data[0].copy()
    assert run_batch(settings,'noc',worksheet=sheet).counts['generated']==1
    assert sheet.data[1][0]=='GENERATED' and len(sheet.writes[-1])==4

def test_retry_replaces_same_file(settings):
    sheet=FakeSheet(); first=run_batch(settings,'noc',worksheet=sheet).rows[0].saved_path
    sheet.data[1][-4]='ERROR'; second=run_batch(settings,'noc',worksheet=sheet).rows[0].saved_path
    assert first==second and len(list(first.parent.glob('*.docx')))==1

def test_bad_progress_callback_does_not_abort(settings):
    def broken(event): raise RuntimeError('consumer failed')
    result=run_batch(settings,'noc',worksheet=FakeSheet(records=[values('noc'),values('noc')]),progress=broken)
    assert result.counts['generated']==2
