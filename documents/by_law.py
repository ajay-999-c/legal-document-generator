"""By-Law contract: three complete business inputs, checked 2026-09-24."""
from models import DocumentSpec, Field

FIELDS = (
    Field('association_name', 'Association Name / संस्था का नाम', 'association_name'),
    Field('association_address', 'Association Address / संस्था का पंजीकृत पता', 'association_address'),
    Field('work_area', 'Work Area / संस्था का कार्यक्षेत्र', 'work_area'),
)


def build_context(values):
    return {field.placeholder: values[field.parameter] for field in FIELDS}


SPEC = DocumentSpec('by_law', '2026-09-24', FIELDS, build_context)
