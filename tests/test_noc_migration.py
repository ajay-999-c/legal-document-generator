from io import BytesIO
import json
import pytest
from docx import Document
from document_registry import SPECS
from document_generator import heading_map, preflight_template, xml_parts
from tests.helpers import values
from tests.extension_helpers import ROOT, render


@pytest.mark.parametrize('date,expected', [('', '..........'), ('2026-09-25', '25-09-2026')])
def test_exact_noc_contract_and_independent_addresses(settings, date, expected):
    spec = SPECS['noc']
    headers = json.loads((ROOT / 'tests/fixtures/migration_headers.json').read_text(encoding='utf-8'))['noc']
    assert len(heading_map(spec, headers)) == 12
    data = values('noc')
    removed = {'signatory_role', 'khasra_number', 'association_location'}
    assert not removed & data.keys()
    assert not removed & {f.placeholder for f in spec.fields}
    data.update(document_date=date, project_location='स्वतंत्र स्थान भोपाल')
    preflight_template(spec, settings.documents['noc'], settings)
    context, output = render(spec, settings, data)
    assert context['association_address'] == data['association_address']
    parts = xml_parts(BytesIO(output))
    # This supplied template places the title/location at the top of the body,
    # rather than in a separate Word header part.
    paragraphs = [p.text.strip() for p in Document(BytesIO(output)).paragraphs if p.text.strip()]
    assert paragraphs.index(data['project_location']) == paragraphs.index(data['association_name']) + 1
    assert data['association_address'] in parts['word/document.xml']
    assert expected in ''.join(parts.values())
    for value in context.values():
        assert value in ''.join(parts.values())
