from unittest.mock import Mock
import subprocess
import sys
import pytest
import yaml
import gspread
import requests
from config_manager import load_settings, DEFAULT_CONFIG
from models import SetupError
from main import main, row_numbers
from sheets_service import connect, read_call
from tests.conftest import ROOT

def write_config(tmp_path,data):
    path=tmp_path/'config.yaml'; path.write_text(yaml.safe_dump(data),encoding='utf-8'); return path

@pytest.mark.parametrize('bad',['YOUR_SPREADSHEET_ID','https://docs.google.com/spreadsheets/d/abc','abc12345678901234567890/',''])
def test_invalid_spreadsheet_id(config_data,tmp_path,bad):
    config_data['google']['spreadsheet_id']=bad
    with pytest.raises(SetupError): load_settings(write_config(tmp_path,config_data))

def test_paths_and_cwd(config_data,tmp_path,monkeypatch):
    absolute=tmp_path/'absolute with spaces'; config_data['documents']['affidavit']['output_dir']=str(absolute)
    path=write_config(tmp_path,config_data); elsewhere=tmp_path/'elsewhere'; elsewhere.mkdir(); monkeypatch.chdir(elsewhere)
    settings=load_settings(path)
    assert settings.documents['noc'].output_dir==tmp_path/'output with spaces/noc'
    assert settings.documents['affidavit'].output_dir==absolute and DEFAULT_CONFIG==ROOT/'config.yaml'
    assert main(['--config',str(path),'validate-config'])==2

@pytest.mark.parametrize('pattern',['../{row_number}.docx','X_{unknown}_{row_number}.docx','X_{project_name!r}_{row_number}.docx','X_{row_number:03}.docx','X_{row_number}.pdf','constant.docx','X_{row_number','X_\\{row_number}.docx'])
def test_bad_patterns(config_data,tmp_path,pattern):
    config_data['documents']['noc']['filename_pattern']=pattern
    with pytest.raises(SetupError): load_settings(write_config(tmp_path,config_data))

def test_duplicate_yaml_unknown_key(config_data,tmp_path):
    path=write_config(tmp_path,config_data); path.write_text(path.read_text()+'\nschema_version: 1\n')
    with pytest.raises(SetupError,match='unique'): load_settings(path)
    config_data['documents']['unregistered']={'enabled':True}
    with pytest.raises(SetupError,match='Unsupported'): load_settings(write_config(tmp_path,config_data))

@pytest.mark.parametrize('change',[lambda d:d['app'].pop('log_file'),lambda d:d['documents']['noc'].update(enabled='yes'),lambda d:d['formatting'].update(blank_document_date='today'),lambda d:d['processing'].update(error_message_max_length=True)])
def test_bad_schema(config_data,tmp_path,change):
    change(config_data)
    with pytest.raises(SetupError): load_settings(write_config(tmp_path,config_data))

@pytest.mark.parametrize('text',['1','0','-2','2,x','2,','2.0','', '٢'])
def test_bad_rows(text):
    with pytest.raises(Exception): row_numbers(text)

def test_list_local(tmp_path,monkeypatch,capsys):
    monkeypatch.chdir(tmp_path); assert main(['list-documents'])==0
    assert 'consent' in capsys.readouterr().out
    result=subprocess.run([sys.executable,str(ROOT/'main.py'),'list-documents'],cwd=tmp_path,capture_output=True,text=True)
    assert result.returncode==0 and '17 inputs' in result.stdout

def test_wrong_worksheet(settings,monkeypatch):
    import sheets_service
    monkeypatch.setattr(sheets_service.Credentials,'from_service_account_file',lambda *a,**kw:object())
    client=Mock(); client.open_by_key.return_value.worksheet.side_effect=gspread.exceptions.WorksheetNotFound('synthetic')
    monkeypatch.setattr(sheets_service.gspread,'authorize',lambda creds:client)
    with pytest.raises(SetupError): connect(settings,settings.documents['noc'])
    client.open_by_key.assert_called_once_with(settings.spreadsheet_id)
    client.open_by_key.return_value.worksheet.assert_called_once_with('NOC Responses')
    client.set_timeout.assert_called_once_with((15,60))

def test_bounded_retries(monkeypatch):
    import sheets_service
    monkeypatch.setattr(sheets_service.time,'sleep',lambda _:None)
    op=Mock(side_effect=requests.Timeout())
    with pytest.raises(requests.Timeout): read_call(op)
    assert op.call_count==3

def test_cli_readonly_dry_run(settings,monkeypatch,capsys):
    import main as cli
    import processor
    from tests.helpers import FakeSheet
    sheet=FakeSheet(); monkeypatch.setattr(cli,'load_settings',lambda _:settings)
    monkeypatch.setattr(cli,'connect',lambda *a:sheet); monkeypatch.setattr(processor,'connect',lambda *a:sheet)
    assert main(['check-sheets','--document','noc'])==0
    assert 'write access unverified' in capsys.readouterr().out
    assert main(['generate','--document','noc','--rows','2','--dry-run'])==0
    assert not sheet.writes and not settings.documents['noc'].output_dir.exists()

def test_date_diagnostics_do_not_expose_values(settings,monkeypatch,capsys):
    import main as cli
    from tests.helpers import FakeSheet, values
    data=values('noc'); data['completion_certificate_date']='PRIVATE wrong date'
    sheet=FakeSheet(records=[data])
    monkeypatch.setattr(cli,'load_settings',lambda _:settings)
    monkeypatch.setattr(cli,'connect',lambda *a:sheet)
    assert main(['check-sheets','--document','noc'])==1
    output=capsys.readouterr().out
    assert 'mismatch=1' in output and 'PRIVATE' not in output and not sheet.writes


def test_tilde_and_disabled(config_data,tmp_path):
    from pathlib import Path
    from document_registry import selected
    config_data['documents']['noc']['output_dir']='~/legal-test-output'
    config_data['documents']['consent']['enabled']=False
    settings=load_settings(write_config(tmp_path,config_data))
    assert settings.documents['noc'].output_dir==Path.home()/'legal-test-output'
    with pytest.raises(SetupError,match='disabled'): selected(settings,'consent')


def test_standalone_copy_without_legacy(config_data,tmp_path):
    import shutil
    destination=tmp_path/'standalone'; destination.mkdir()
    for source in ROOT.glob('*.py'): shutil.copy2(source,destination/source.name)
    shutil.copytree(ROOT/'documents',destination/'documents',ignore=shutil.ignore_patterns('__pycache__'))
    shutil.copytree(ROOT/'templates',destination/'templates')
    for config in config_data['documents'].values():
        config['template_path']='templates/'+config['template_path'].split('/')[-1]
    config=write_config(destination,config_data)
    # Fresh interpreter with neither parent workspace nor sibling apps on sys.path.
    script="from config_manager import load_settings; from document_registry import SPECS; from document_generator import preflight_template; s=load_settings(); [preflight_template(SPECS[k], c, s) for k,c in s.documents.items()]; print('standalone templates OK')"
    result=subprocess.run([sys.executable,'-c',script],cwd=destination,capture_output=True,text=True)
    assert result.returncode==0, result.stderr
    assert 'standalone templates OK' in result.stdout
