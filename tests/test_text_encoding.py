"""Regression checks for the Windows CP1252 fixture-loading failure."""
from pathlib import Path
import pytest

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
    for key, count, required in [('noc', 12, 11), ('affidavit', 15, 15), ('consent', 35, 22)]:
        test_schema_against_business_contract(key, count, required)
