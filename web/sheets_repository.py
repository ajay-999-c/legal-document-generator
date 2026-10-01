"""Normalized Sheets storage for the web UI only; legacy response tabs are untouched.

Run `python -m web.sheets_repository check` or `init`. Initialization is explicit;
normal app startup never creates tabs or imports demo data.
"""
from copy import deepcopy
from hashlib import sha256
import json
import os
from pathlib import Path
import re
from threading import RLock

import gspread
from google.oauth2.service_account import Credentials
import yaml

from web.repository import Project, RepositoryError, ConflictError, check_project_name
from web.schema import PROJECT_FIELDS, MEMBER_FIELDS, SETTINGS_FIELDS, DESIGNATIONS

TABLES = {
    'UI Projects': ('project_id', *(f.key for f in PROJECT_FIELDS), *(f.key for f in SETTINGS_FIELDS)),
    'UI Members': ('project_id', 'member_id', *(f.key for f in MEMBER_FIELDS)),
    'UI Committee': ('project_id', 'member_id', 'designation', 'position'),
}
MAX_ROWS = 10000


def open_book():
    """Reuse only existing Google settings, without importing the legacy backend."""
    try:
        config_path = Path(os.environ.get('LEGAL_WEB_CONFIG', Path(__file__).resolve().parents[1] / 'config.yaml')).expanduser().resolve()
        google = yaml.safe_load(config_path.read_text(encoding='utf-8'))['google']
        spreadsheet_id = os.environ.get('LEGAL_WEB_SPREADSHEET_ID', google['spreadsheet_id'])
        if not re.fullmatch(r'[A-Za-z0-9_-]{20,}', spreadsheet_id):
            raise ValueError('Invalid spreadsheet ID')
        credentials_path = Path(google['credentials_file']).expanduser()
        if not credentials_path.is_absolute():
            credentials_path = config_path.parent / credentials_path
        credentials = Credentials.from_service_account_file(str(credentials_path), scopes=['https://www.googleapis.com/auth/spreadsheets'])
        client = gspread.authorize(credentials)
        client.set_timeout((10, 30))
        return client.open_by_key(spreadsheet_id)
    except Exception:
        raise RepositoryError('Cannot connect to Google Sheets. Check the configured spreadsheet, service-account credentials and sharing access.') from None


def encode(project):
    """Canonical rows only. Simulation badges never enter Google Sheets."""
    data = {**project.details, **project.settings, 'project_id': project.project_id}
    return {
        'UI Projects': [[data.get(k, '') for k in TABLES['UI Projects']]],
        'UI Members': [[project.project_id, member_id, *(m.get(f.key, '') for f in MEMBER_FIELDS)]
                       for member_id, m in sorted(project.members.items())],
        'UI Committee': [[project.project_id, a['member_id'], a['designation'], str(i)]
                         for i, a in enumerate(project.committee_members, 1)],
    }


