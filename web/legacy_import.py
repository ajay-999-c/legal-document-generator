"""Read-only response-sheet discovery and reviewable canonical import plans.

No production adapter imports and no response-sheet writes. Header contract is
snapshotted in legacy_fields.json and checked against adapters in offline tests.
"""
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import unicodedata

import gspread
import yaml

from web.repository import Project, RepositoryError
from web.schema import PROJECT_FIELDS, SETTINGS_FIELDS, MEMBER_FIELDS, DESIGNATIONS

CONTRACT = json.loads(Path(__file__).with_name('legacy_fields.json').read_text())
MAP = {
    'affidavit': {'city': 'affidavit_execution_place'},
    'consent': {'registration_no': 'rera_registration_no', 'certificate_no': 'completion_certificate_no',
                'certificate_date': 'completion_certificate_date', 'place': 'consent_place'},
    'registration': {'place': 'registration_place', 'signatory_name': 'registration_signatory_name'},
    'form_a_registration': {'management_committee_address': 'project_location'},
}
CANONICAL = {f.key for f in (*PROJECT_FIELDS, *SETTINGS_FIELDS)}


def norm(value):
    return ' '.join(unicodedata.normalize('NFC', value).split()).casefold()


def heading(value):
    return re.sub(r'\s*/\s*', '/', norm(value).lstrip('\ufeff'))


