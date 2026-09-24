"""Registration contract: final combined address, live headings checked 2026-09-24."""
from models import DocumentSpec, Field

FIELDS = (
    Field('authority_location', 'Authority Location / सक्षम प्राधिकारी का स्थान', 'authority_location'),
    Field('project_name', 'Project Name / परियोजना का नाम', 'project_name'),
    Field('association_address', 'Association Address', 'association_address'),
    Field('police_station', 'Police Station / पुलिस थाना', 'police_station'),
    Field('association_name', 'Association / Society Name / एसोसिएशन / संस्था का नाम', 'association_name'),
    Field('place', 'Place / स्थान', 'place'),
    Field('signatory_name', 'Signatory Name / हस्ताक्षरकर्ता का नाम', 'signatory_name'),
)


def build_context(values):
    return {field.placeholder: values[field.parameter] for field in FIELDS}


SPEC = DocumentSpec('registration', '2026-09-24', FIELDS, build_context)
