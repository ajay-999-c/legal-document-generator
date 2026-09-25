"""Final Form contract 2026-09-25; exact labels and explicit reviewed aliases."""
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
    Field('authority_location', 'Authority Location / सक्षम प्राधिकारी का स्थान', 'AUTHORITY_LOCATION', True, 'text', ()),
    Field('city', 'City / Place / शहर / स्थान', 'CITY', True, 'text', ()),
)


def build_context(values):
    return {f.placeholder: values[f.parameter] for f in FIELDS}


def check_template(parts):
    body = parts['word/document.xml']
    if 'कार्यकारिणी कोषाध्यक्ष' not in body or body.count('_________') != 3:
        raise SetupError('Affidavit requires its fixed treasurer wording and three manual date blanks.')


SPEC = DocumentSpec('affidavit', '2026-09-25', FIELDS, build_context, check_template)