def revision(project):
    return sha256(json.dumps(encode(project), ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def cells_request(sheet_id, row_index, values):
    return {'updateCells': {
        'range': {'sheetId': sheet_id, 'startRowIndex': row_index, 'endRowIndex': row_index + 1,
                  'startColumnIndex': 0, 'endColumnIndex': len(values)},
        'rows': [{'values': [{'userEnteredValue': {'stringValue': value}} for value in values]}],
        'fields': 'userEnteredValue',
    }}


class SheetsProjectRepository:
    mode = 'sheets'

    def __init__(self, book_factory=open_book):
        self._book_factory = book_factory
        self._book = None
        self._lock = RLock()
        self._generated = {}

    @property
    def book(self):
        if self._book is None:
            self._book = self._book_factory()
        return self._book

    def _metadata(self):
        try:
            return {s['properties']['title']: s['properties'] for s in self.book.fetch_sheet_metadata()['sheets']}
        except RepositoryError:
            raise
        except Exception:
            raise RepositoryError('Unable to read Google Sheets. Check your connection and spreadsheet access; no changes were saved.') from None

    def _read(self, allow_missing=False):
        metadata = self._metadata()
        missing = set(TABLES) - set(metadata)
        if missing and not allow_missing:
            raise RepositoryError('Web storage is not initialized. Run: python -m web.sheets_repository init')
        owned = {name: metadata[name] for name in TABLES if name in metadata}
        if any(p.get('sheetType', 'GRID') != 'GRID' or p['gridProperties']['rowCount'] > MAX_ROWS or
               p['gridProperties']['columnCount'] != len(TABLES[name]) for name, p in owned.items()):
            raise RepositoryError('Web storage dimensions changed or exceed the 10,000-row limit. Review the UI tabs before continuing.')
        if not owned:
            return metadata, {}
        try:
            # Exact owned tabs only. Grid values distinguish literal text from formulas.
            result = self.book.fetch_sheet_metadata(params={
                'includeGridData': True,
                'ranges': [f"'{name}'!A1:{gspread.utils.rowcol_to_a1(p['gridProperties']['rowCount'], len(TABLES[name]))}" for name, p in owned.items()],
                'fields': 'sheets(properties,data(startRow,rowData(values(userEnteredValue))))',
            })
        except Exception:
            raise RepositoryError('Unable to read web records from Google Sheets. No changes were saved.') from None
        tables = {}
        for sheet in result.get('sheets', []):
            name = sheet['properties']['title']
            if name not in owned:
                continue
            rows = {}
            for block in sheet.get('data', []):
                for index, raw in enumerate(block.get('rowData', []), block.get('startRow', 0)):
                    values = []
                    for cell in raw.get('values', []):
                        entered = cell.get('userEnteredValue', {})
                        if entered and set(entered) != {'stringValue'}:
                            raise RepositoryError(f'{name}: use plain text cells only; formulas and converted numbers are not supported.')
                        values.append(entered.get('stringValue', ''))
                    if any(values):
                        if len(values) > len(TABLES[name]):
                            raise RepositoryError(f'{name}: unexpected columns; no changes were saved.')
                        rows[index] = values + [''] * (len(TABLES[name]) - len(values))
            # Accept the former column name so existing sheets remain usable.
            if name == 'UI Projects' and 0 in rows:
                rows[0] = ['tehsil' if value == 'authority_location' else value for value in rows[0]]
            if rows.get(0) != list(TABLES[name]):
                raise RepositoryError(f'{name}: headings do not match the web schema. Existing cells were not changed.')
            tables[name] = rows
        if set(tables) != set(owned):
            raise RepositoryError('Incomplete Google Sheets response. No changes were saved.')
        return metadata, tables

    def initialize(self):
        """Create only absent UI tabs, with headers, in one atomic request."""
        with self._lock:
            metadata, _ = self._read(allow_missing=True)
            missing = [name for name in TABLES if name not in metadata]
            ids = {p['sheetId'] for p in metadata.values()}
            next_id = max(ids, default=0) + 1
            requests = []
            for name in missing:
                while next_id in ids:
                    next_id += 1
                sheet_id = next_id
                ids.add(sheet_id)
                next_id += 1
                width = len(TABLES[name])
                requests += [
                    {'addSheet': {'properties': {'sheetId': sheet_id, 'title': name,
                        'gridProperties': {'rowCount': 1000, 'columnCount': width, 'frozenRowCount': 1}}}},
                    {'repeatCell': {'range': {'sheetId': sheet_id}, 'cell': {'userEnteredFormat': {
                        'numberFormat': {'type': 'TEXT'}, 'wrapStrategy': 'WRAP'}}, 'fields': 'userEnteredFormat'}},
                    cells_request(sheet_id, 0, TABLES[name]),
                    {'repeatCell': {'range': {'sheetId': sheet_id, 'startRowIndex': 0, 'endRowIndex': 1},
                        'cell': {'userEnteredFormat': {'backgroundColor': {'red': .14, 'green': .35, 'blue': .53},
                            'textFormat': {'bold': True, 'foregroundColor': {'red': 1, 'green': 1, 'blue': 1}}}},
                        'fields': 'userEnteredFormat.backgroundColor,userEnteredFormat.textFormat'}},
                    {'updateDimensionProperties': {'range': {'sheetId': sheet_id, 'dimension': 'COLUMNS',
                        'startIndex': 0, 'endIndex': width}, 'properties': {'pixelSize': 220}, 'fields': 'pixelSize'}},
                ]
            if requests:
                self._write(requests)
            self._read()
            return missing

    def _decode(self, tables):
        projects = {}
        for row, values in tables['UI Projects'].items():
            if row == 0:
                continue
            data = dict(zip(TABLES['UI Projects'], values))
            project_id = data['project_id']
            if not project_id or project_id in projects:
                raise RepositoryError('UI Projects contains missing or duplicate IDs. Review the storage tabs.')
            projects[project_id] = Project(project_id,
                {f.key: data[f.key] for f in PROJECT_FIELDS}, settings={f.key: data[f.key] for f in SETTINGS_FIELDS})
        for row, values in tables['UI Members'].items():
            if row == 0:
                continue
            data = dict(zip(TABLES['UI Members'], values))
            project = projects.get(data.pop('project_id'))
            member_id = data['member_id']
            if project is None or not member_id or member_id in project.members:
                raise RepositoryError('UI Members contains an invalid project reference or duplicate/missing member ID.')
            project.members[member_id] = data
        assignments = {key: [] for key in projects}
        for row, values in tables['UI Committee'].items():
            if row == 0:
                continue
            project_id, member_id, designation, position = values
            if project_id not in projects or member_id not in projects[project_id].members or designation not in DESIGNATIONS or not re.fullmatch(r'[1-9][0-9]*', position):
                raise RepositoryError('UI Committee contains an invalid member, project, designation or position.')
            assignments[project_id].append((int(position), member_id, designation))
        for project_id, project in projects.items():
            ordered = sorted(assignments[project_id])
            if len({a[0] for a in ordered}) != len(ordered) or len({a[1] for a in ordered}) != len(ordered) or sum(a[2] == 'अध्यक्ष' for a in ordered) > 1 or len(ordered) > 11:
                raise RepositoryError('UI Committee contains duplicate assignments/positions/presidents or more than 11 members.')
            project.committee_members = [{'member_id': mid, 'designation': designation} for _, mid, designation in ordered]
            project.revision = revision(project)
            cache = self._generated.get(project_id)
            if cache and cache[0] == project.revision:
                project.generated = set(cache[1])
        return projects

    def list(self):
        with self._lock:
            _, tables = self._read()
            return list(self._decode(tables).values())

    def get(self, project_id):
        return next((p for p in self.list() if p.project_id == project_id), None)

    def _write(self, requests):
        try:
            # No automatic retry: a lost response can conceal an applied write.
            self.book.batch_update({'requests': requests})
        except Exception:
            raise RepositoryError('Google Sheets did not confirm the save. It may have completed. Reload and check your records before trying again.') from None

    def save(self, project):
        with self._lock:
            metadata, tables = self._read()
            projects = self._decode(tables)
            check_project_name(project, projects.values())
            current = projects.get(project.project_id)
            if (current.revision if current else '') != project.revision:
                raise ConflictError('This project changed after it was opened. Reload the page before saving again.')
            desired = encode(project)
            if current and desired == encode(current):
                self._generated[project.project_id] = (current.revision, set(project.generated))
                return
            # Validate the proposed aggregate using the same relational checks before writing.
            proposed = {name: {0: list(TABLES[name]), **{i: row for i, row in enumerate(rows, 1)}} for name, rows in desired.items()}
            self._decode(proposed)
            requests = []
            for name, new_rows in desired.items():
                rows = tables[name]
                old_indexes = [i for i, row in sorted(rows.items()) if i and row[0] == project.project_id]
                free_indexes = (i for i in range(1, MAX_ROWS) if i not in rows)
                indexes = old_indexes[:]
                while len(indexes) < len(new_rows):
                    try:
                        indexes.append(next(free_indexes))
                    except StopIteration:
                        raise RepositoryError('Web storage is full. No changes were saved.') from None
                capacity = metadata[name]['gridProperties']['rowCount']
                needed = max(indexes, default=0) + 1
                if needed > capacity:
                    requests.append({'appendDimension': {'sheetId': metadata[name]['sheetId'], 'dimension': 'ROWS', 'length': needed - capacity}})
                for offset, index in enumerate(indexes):
                    values = new_rows[offset] if offset < len(new_rows) else [''] * len(TABLES[name])
                    if rows.get(index) != values:
                        requests.append(cells_request(metadata[name]['sheetId'], index, values))
            self._write(requests)
            # Verify saved canonical data, never claim success on an uncertain readback.
            try:
                saved = self.get(project.project_id)
            except RepositoryError:
                raise RepositoryError('Save was sent, but verification failed. Reload and check the records before trying again.') from None
            if saved is None or encode(saved) != desired:
                raise RepositoryError('Saved records could not be verified. Reload before making more changes.')
            project.revision = saved.revision
            self._generated[project.project_id] = (saved.revision, set(project.generated))


def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('check', 'init'))
    args = parser.parse_args()
    repo = SheetsProjectRepository()
    try:
        if args.command == 'init':
            created = repo.initialize()
            print('Created tabs: ' + (', '.join(created) or 'none; already initialized'))
        projects = repo.list()
        print(f'Connected. Projects={len(projects)}, members={sum(len(p.members) for p in projects)}. Legacy worksheets untouched.')
    except RepositoryError as exc:
        print(str(exc))
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
