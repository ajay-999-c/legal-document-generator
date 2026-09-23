"""Exact worksheet access, formatted strings, and operational-cell-only writes."""
from dataclasses import dataclass
import time
import requests
import gspread
from google.oauth2.service_account import Credentials
from document_generator import heading_map
from models import SetupError

STATUS_COLUMNS = ('processing_status', 'generated_file', 'processed_at', 'error_message')


def read_call(operation):
    """Retry reads only, at most three attempts. Ambiguous writes are not replayed."""
    for attempt in range(3):
        try:
            return operation()
        except (requests.Timeout, requests.ConnectionError, gspread.exceptions.APIError) as exc:
            transient = not isinstance(exc, gspread.exceptions.APIError) or exc.response.status_code in (429, 500, 502, 503, 504)
            if not transient or attempt == 2:
                raise
            time.sleep(0.5 * (2 ** attempt))


def connect(settings, config):
    try:
        credentials = Credentials.from_service_account_file(str(settings.credentials_file), scopes=settings.scopes)
        client = gspread.authorize(credentials)
        client.set_timeout((15, 60))
        book = read_call(lambda: client.open_by_key(settings.spreadsheet_id))
        return read_call(lambda: book.worksheet(config.worksheet_name))
    except Exception as exc:
        raise SetupError(f'{config.key}: cannot open configured worksheet; check credentials, spreadsheet access and exact worksheet name.') from exc


def pad(row, width):
    if any(not isinstance(value, str) for value in row):
        raise SetupError('Sheet transport must return formatted text without numeric conversion.')
    return tuple(row) + ('',) * max(0, width-len(row))


@dataclass(frozen=True)
class SheetSnapshot:
    headers: tuple[str, ...]
    fields: dict[str, int]
    operations: dict[str, int]
    rows: dict[int, tuple[str, ...]]


def snapshot(worksheet, spec):
    values = read_call(lambda: worksheet.get_all_values(value_render_option='FORMATTED_VALUE'))
    if not values:
        raise SetupError('Worksheet has no header row.')
    headers = tuple(values[0])
    operations = {}
    for name in STATUS_COLUMNS:
        if headers.count(name) != 1:
            raise SetupError(f'Operational header must occur exactly once: {name}.')
        operations[name] = headers.index(name)
    fields = heading_map(spec, headers)
    rows = {n: pad(row, len(headers)) for n, row in enumerate(values[1:], 2)}
    return SheetSnapshot(headers, fields, operations, rows)


def unchanged(worksheet, snapshot, number, original):
    headers = tuple(read_call(lambda: worksheet.row_values(1)))
    current = pad(read_call(lambda: worksheet.row_values(number)), len(snapshot.headers))
    return headers == snapshot.headers and current == original


def column_name(index):
    result = ''
    while index:
        index, remainder = divmod(index-1, 26)
        result = chr(65+remainder) + result
    return result


def update_operations(worksheet, snapshot, number, values):
    if not values or set(values) - set(STATUS_COLUMNS):
        raise ValueError('Only operational cells can be written.')
    updates = [{'range': f'{column_name(snapshot.operations[name]+1)}{number}', 'values': [[value]]} for name, value in values.items()]
    # One request, RAW literals. No automatic retries of an uncertain status write.
    worksheet.batch_update(updates, value_input_option='RAW')
