"""Form contract 2026-09-25; exact labels and explicit reviewed aliases."""
from models import DocumentSpec, Field, SetupError

FIELDS = (
    Field('association_name', 'Association Name / संस्था का नाम', 'association_name'),
    Field('project_location', 'Project Location / परियोजना का स्थान', 'project_location'),
    Field('association_address', 'Association Address / संस्था का पूरा पता', 'association_address'),
    Field('document_date', 'Document Date / दस्तावेज़ दिनांक', 'document_date', False, 'date'),
    Field('recipient_name', 'Recipient Name / प्राप्तकर्ता का नाम', 'recipient_name'),
    Field('developer_company', 'Developer Company / विकासकर्ता फर्म का नाम', 'developer_company'),
    Field('developer_address', 'Developer Address / विकासकर्ता का पता', 'developer_address'),
    Field('project_name', 'Project Name / परियोजना का नाम', 'project_name'),
    Field('rera_registration_no', 'RERA Registration Number / रेरा पंजीयन क्रमांक', 'rera_registration_no'),
    Field('completion_certificate_no', 'Completion Certificate Number / पूर्णता प्रमाण पत्र क्रमांक', 'completion_certificate_no'),
    Field('completion_certificate_date', 'Completion Certificate Date / पूर्णता प्रमाण पत्र दिनांक', 'completion_certificate_date', True, 'date'),
    Field('signatory_name', 'Signatory Name / हस्ताक्षरकर्ता का नाम', 'signatory_name'),
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


SPEC = DocumentSpec('noc', "2026-09-25", FIELDS, build_context, check_template)
