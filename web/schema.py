"""Canonical UI fields from mater_ui_variables.md (approved UI contract)."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Field:
    key: str
    label: str
    kind: str = 'text'
    required: bool = True


PROJECT_GROUPS = {
    'Project / Association': (
        Field('project_name', 'Project Name / परियोजना का नाम'),
        Field('project_location', 'Project Location / परियोजना का स्थान'),
        Field('association_name', 'Association Name / संस्था का नाम'),
        Field('association_address', 'Association Address / संस्था का पूरा पता', 'textarea'),
        Field('work_area', 'Work Area / कार्यक्षेत्र'),
        Field('association_email', 'Association Email / संस्था ईमेल', 'email', False),
    ),
    'Developer': (
        Field('developer_name', 'Developer Name / विकासकर्ता का नाम'),
        Field('developer_address', 'Developer Address / विकासकर्ता का पता', 'textarea'),
        Field('developer_company', 'Developer Company / विकासकर्ता फर्म का नाम'),
    ),
    'Registration / Certificate': (
        Field('rera_registration_no', 'RERA Registration No. / रेरा पंजीयन क्रमांक'),
        Field('completion_certificate_no', 'Completion Certificate No. / पूर्णता प्रमाण पत्र क्रमांक'),
        Field('completion_certificate_date', 'Completion Certificate Date / पूर्णता प्रमाण पत्र दिनांक', 'date'),
    ),
    'Location / Authority': (
        Field('tehsil', 'Tehsil / तहसील'),
        Field('district_name', 'District / जिला'),
        Field('police_station', 'Police Station / पुलिस थाना'),
    ),
}
MEMBER_FIELDS = (
    Field('member_name', 'Name / सदस्य का नाम'),
    Field('father_name', 'Father Name / पिता का नाम', required=False),
    Field('age', 'Age / उम्र', 'number', False),
    Field('residential_address', 'Residential Address / निवास का पता', 'textarea', False),
    Field('plot_no', 'Plot No. / भूखंड क्रमांक', required=False),
    Field('mobile', 'Mobile / मोबाइल', 'tel', False),
)
SETTINGS_GROUPS = {
    'Affidavit': (Field('affidavit_execution_place', 'Execution Place / शपथ पत्र का स्थान'),),
    'Consent': (Field('consent_place', 'Consent Place / सहमति का स्थान'),),
    'Registration': (
        Field('registration_place', 'Registration Place / पंजीयन का स्थान'),
        Field('registration_signatory_name', 'Registration Signatory / पंजीयन हस्ताक्षरकर्ता'),
    ),
    'Form-A': (
        Field('share_capital', 'Share Capital / अंश पूंजी'),
        Field('price_per_share', 'Price per Share / प्रति अंश कीमत'),
        Field('member_count', 'Declared Member Count / सदस्यों की घोषित संख्या', 'number'),
        Field('meeting_chairperson_name', 'Meeting Chairperson / बैठक अध्यक्ष'),
        Field('proposed_by', 'Proposed By / प्रस्तावक'),
        Field('approved_by', 'Approved By / अनुमोदक'),
    ),
}
PROJECT_FIELDS = tuple(f for fields in PROJECT_GROUPS.values() for f in fields)
SETTINGS_FIELDS = tuple(f for fields in SETTINGS_GROUPS.values() for f in fields)
LABELS = {f.key: f.label for f in (*PROJECT_FIELDS, *MEMBER_FIELDS, *SETTINGS_FIELDS)}
PROJECT_DOCUMENTS = {'noc': 'NOC', 'registration': 'Registration', 'by_law': 'By-Law', 'form_a': 'Form-A'}
MEMBER_DOCUMENTS = {'affidavit': 'Affidavit', 'consent': 'Consent'}
DESIGNATIONS = ('अध्यक्ष', 'उपाध्यक्ष', 'सचिव', 'सह सचिव', 'कोषाध्यक्ष', 'सदस्य')
