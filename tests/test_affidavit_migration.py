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
    assert len(heading_map(spec, headers)) == 15
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


@pytest.mark.parametrize('designation', ['कोषाध्यक्ष', 'अध्यक्ष', 'सचिव', 'सदस्य'])
def test_designation_sheet_row_normalization_context_and_render(settings, designation):
    from document_generator import validate_values
    from sheets_service import snapshot
    from tests.helpers import FakeSheet

    spec = SPECS['affidavit']
    sheet = FakeSheet('affidavit', [{**values('affidavit'), 'member_designation': f'  {designation} \t'}])
    state = snapshot(sheet, spec)
    index = sheet.headers.index('Member Designation / सदस्य का पद')
    assert state.fields['member_designation'] == index
    inputs = {key: state.rows[2][column] for key, column in state.fields.items()}
    cleaned = validate_values(spec, inputs, settings.documents['affidavit'], settings)
    assert cleaned['member_designation'] == designation
    context, output = render(spec, settings, inputs)
    assert context['MEMBER_DESIGNATION'] == designation
    text = xml_parts(BytesIO(output))['word/document.xml']
    assert text.count(f'कार्यकारिणी {designation}') == 4
    assert f'कार्यकारिणी कार्यकारिणी {designation}' not in text
    if designation != 'कोषाध्यक्ष':
        assert 'कोषाध्यक्ष' not in text
    assert not sheet.writes


@pytest.mark.parametrize('blank', ['', ' \t\n ', None])
def test_blank_designation_fails_without_default(settings, blank):
    from models import RowError
    with pytest.raises(RowError, match='member_designation: required value is blank'):
        render(SPECS['affidavit'], settings, {**values('affidavit'), 'member_designation': blank})


def test_missing_designation_sheet_header_rejected():
    from models import SetupError
    spec = SPECS['affidavit']
    with pytest.raises(SetupError, match='Missing document columns: member_designation'):
        heading_map(spec, [f.heading for f in spec.fields if f.parameter != 'member_designation'])


def test_designation_template_inventory(settings):
    from document_generator import template_expressions
    spec = SPECS['affidavit']
    config = settings.documents['affidavit']
    parts = xml_parts(config.template_path)
    expressions = template_expressions(parts)
    assert expressions['MEMBER_DESIGNATION'] == 4
    assert set(expressions) == {f.placeholder for f in spec.fields}
    assert not any('कार्यकारिणी कोषाध्यक्ष' in text for text in parts.values())
    preflight_template(spec, config, settings)


@pytest.mark.parametrize('replacement', ['{{MEMBER_DESIGNATION}}', 'कार्यकारिणी कोषाध्यक्ष'])
def test_template_requires_fixed_prefix_and_dynamic_designation(settings, tmp_path, replacement):
    from dataclasses import replace
    from zipfile import ZipFile
    from models import SetupError
    config = settings.documents['affidavit']
    path = tmp_path / 'invalid-affidavit.docx'
    with ZipFile(config.template_path) as source, ZipFile(path, 'w') as target:
        for entry in source.infolist():
            data = source.read(entry.filename)
            if entry.filename == 'word/document.xml':
                original = 'कार्यकारिणी {{MEMBER_DESIGNATION}}'.encode()
                assert original in data
                data = data.replace(original, replacement.encode(), 1)
            target.writestr(entry, data)
    with pytest.raises(SetupError, match='four fixed कार्यकारिणी prefixes'):
        preflight_template(SPECS['affidavit'], replace(config, template_path=path), settings)
