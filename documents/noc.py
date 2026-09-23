"""Form contract 2026-09-23; exact labels and explicit reviewed aliases."""
from models import DocumentSpec, Field, SetupError

FIELDS = (
    Field('association_name', 'Association / Society Name / एसोसिएशन / संस्था का नाम', 'association_name', True, 'text', ()),
    Field('association_location', 'Association Location / Address / एसोसिएशन का स्थान / पता', 'association_location', True, 'text', ('Association Address / एसोसिएशन का  पता',)),
    Field('document_date', 'Document Date / दस्तावेज़ दिनांक', 'document_date', False, 'date', ()),
    Field('recipient_name', 'Recipient Name / प्राप्तकर्ता का नाम', 'recipient_name', True, 'text', ()),
    Field('developer_company', 'Developer / Partnership Firm Name / विकासकर्ता / भागीदारी फर्म का नाम', 'developer_company', True, 'text', ()),
    Field('developer_address', 'Developer / Firm Address / विकासकर्ता / फर्म का पता', 'developer_address', True, 'text', ()),
    Field('project_name', 'Project Name / परियोजना का नाम', 'project_name', True, 'text', ()),
    Field('khasra_number', 'Khasra Number / खसरा नंबर', 'khasra_number', True, 'text', ()),
    Field('project_location', 'Project Location / परियोजना का स्थान', 'project_location', True, 'text', ()),
    Field('rera_registration_no', 'RERA Registration Number / रेरा पंजीयन क्रमांक', 'rera_registration_no', True, 'text', ()),
    Field('completion_certificate_no', 'Completion Certificate Number / पूर्णता प्रमाण पत्र क्रमांक', 'completion_certificate_no', True, 'text', ()),
    Field('completion_certificate_date', 'Completion Certificate Date / पूर्णता प्रमाण पत्र दिनांक', 'completion_certificate_date', True, 'date', ()),
    Field('signatory_name', 'Signatory Name / हस्ताक्षरकर्ता का नाम', 'signatory_name', True, 'text', ()),
    Field('signatory_role', 'Signatory Role / Designation / हस्ताक्षरकर्ता का पद / पदनाम', 'signatory_role', False, 'text', ()),
)


def build_context(values):
    return {f.placeholder: values[f.parameter] for f in FIELDS}


def check_template(parts):
    import re
    title_pattern = r"{{\s*association_name\s*}}"
    titles = [text.strip() for key, text in parts.items()
              if key.startswith('__paragraph__') and re.search(title_pattern, text)]
    if not titles or any(not re.fullmatch(title_pattern, title) for title in titles):
        raise SetupError("NOC title must contain only association_name; review template city suffix/wording.")


SPEC = DocumentSpec('noc', "2026-09-23", FIELDS, build_context, check_template)
