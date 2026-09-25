"""Regression checks for the Windows CP1252 fixture-loading failure."""
from pathlib import Path
import pytest

from desktop_config import DesktopConfig
from tests.helpers import values


@pytest.fixture
def cp1252_default(monkeypatch):
    original = Path.open

    def windows_open(self, mode='r', buffering=-1, encoding=None, errors=None, newline=None):
        if 'b' not in mode and encoding in (None, 'locale'):
            encoding = 'cp1252'
        return original(self, mode, buffering, encoding, errors, newline)

    monkeypatch.setattr(Path, 'open', windows_open)


@pytest.mark.parametrize('key', ['noc', 'affidavit', 'consent'])
def test_hindi_fixtures_with_cp1252_default(cp1252_default, key):
    # These literal Hindi fixtures previously failed before processing even began.
    assert any('परीक्षण' in value for value in values(key).values())


def test_form_contract_with_cp1252_default(cp1252_default):
    from tests.test_documents import test_schema_against_business_contract
    for key, count, required in [('noc', 12, 11), ('affidavit', 14, 14), ('consent', 35, 22)]:
        test_schema_against_business_contract(key, count, required)


def test_unicode_output_config_roundtrip_with_cp1252_default(cp1252_default, settings, tmp_path):
    folder = tmp_path / 'परीक्षण Documents'
    folder.mkdir()
    store = DesktopConfig(settings.config_path)
    updated = store.save_output('noc', folder)
    assert updated.documents['noc'].output_dir == folder
    assert store.load().documents['noc'].output_dir == folder
    assert 'परीक्षण' in settings.config_path.read_text(encoding='utf-8')
