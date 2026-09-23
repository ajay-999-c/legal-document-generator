"""Shared validation and strict DOCX rendering, with no cloud operations."""
from collections import Counter
from datetime import datetime
from io import BytesIO
from pathlib import Path
from tempfile import NamedTemporaryFile
from xml.etree import ElementTree as ET
from zipfile import ZipFile
import hashlib
import re
import unicodedata
from docx import Document
from docxtpl import DocxTemplate
from jinja2 import Environment, StrictUndefined
from models import RowError, SetupError

INVALID_XML = re.compile(r'[\x00-\x08\x0b\x0c\x0e-\x1f\ud800-\udfff\ufffe\uffff]')
ENV = Environment(undefined=StrictUndefined, autoescape=True)


def clean(value):
    return '' if value is None else str(value).strip()


def normalize_header(header):
    header = unicodedata.normalize('NFC', str(header)).lstrip('\ufeff')
    return re.sub(r'\s*/\s*', '/', ' '.join(header.split()).casefold())


def heading_map(spec, headers):
    accepted = {}
    for field in spec.fields:
        for heading in (field.heading, *field.aliases):
            norm = normalize_header(heading)
            if norm in accepted and accepted[norm] != field.parameter:
                raise SetupError('Adapter has an ambiguous heading alias.')
            accepted[norm] = field.parameter
    result = {}
    for index, header in enumerate(headers):
        parameter = accepted.get(normalize_header(header))
        if parameter:
            if parameter in result:
                raise SetupError(f'Ambiguous document column: {parameter}.')
            result[parameter] = index
    missing = [f.parameter for f in spec.fields if f.parameter not in result]
    if missing:
        raise SetupError('Missing document columns: ' + ', '.join(missing))
    return result


def validate_values(spec, values, config, settings):
    result = {}
    for field in spec.fields:
        if field.parameter not in values:
            raise RowError(f'{field.parameter}: input is missing.')
        raw = values[field.parameter]
        if raw is not None and not isinstance(raw, str):
            raise RowError(f'{field.parameter}: expected text; verify Sheet value transport.')
        value = clean(raw)
        if not value and field.required:
            raise RowError(f'{field.parameter}: required value is blank.')
        if INVALID_XML.search(value) or any(token in value for token in ('{{', '}}', '{%', '%}')):
            raise RowError(f'{field.parameter}: invalid XML character or template delimiter.')
        if field.kind == 'date':
            if not value:
                value = settings.blank_document_date
            else:
                try:
                    value = datetime.strptime(value, config.input_date_format).strftime(settings.document_date_format)
                except ValueError as exc:
                    raise RowError(f'{field.parameter}: invalid date; expected {config.input_date_format}.') from exc
        elif field.kind == 'age':
            if not re.fullmatch(r'[0-9]{1,3}', value) or not 1 <= int(value) <= 120:
                raise RowError('age: enter a whole number from 1 to 120.')
            value = str(int(value))
        result[field.parameter] = value
    return result


def xml_parts(source):
    with ZipFile(source) as archive:
        result = {}
        for name in archive.namelist():
            if name.endswith('.xml'):
                root = ET.fromstring(archive.read(name))
                result[name] = ''.join(root.itertext())
                if name == 'word/document.xml':
                    result['__paragraphs__'] = '\n'.join(''.join(p.itertext()) for p in root.iter('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}p'))
                if name == 'word/document.xml' or re.fullmatch(r'word/header\d+\.xml', name):
                    for index, paragraph in enumerate(root.iter('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}p')):
                        result[f'__paragraph__{name}:{index}'] = ''.join(paragraph.itertext())
        return result


def template_expressions(parts):
    return Counter(re.sub(r'\s+', '', token) for name, text in parts.items() if not name.startswith('__') for token in re.findall(r'{{(.*?)}}', text, flags=re.S))


def synthetic_values(spec, config):
    """Only used for local preflight; never a substitute for respondent data."""
    return {f.parameter: (datetime(2026, 9, 23).strftime(config.input_date_format) if f.kind == 'date' else '35' if f.kind == 'age' else 'TEST_' + f.parameter) for f in spec.fields}


def render_bytes(template, context):
    try:
        doc = DocxTemplate(template)
        doc.render(context, jinja_env=ENV, autoescape=True)
        stream = BytesIO()
        doc.save(stream)
        data = stream.getvalue()
        parts = xml_parts(BytesIO(data))
        if any('{{' in value or '}}' in value or '{%' in value or '%}' in value for value in parts.values()):
            raise RowError('Unresolved template delimiters remain.')
        Document(BytesIO(data))
        return data
    except RowError:
        raise
    except Exception as exc:
        raise RowError('DOCX rendering failed; check template and field compatibility.') from exc


def preflight_template(spec, config, settings):
    try:
        if not config.template_path.is_file():
            raise SetupError(f'{spec.key}: template file is missing.')
        parts = xml_parts(config.template_path)
        found = set(template_expressions(parts))
        expected = {re.sub(r'\s+', '', f.placeholder) for f in spec.fields}
        if found != expected:
            # Never print unknown template text, which could contain confidential literals.
            raise SetupError(f'{spec.key}: template placeholder mismatch ({len(expected-found)} missing, {len(found-expected)} unexpected).')
        if spec.template_check:
            spec.template_check(parts)
        values = validate_values(spec, synthetic_values(spec, config), config, settings)
        context = spec.context_builder(values)
        unknown = DocxTemplate(config.template_path).get_undeclared_template_variables() - context.keys()
        if unknown:
            raise SetupError(f'{spec.key}: unsupported template variables.')
        render_bytes(config.template_path, context)  # Includes indexed-member strict checks.
    except SetupError:
        raise
    except Exception as exc:
        raise SetupError(f'{spec.key}: template preflight failed; review the DOCX.') from exc


def safe_component(value):
    value = unicodedata.normalize('NFC', str(value))
    safe = ''.join(c if unicodedata.category(c)[0] in {'L', 'M', 'N'} or c in '-_' else '_' for c in value)
    safe = re.sub('_+', '_', safe).strip('_-') or 'document'
    if re.fullmatch(r'(?i)(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])', safe):
        safe = '_' + safe
    if len(safe.encode('utf-8')) > 100:
        safe = safe.encode('utf-8')[:75].decode('utf-8', errors='ignore') + '_' + hashlib.sha256(safe.encode()).hexdigest()[:12]
    return safe


def output_filename(config, values, row_number):
    components = {k: safe_component(v) for k, v in values.items()}
    name = config.filename_pattern.format(**components, row_number=row_number)
    stem = name[:-5]
    # Bound the entire filename, retaining a deterministic digest and row suffix.
    if len(name.encode('utf-8')) > 230:
        digest = hashlib.sha256(name.encode()).hexdigest()[:16]
        stem = stem.encode('utf-8')[:170].decode('utf-8', errors='ignore') + f'_{digest}_{row_number}'
    if re.fullmatch(r'(?i)(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])', stem):
        stem = '_' + stem
    return stem + '.docx'


def preflight_destination(config):
    try:
        config.output_dir.mkdir(parents=True, exist_ok=True)
        with NamedTemporaryFile(dir=config.output_dir, prefix='.access-', suffix='.tmp'):
            pass
    except OSError as exc:
        raise SetupError(f'{config.key}: output directory is not writable.') from exc


def save_atomic(data, destination):
    temporary = None
    try:
        with NamedTemporaryFile(dir=destination.parent, prefix='.docx-', suffix='.tmp', delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(data)
            stream.flush()
        temporary.replace(destination)
    except OSError as exc:
        raise RowError('Document save failed; check destination access and free space.') from exc
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return destination
