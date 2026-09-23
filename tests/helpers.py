from copy import deepcopy
from pathlib import Path
import json
import re
from document_registry import SPECS
from sheets_service import STATUS_COLUMNS

FIXTURES = Path(__file__).parent / 'fixtures'


def values(key):
    return json.loads((FIXTURES / f'{key}.json').read_text(encoding='utf-8'))


class FakeSheet:
    def __init__(self, key='noc', records=None):
        spec = SPECS[key]
        self.headers = ['Timestamp', *[f.heading for f in spec.fields], *STATUS_COLUMNS]
        self.data = [self.headers.copy()]
        for record in (records if records is not None else [values(key)]):
            if record is None:
                self.data.append([])
            else:
                self.data.append(['TEST timestamp', *[record.get(f.parameter, '') for f in spec.fields], record.get('processing_status', ''), '', '', ''])
        self.writes = []
        self.fail_statuses = set()
        self.before_read = None

    def get_all_values(self, **kwargs):
        assert kwargs == {'value_render_option': 'FORMATTED_VALUE'}
        return deepcopy(self.data)

    def row_values(self, number):
        if self.before_read:
            self.before_read(self, number)
        return list(self.data[number-1]) if number <= len(self.data) else []

    def batch_update(self, updates, value_input_option):
        assert value_input_option == 'RAW'
        parsed = []
        for update in updates:
            col, number = re.fullmatch(r'([A-Z]+)(\d+)', update['range']).groups()
            index = 0
            for c in col:
                index = index * 26 + ord(c)-64
            assert self.headers[index-1] in STATUS_COLUMNS
            parsed.append((int(number), index-1, update['values'][0][0]))
        status = next((v for _, c, v in parsed if self.headers[c] == 'processing_status'), '')
        if status in self.fail_statuses:
            raise OSError('synthetic write failure')
        self.writes.append(deepcopy(updates))
        for number, index, value in parsed:
            self.data[number-1] += [''] * max(0, len(self.headers)-len(self.data[number-1]))
            self.data[number-1][index] = value
