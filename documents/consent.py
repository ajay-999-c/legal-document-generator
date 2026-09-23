"""Form contract 2026-09-23; exact labels and explicit reviewed aliases."""
from models import DocumentSpec, Field, SetupError

FIELDS = (
    Field('society_name', 'Society / Association Name / संस्था / एसोसिएशन का नाम', 'society_name', True, 'text', ()),
    Field('society_address', 'Society Address / संस्था का पता', 'society_address', True, 'text', ()),
    Field('applicant_name', 'Applicant Name / आवेदक का नाम', 'applicant_name', True, 'text', ()),
    Field('applicant_address', 'Applicant Address / आवेदक का पता', 'applicant_address', True, 'text', ()),
    Field('project_name', 'Project Name / परियोजना का नाम', 'project_name', True, 'text', ()),
    Field('survey_numbers', 'Survey / Khasra Numbers / सर्वे / खसरा नंबर', 'survey_numbers', True, 'text', ()),
    Field('project_location', 'Project Location / परियोजना का स्थान', 'project_location', True, 'text', ()),
    Field('registration_no', 'RERA Registration Number / रेरा पंजीयन क्रमांक', 'registration_no', True, 'text', ()),
    Field('certificate_no', 'Completion Certificate Number / पूर्णता प्रमाण पत्र नंबर', 'certificate_no', True, 'text', ()),
    Field('certificate_date', 'Completion Certificate Date / पूर्णता प्रमाण पत्र दिनांक', 'certificate_date', True, 'date', ()),
    Field('plot_no', 'Plot / Khand Number / प्लॉट / खंड नंबर', 'plot_no', True, 'text', ()),
    Field('member_name_1', 'Member 1 Name / सदस्य 1 का नाम', 'members[0].name', True, 'text', ()),
    Field('member_designation_1', 'Member 1 Designation / सदस्य 1 का पद / दायित्व', 'members[0].designation', True, 'text', ()),
    Field('member_name_2', 'Member 2 Name / सदस्य 2 का नाम', 'members[1].name', True, 'text', ()),
    Field('member_designation_2', 'Member 2 Designation / सदस्य 2 का पद / दायित्व', 'members[1].designation', True, 'text', ()),
    Field('member_name_3', 'Member 3 Name / सदस्य 3 का नाम', 'members[2].name', True, 'text', ()),
    Field('member_designation_3', 'Member 3 Designation / सदस्य 3 का पद / दायित्व', 'members[2].designation', True, 'text', ()),
    Field('member_name_4', 'Member 4 Name / सदस्य 4 का नाम', 'members[3].name', True, 'text', ()),
    Field('member_designation_4', 'Member 4 Designation / सदस्य 4 का पद / दायित्व', 'members[3].designation', True, 'text', ()),
    Field('member_name_5', 'Member 5 Name / सदस्य 5 का नाम', 'members[4].name', True, 'text', ()),
    Field('member_designation_5', 'Member 5 Designation / सदस्य 5 का पद / दायित्व', 'members[4].designation', True, 'text', ()),
    Field('place', 'Place / स्थान', 'place', True, 'text', ()),
    Field('document_date', 'Document Date / दस्तावेज़ दिनांक', 'document_date', False, 'date', ()),
    Field('signatory_name', 'Signatory Name / हस्ताक्षरकर्ता का नाम', 'signatory_name', True, 'text', ()),
)


def build_context(values):
    context = {f.placeholder: values[f.parameter] for f in FIELDS if not f.placeholder.startswith("members[")}
    context["members"] = [{"name": values[f"member_name_{i}"], "designation": values[f"member_designation_{i}"]} for i in range(1, 6)]
    return context


SPEC = DocumentSpec('consent', "2026-09-23", FIELDS, build_context)
