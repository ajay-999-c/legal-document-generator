from io import BytesIO
import json
import pytest
from docx import Document
from document_registry import SPECS
from document_generator import heading_map, preflight_template, xml_parts
from tests.helpers import values
from tests.extension_helpers import ROOT, render


def test_final_affidavit_headers_and_fixed_content(settings):
    spec = SPECS['affidavit']
    headers = json.loads((ROOT / 'tests/fixtures/migration_headers.json').read_text(encoding='utf-8'))['affidavit']
    assert len(heading_map(spec, headers)) == 14
    data = values('affidavit')
    assert not {'land_details', 'khasra_number', 'project_location', 'designation', 'document_date'} & data.keys()
    preflight_template(spec, settings.documents['affidavit'], settings)
    context, output = render(spec, settings, data)
    text = xml_parts(BytesIO(output))['word/document.xml']
    for value in context.values():
        assert value in text
    assert text.count(data['association_address']) == 1
    assert text.count('_________') == 3
    assert text.count('कार्यकारिणी कोषाध्यक्ष') == 4
    assert context['ASSOCIATION_NAME'] == data['association_name']


@pytest.mark.parametrize('parameter', [f.parameter for f in SPECS['affidavit'].fields])
def test_missing_affidavit_input(settings, parameter):
    from models import RowError
    data = values('affidavit')
    del data[parameter]
    with pytest.raises(RowError, match=parameter):
        render(SPECS['affidavit'], settings, data)
