"""Builder NOC uses existing UI Projects values; the printed date stays literal."""
from models import DocumentSpec, Field

FIELDS = (
    Field('developer_company', 'Developer Company / विकासकर्ता फर्म का नाम', 'developer_company'),
    Field('developer_address', 'Developer Address / विकासकर्ता का पता', 'developer_address'),
    Field('developer_name', 'Developer Name / विकासकर्ता का नाम', 'developer_name'),
    Field('tehsil', 'Tehsil / तहसील', 'tehsil'),
    Field('district_name', 'District / जिला', 'district_name'),
    Field('association_name', 'Association Name / संस्था का नाम', 'association_name'),
    Field('project_name', 'Project Name / परियोजना का नाम', 'project_name'),
    Field('association_address', 'Association Address / संस्था का पूरा पता', 'association_address'),
    Field('rera_registration_no', 'RERA Registration No. / रेरा पंजीयन क्रमांक', 'rera_registration_no'),
    Field('completion_certificate_no', 'Completion Certificate No. / पूर्णता प्रमाण पत्र क्रमांक', 'completion_certificate_no'),
    Field('completion_certificate_date', 'Completion Certificate Date / पूर्णता प्रमाण पत्र दिनांक',
          'completion_certificate_date', True, 'date'),
)


def build_context(values):
    return {field.placeholder: values[field.parameter] for field in FIELDS}


SPEC = DocumentSpec('builder_noc', '2026-10-01', FIELDS, build_context)
