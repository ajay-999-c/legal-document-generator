"""Affidavit contract with required member designation and explicit reviewed aliases."""
import re
from models import DocumentSpec, Field, SetupError

FIELDS = (
    Field('name', 'Name / नाम', 'NAME', True, 'text', ()),
    Field('father_name', 'Father’s Name / पिता का नाम', 'FATHER', True, 'text', ("Father's Name / पिता का नाम",)),
    Field('age', 'Age / उम्र', 'AGE', True, 'age', ()),
    Field('address', 'Residential Address / निवास का पता', 'ADDRESS', True, 'text', ()),
    Field('project_name', 'Project Name / परियोजना का नाम', 'PROJECT', True, 'text', ()),
    Field('association_address', 'Association Address / संस्था का पूरा पता', 'association_address'),
    Field('rera_registration_no', 'RERA Registration Number / रेरा पंजीयन क्रमांक', 'RERA', True, 'text', ()),
    Field('developer_name', 'Developer Name / विकासकर्ता का नाम', 'DEVELOPER', True, 'text', ()),
    Field('completion_certificate_no', 'Completion Certificate Number / पूर्णता प्रमाण पत्र क्रमांक', 'CERT_NO', True, 'text', ()),
    Field('completion_certificate_date', 'Completion Certificate Date / पूर्णता प्रमाण पत्र दिनांक', 'CERT_DATE', True, 'date', ()),
    Field('plot_no', 'Plot Number / भूखंड क्रमांक', 'PLOT_NO', True, 'text', ()),
    Field('association_name', 'Association Name / संघ का नाम', 'ASSOCIATION_NAME', True, 'text', ()),
    Field('tehsil', 'Tehsil / तहसील', 'AUTHORITY_LOCATION', True, 'text', ('Authority Location / सक्षम प्राधिकारी का स्थान',)),
    Field('city', 'City / Place / शहर / स्थान', 'CITY', True, 'text', ()),
    Field('member_designation', 'Member Designation / सदस्य का पद', 'MEMBER_DESIGNATION', True, 'text', ()),
)


def build_context(values):
    return {f.placeholder: values[f.parameter] for f in FIELDS}


def check_template(parts):
    body = parts['word/document.xml']
    designations = re.findall(r'कार्यकारिणी\s+{{\s*MEMBER_DESIGNATION\s*}}', body)
    if len(designations) != 4 or body.count('_________') != 3:
        raise SetupError('Affidavit requires four fixed कार्यकारिणी prefixes with MEMBER_DESIGNATION and three manual date blanks.')


SPEC = DocumentSpec('affidavit', '2026-09-29', FIELDS, build_context, check_template)
