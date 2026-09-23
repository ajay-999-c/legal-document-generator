"""One strict YAML settings source, resolved relative to its own location."""
from pathlib import Path
from string import Formatter
import re
import yaml
from document_registry import SPECS
from models import DocumentSettings, Settings, SetupError

DEFAULT_CONFIG = Path(__file__).resolve().parent / 'config.yaml'
DATE_FORMATS = {'%Y-%m-%d', '%d-%m-%Y', '%m/%d/%Y', '%d/%m/%Y', '%m/%d/%y', '%d/%m/%y'}


class UniqueLoader(yaml.SafeLoader):
    pass


def unique_mapping(loader, node, deep=False):
    result = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if not isinstance(key, str) or key in result:
            raise SetupError('YAML keys must be unique strings.')
        result[key] = loader.construct_object(value_node, deep=deep)
    return result


UniqueLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, unique_mapping)


def mapping(value, keys, location):
    if not isinstance(value, dict) or set(value) != set(keys):
        raise SetupError(f'{location}: expected settings: {", ".join(keys)}.')
    return value


def string(value, location):
    if not isinstance(value, str) or not value.strip():
        raise SetupError(f'{location}: must be a nonblank string.')
    return value.strip()


def validate_pattern(pattern, spec):
    if not pattern.endswith('.docx') or re.search(r'[<>:"/\\|?*\x00-\x1f\x7f]', pattern) or '..' in pattern:
        raise SetupError(f'{spec.key}: filename_pattern must be a safe basename ending in .docx.')
    try:
        parts = list(Formatter().parse(pattern))
    except ValueError as exc:
        raise SetupError(f'{spec.key}: malformed filename_pattern.') from exc
    allowed = {f.parameter for f in spec.fields} | {'row_number'}
    fields = []
    for literal, name, fmt, conversion in parts:
        if name is not None:
            if name not in allowed or fmt or conversion:
                raise SetupError(f'{spec.key}: unsupported filename placeholder or format.')
            fields.append(name)
    if 'row_number' not in fields:
        raise SetupError(f'{spec.key}: filename_pattern must include row_number.')


def load_settings(path=None):
    path = Path(path or DEFAULT_CONFIG).expanduser().resolve()
    try:
        data = yaml.load(path.read_text(encoding='utf-8'), Loader=UniqueLoader)
    except (OSError, yaml.YAMLError) as exc:
        raise SetupError('Cannot read config.yaml; check path and YAML syntax.') from exc
    mapping(data, ('schema_version', 'app', 'google', 'formatting', 'processing', 'documents'), 'config')
    if type(data['schema_version']) is not int or data['schema_version'] != 1:
        raise SetupError('schema_version must be 1.')
    app = mapping(data['app'], ('name', 'log_file', 'log_level'), 'app')
    google = mapping(data['google'], ('spreadsheet_id', 'credentials_file', 'scopes'), 'google')
    formatting = mapping(data['formatting'], ('document_date_format', 'processed_at_format', 'blank_document_date'), 'formatting')
    processing = mapping(data['processing'], ('error_message_max_length',), 'processing')
    def resolve(value, name):
        candidate = Path(string(value, name)).expanduser()
        return (path.parent / candidate).resolve() if not candidate.is_absolute() else candidate.resolve()
    spreadsheet = string(google['spreadsheet_id'], 'spreadsheet_id')
    if not re.fullmatch(r'[A-Za-z0-9_-]{20,}', spreadsheet) or any(p in spreadsheet.upper() for p in ('YOUR_', 'PLACEHOLDER', 'REPLACE_', 'SPREADSHEET_ID')):
        raise SetupError('spreadsheet_id must be the actual bare ID, not a placeholder, URL, or trailing slash.')
    scopes = google['scopes']
    if scopes != ['https://www.googleapis.com/auth/spreadsheets']:
        raise SetupError('google.scopes must contain only the spreadsheets scope.')
    if formatting != {'document_date_format': '%d-%m-%Y', 'processed_at_format': '%d-%m-%Y %H:%M:%S', 'blank_document_date': '..........'}:
        raise SetupError('formatting must follow the agreed DD-MM-YYYY, timestamp and ten-dot contract.')
    limit = processing['error_message_max_length']
    if type(limit) is not int or not 1 <= limit <= 500:
        raise SetupError('error_message_max_length must be an integer from 1 to 500.')
    level = string(app['log_level'], 'log_level').upper()
    if level not in ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'):
        raise SetupError('Invalid log_level.')
    docs = data['documents']
    if not isinstance(docs, dict) or not docs:
        raise SetupError('documents must be a nonempty mapping.')
    configurations = {}
    for key, value in docs.items():
        if not isinstance(value, dict) or type(value.get('enabled')) is not bool:
            raise SetupError(f'{key}: enabled must be true or false.')
        if key not in SPECS:
            if value['enabled']:
                raise SetupError('Unsupported enabled document key.')
            continue
        mapping(value, ('enabled', 'label', 'worksheet_name', 'template_path', 'output_dir', 'filename_pattern', 'input_date_format'), key)
        for field in ('label', 'worksheet_name', 'filename_pattern', 'input_date_format'):
            string(value[field], f'{key}.{field}')
        if value['input_date_format'] not in DATE_FORMATS:
            raise SetupError(f'{key}: unsupported input_date_format; configure an explicit year/month/day format.')
        validate_pattern(value['filename_pattern'], SPECS[key])
        configurations[key] = DocumentSettings(key, value['enabled'], value['label'], value['worksheet_name'], resolve(value['template_path'], 'template_path'), resolve(value['output_dir'], 'output_dir'), value['filename_pattern'], value['input_date_format'])
    enabled = [d for d in configurations.values() if d.enabled]
    if len({d.worksheet_name for d in enabled}) != len(enabled):
        raise SetupError('Enabled documents must use separate worksheet names.')
    if len({d.output_dir for d in enabled}) != len(enabled):
        raise SetupError('Enabled documents must use separate output directories.')
    return Settings(path, spreadsheet, resolve(google['credentials_file'], 'credentials_file'), tuple(scopes), string(app['name'], 'app.name'), resolve(app['log_file'], 'log_file'), level, **formatting, error_message_max_length=limit, documents=configurations)
