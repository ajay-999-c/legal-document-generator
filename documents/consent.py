"""Final 2026-09-25 Consent contract with a single contiguous 5–11-member list."""
import re
from models import DocumentSpec, Field, RowError, SetupError

SCALAR_FIELDS = (
    Field('association_name', 'Association Name / संस्था / एसोसिएशन का नाम', 'association_name'),
    Field('project_location', 'Project Location / परियोजना का स्थान', 'project_location'),
    Field('applicant_name', 'Applicant Name / आवेदक का नाम', 'applicant_name'),
    Field('applicant_address', 'Applicant Address / आवेदक का पता', 'applicant_address'),
    Field('project_name', 'Project Name / परियोजना का नाम', 'project_name'),
    Field('association_address', 'Association Address / संस्था का पूरा पता', 'association_address'),
    Field('registration_no', 'RERA Registration Number / रेरा पंजीयन क्रमांक', 'registration_no'),
    Field('certificate_no', 'Completion Certificate Number / पूर्णता प्रमाण पत्र नंबर', 'certificate_no'),
    Field('certificate_date', 'Completion Certificate Date / पूर्णता प्रमाण पत्र दिनांक', 'certificate_date', True, 'date'),
    Field('plot_no', 'Plot / Khand Number / प्लॉट / खंड नंबर', 'plot_no'),
    Field('place', 'Place / स्थान', 'place'),
    Field('document_date', 'Document Date / दस्तावेज़ दिनांक', 'document_date', False, 'date'),
    Field('signatory_name', 'Signatory Name / हस्ताक्षरकर्ता का नाम', 'signatory_name'),
)
FIELDS = SCALAR_FIELDS + tuple(
    field for i in range(1, 12) for field in (
        Field(f'member_{i}_name', f'Member {i} Name / सदस्य {i} का नाम', f'members[{i-1}].name', i <= 5),
        Field(f'member_{i}_designation', f'Member {i} Designation / सदस्य {i} का पद / दायित्व', f'members[{i-1}].designation', i <= 5),
    )
)


def build_members(values):
    allowed = {f.parameter for f in FIELDS}
    if any(key.startswith('member_') and key not in allowed for key in values):
        raise RowError('members: only name and designation for members 1–11 are supported.')
    members = []
    gap = False
    for i in range(1, 12):
        member = {part: values.get(f'member_{i}_{part}', '') for part in ('name', 'designation')}
        present = [bool(value and str(value).strip()) for value in member.values()]
        if i > 5 and not any(present):
            gap = True
            continue
        if not all(present):
            raise RowError(f'member_{i}: name and designation are required; members 1–5 are mandatory.')
        if gap:
            raise RowError(f'member_{i}: optional members must be contiguous.')
        members.append(member)
    return members


def check_row(values):
    build_members(values)


def build_context(values):
    context = {f.placeholder: values[f.parameter] for f in SCALAR_FIELDS}
    context['members'] = build_members(values)
    return context


def check_headers(headers):
    from document_generator import normalize_header
    accepted = {normalize_header(f.heading) for f in FIELDS}
    for header in headers:
        norm = normalize_header(header)
        if re.match(r'member(?:\s|_)', norm) and norm not in accepted:
            raise SetupError('Unsupported member column: only names/designations for members 1–11 are accepted.')


def check_template(parts):
    blocks = [re.sub(r'\s+', '', block) for name,text in parts.items() if not name.startswith('__')
              for block in re.findall(r'{%(.*?)%}', text, flags=re.S)]
    if blocks != ['trformemberinmembers', 'trendfor']:
        raise SetupError('Consent requires the supplied dynamic member row loop.')


SPEC = DocumentSpec('consent', '2026-09-25', FIELDS, build_context,
                    template_check=check_template,
                    template_placeholders=frozenset(f.placeholder for f in SCALAR_FIELDS) |
                        frozenset(('"%02d"|format(loop.index)', 'member.name', 'member.designation')),
                    header_check=check_headers, row_check=check_row)
