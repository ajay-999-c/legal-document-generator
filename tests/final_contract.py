"""Independent assertions against the user-supplied final business specification."""
import re
from tests.conftest import ROOT
from document_registry import SPECS

SECTIONS = {'noc': '5. NOC', 'affidavit': '6. Affidavit', 'consent': '7. Consent Letter',
            'registration': '8. Registration Application', 'by_law': '9. By-Law',
            'form_a_registration': '10. Form-A Registration'}


def assert_contract(key):
    text = (ROOT / 'FORM_SPEC_FINAL.md').read_text(encoding='utf-8')
    section = text.split('# ' + SECTIONS[key] + '\n')[1].split('\n# ')[0]
    rows = [line.split('|')[1:-1] for line in section.splitlines() if re.match(r'\| \d+ \|', line)]
    expected = [(row[1].strip(), row[4].strip().strip('`'), row[3].strip() == 'Yes') for row in rows]
    if key == 'consent':
        for i in range(1, 12):
            expected += [(f'Member {i} Name / सदस्य {i} का नाम', f'member_{i}_name', i <= 5),
                         (f'Member {i} Designation / सदस्य {i} का पद / दायित्व', f'member_{i}_designation', i <= 5)]
    if key == 'form_a_registration':
        for i in range(1, 12):
            for part, en, hi in [('name', 'Name', 'का नाम'), ('designation', 'Designation', 'का पद'),
                                 ('plot_no', 'Plot Number', 'भूखंड क्रमांक'), ('mobile', 'Mobile Number', 'मोबाइल नंबर')]:
                expected.append((f'Committee Member {i} {en} / समिति सदस्य {i} {hi}', f'committee_member_{i}_{part}', i <= 5))
    assert [(f.heading, f.parameter, f.required) for f in SPECS[key].fields] == expected