def digest(value):
    return sha256(json.dumps(value, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


@dataclass
class SourceRow:
    kind: str
    sheet: str
    row: int
    values: dict
    date_format: str

    @property
    def label(self):
        return f'{self.sheet} · row {self.row}'


@dataclass
class Candidate:
    key: str
    project_name: str
    association_name: str
    rows: list

    @property
    def fingerprint(self):
        return digest([vars(row) for row in self.rows])

    @property
    def project_id(self):
        return 'import-' + self.key[:24]


class LegacySource:
    def __init__(self, repository, configurations=None):
        self.repository = repository
        self.configurations = configurations

    def read(self):
        """Bounded formatted reads preserve source identifiers and physical row numbers."""
        with self.repository._lock:
            try:
                configurations = self.configurations
                if configurations is None:
                    config_path = Path(os.environ.get('LEGAL_WEB_CONFIG', Path(__file__).resolve().parents[1] / 'config.yaml')).expanduser()
                    configurations = yaml.safe_load(config_path.read_text())['documents']
                book = self.repository.book
                metadata = {s['properties']['title']: s['properties'] for s in book.fetch_sheet_metadata()['sheets']}
                result = []
                warnings = []
                for kind in CONTRACT:
                    config = configurations.get(kind)
                    if not config:
                        continue
                    name = config['worksheet_name']
                    if name.startswith('UI '):
                        raise RepositoryError('A response source points to a UI storage tab. Check configuration.')
                    if name not in metadata:
                        warnings.append(f'{name}: worksheet not found; not included.')
                        continue
                    grid = metadata[name]['gridProperties']
                    if grid['rowCount'] > 10000 or grid['columnCount'] > 150:
                        raise RepositoryError(f'{name}: source exceeds the supported import size; narrow the source before importing.')
                    quoted = "'" + name.replace("'", "''") + "'"
                    headers = book.values_get(f'{quoted}!1:1', params={'valueRenderOption':'FORMATTED_VALUE'}).get('values', [[]])[0]
                    indexes = {}
                    for field in CONTRACT[kind]:
                        accepted = {heading(h) for h in field['headings']}
                        matches = [i for i,h in enumerate(headers) if heading(h) in accepted]
                        if len(matches) > 1:
                            raise RepositoryError(f'{name}: ambiguous column for {field["key"]}. Resolve headings before import.')
                        if matches:
                            indexes[field['key']] = matches[0]
                    identity = 'association_name' if kind == 'by_law' else 'project_name'
                    if identity not in indexes:
                        warnings.append(f'{name}: project/association heading not recognized; not included.')
                        continue
                    # <= 45,000 cells per read; no write/status operation on source sheets.
                    chunk_size = max(1, 45000 // max(1, grid['columnCount']))
                    for start in range(2, grid['rowCount'] + 1, chunk_size):
                        end = min(start + chunk_size - 1, grid['rowCount'])
                        a1 = f'{quoted}!A{start}:{gspread.utils.rowcol_to_a1(end, grid["columnCount"])}'
                        rows = book.values_get(a1, params={'valueRenderOption':'FORMATTED_VALUE'}).get('values', [])
                        for number, raw in enumerate(rows, start):
                            values = {key: str(raw[i]).strip() if i < len(raw) else '' for key,i in indexes.items()}
                            if values.get(identity):
                                result.append(SourceRow(kind,name,number,values,config.get('input_date_format','')))
                return group_candidates(result), warnings
            except RepositoryError:
                raise
            except Exception:
                raise RepositoryError('Unable to read previous projects. Check spreadsheet access and source configuration. No records were imported.') from None


def group_candidates(rows):
    groups = {}
    by_laws = []
    for row in rows:
        if row.kind == 'by_law':
            by_laws.append(row)
            continue
        name, association = row.values.get('project_name',''), row.values.get('association_name','')
        if not name:
            continue
        key = digest([norm(name), norm(association)])
        if key not in groups:
            groups[key] = Candidate(key,name,association,[])
        groups[key].rows.append(row)
    # Association-only By-Law rows join only one exact association, never fuzzy matches.
    for row in by_laws:
        matches = [c for c in groups.values() if norm(c.association_name) == norm(row.values['association_name'])]
        if len(matches) == 1:
            matches[0].rows.append(row)
    return sorted(groups.values(), key=lambda c: (norm(c.project_name),norm(c.association_name)))


def build_plan(candidate):
    project = Project(candidate.project_id, {f.key:'' for f in PROJECT_FIELDS}, settings={f.key:'' for f in SETTINGS_FIELDS})
    collected = defaultdict(list)
    warnings = []
    conflicts = {}
    people = []
    rosters = []
    for source in candidate.rows:
        for key, raw in source.values.items():
            target = MAP.get(source.kind, {}).get(key,key)
            if target not in CANONICAL or not raw:
                continue
            value = raw
            if target == 'completion_certificate_date':
                try:
                    if not source.date_format:
                        raise ValueError
                    value = datetime.strptime(raw,source.date_format).date().isoformat()
                except ValueError:
                    warnings.append(f'{source.label}: certificate date could not be read using the configured format; enter it during review.')
                    continue
            if target == 'member_count' and re.fullmatch(r'[0-9]+\.0+', value):
                value = value.split('.')[0]
            if (value,source.label) not in collected[target]:
                collected[target].append((value,source.label))
        if source.kind in ('affidavit','consent'):
            fields = {'member_name':'name','father_name':'father_name','age':'age','residential_address':'address','plot_no':'plot_no'} if source.kind == 'affidavit' else {'member_name':'applicant_name','residential_address':'applicant_address','plot_no':'plot_no'}
            person = {key:source.values.get(alias,'') for key,alias in fields.items()}
            if person.get('member_name'):
                people.append((person,source.label))
        if source.kind in ('consent','form_a_registration'):
            roster = []
            for i in range(1,12):
                prefix = f'committee_member_{i}_' if source.kind == 'form_a_registration' else f'member_{i}_'
                person = {'member_name':source.values.get(prefix+'name',''), 'plot_no':source.values.get(prefix+'plot_no',''), 'mobile':source.values.get(prefix+'mobile','')}
                role = source.values.get(prefix+'designation','')
                if person['member_name']:
                    people.append((person,source.label))
                    roster.append((person,role))
            if roster:
                rosters.append((roster,source.label))
    for key, entries in collected.items():
        values = list(dict.fromkeys(value for value,_ in entries))
        if len(values) == 1:
            target = project.details if key in project.details else project.settings
            target[key] = values[0]
        else:
            conflicts[key] = entries
    # Identity is the selected group, not inferred from a conflicting row.
    project.details['project_name'] = candidate.project_name
    project.details['association_name'] = candidate.association_name
    # Strong matches require name + plot. Name-only records join only a unique identity.
    buckets = defaultdict(list)
    for person,label in people:
        if person.get('plot_no'):
            buckets[(norm(person['member_name']),norm(person['plot_no']))].append((person,label))
    for person,label in people:
        if not person.get('plot_no'):
            matches = [key for key in buckets if key[0] == norm(person['member_name'])]
            key = matches[0] if len(matches) == 1 else (norm(person['member_name']), '')
            buckets[key].append((person,label))
            if len(matches) > 1:
                warnings.append(f'{label}: {person["member_name"]} matches several plots; retained separately for review.')
    member_keys = {}
    for key, entries in sorted(buckets.items()):
        mid = 'member-' + digest([candidate.key,*key])[:24]
        person = {'member_id':mid}
        for field in MEMBER_FIELDS:
            values = list(dict.fromkeys(p.get(field.key,'') for p,_ in entries if p.get(field.key)))
            person[field.key] = values[0] if len(values) == 1 else ''
            if len(values) > 1:
                # Case/whitespace-only name variation does not create a missing name.
                if field.key == 'member_name' and len({norm(v) for v in values}) == 1:
                    person[field.key] = values[0]
                else:
                    warnings.append(f'{entries[0][0]["member_name"]}: conflicting {field.label}: {" / ".join(values)}. Left blank; edit this member after loading.')
        if person['age'] and (not re.fullmatch(r'[0-9]{1,3}',person['age']) or not 1 <= int(person['age']) <= 120):
            warnings.append(f'{person["member_name"]}: invalid age left blank.')
            person['age'] = ''
        if not person['member_name']:
            person['member_name'] = entries[0][0]['member_name']
        project.members[mid] = person
        member_keys[key] = mid
    resolved_rosters = []
    for roster,label in rosters:
        resolved = []
        for person,role in roster:
            matches = [mid for (name,plot),mid in member_keys.items() if name == norm(person['member_name']) and (not person['plot_no'] or plot == norm(person['plot_no']))]
            if len(matches) != 1 or role not in DESIGNATIONS:
                warnings.append(f'{label}: a committee assignment is ambiguous or has an unsupported designation. Assign the committee after loading.')
                resolved = []
                break
            resolved.append({'member_id':matches[0],'designation':role})
        if resolved:
            resolved_rosters.append(resolved)
    if resolved_rosters and len(resolved_rosters) == len(rosters) and all(r == resolved_rosters[0] for r in resolved_rosters):
        roster = resolved_rosters[0]
        if len({a['member_id'] for a in roster}) == len(roster) and sum(a['designation']=='अध्यक्ष' for a in roster) <= 1:
            project.committee_members = roster
    if rosters and not project.committee_members:
        warnings.append('Committee sources do not resolve to one consistent roster. Members are retained; assign their roles after loading.')
    return {'project':project,'conflicts':conflicts,'warnings':list(dict.fromkeys(warnings))}
