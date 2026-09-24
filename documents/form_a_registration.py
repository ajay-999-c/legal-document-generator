"""Final Form-A contract with one sequential committee shared by every table."""
from collections import Counter
import re

from models import DocumentSpec, Field, RowError, SetupError

SCALAR_FIELDS = (
    Field('association_name', 'Association Name / प्रस्तावित संस्था का नाम', 'association_name'),
    Field('association_address', 'Association Address / संस्था का पता', 'association_address'),
    Field('work_area', 'Work Area / कार्यक्षेत्र', 'work_area'),
    Field('share_capital', 'Share Capital / अंश पूंजी', 'share_capital'),
    Field('price_per_share', 'Price Per Share / प्रति अंश कीमत', 'price_per_share'),
    Field('member_count', 'Number of Members / सदस्यों की संख्या', 'member_count'),
    Field('association_email', 'Association Email / संस्था ईमेल', 'association_email', False),
    Field('project_name', 'Project Name / परियोजना का नाम', 'project_name'),
    Field('completion_certificate_no', 'Completion Certificate Number / पूर्णता प्रमाण-पत्र क्रमांक', 'completion_certificate_no'),
    Field('completion_certificate_date', 'Completion Certificate Date / पूर्णता प्रमाण-पत्र दिनांक', 'completion_certificate_date', True, 'date'),
    Field('district_name', 'District / जिला', 'district_name'),
    Field('management_committee_address', 'Management Committee Address / प्रबंध कार्यकारिणी का पता', 'management_committee_address'),
    Field('meeting_chairperson_name', 'Meeting Chairperson Name / बैठक अध्यक्ष का नाम', 'meeting_chairperson_name'),
    Field('proposed_by', 'Proposed By / प्रस्ताव रखने वाले का नाम', 'proposed_by'),
    Field('approved_by', 'Approved By / अनुमोदन करने वाले का नाम', 'approved_by'),
)
MEMBER_PARTS = (
    ('name', 'Name', 'का नाम'),
    ('designation', 'Designation', 'का पद'),
    ('plot_no', 'Plot Number', 'भूखंड क्रमांक'),
    ('mobile', 'Mobile Number', 'मोबाइल नंबर'),
)
FIELDS = SCALAR_FIELDS + tuple(
    Field(f'committee_member_{i}_{key}', f'Committee Member {i} {english} / समिति सदस्य {i} {hindi}',
          f'committee_members[{i-1}].{key}', i <= 5)
    for i in range(1, 12) for key, english, hindi in MEMBER_PARTS
)

# Exact expressions in the supplied DOCX, including Jinja row-loop locals.
TEMPLATE_PLACEHOLDERS = frozenset(f.placeholder for f in SCALAR_FIELDS) | frozenset((
    'committee_members[0].name', 'committee_members[0].mobile',
    '"%02d"|format(loop.index)', 'loop.index',
    'member.name', 'member.designation', 'member.plot_no', 'member.mobile',
    'committee_members[i].name', 'committee_members[i].designation', 'committee_members[i].plot_no',
))


def committee(values):
    allowed = {f.parameter for f in FIELDS}
    if any(key.startswith('committee_member_') and key not in allowed for key in values):
        raise RowError('committee_members: only members 1–11 with name, designation, plot_no and mobile are supported.')
    members = []
    gap = False
    for i in range(1, 12):
        member = {key: values.get(f'committee_member_{i}_{key}', '') for key, _, _ in MEMBER_PARTS}
        present = [bool(value and str(value).strip()) for value in member.values()]
        if not any(present) and i > 5:
            gap = True
            continue
        if not all(present):
            raise RowError(f'committee_member_{i}: all four fields are required for a populated member; members 1–5 are mandatory.')
        if gap:
            raise RowError(f'committee_member_{i}: optional members must be contiguous; fill earlier members first.')
        members.append(member)
    if not 5 <= len(members) <= 11:
        raise RowError('committee_members: between 5 and 11 complete members are required.')
    return members


def total_members(value, committee_count):
    # Formatted Sheet strings such as 85 and 85.0 represent the same integer.
    # Fractions, exponents, signs, separators, zero and booleans are not accepted.
    if not isinstance(value, str) or not re.fullmatch(r'[0-9]+(?:\.0+)?', value):
        raise RowError('member_count: enter a positive whole number.')
    try:
        count = int(value.split('.')[0])
    except ValueError as exc:
        raise RowError('member_count: invalid whole number.') from exc
    if count < committee_count:
        raise RowError('member_count: must be at least the committee-member count.')
    return count


def check_row(values):
    members = committee(values)
    total_members(values.get('member_count', ''), len(members))


def build_context(values):
    members = committee(values)
    context = {field.placeholder: values[field.parameter] for field in SCALAR_FIELDS}
    context['member_count'] = total_members(values.get('member_count', ''), len(members))
    context['committee_members'] = members
    return context


def check_headers(headers):
    from document_generator import normalize_header
    allowed = {normalize_header(f.heading) for f in FIELDS}
    for header in headers:
        normalized = normalize_header(header)
        if re.match(r'committee member\b', normalized) and normalized not in allowed:
            raise SetupError('Unsupported committee-member column; only the four fields for members 1–11 are accepted.')


def check_template(parts):
    body = parts['word/document.xml']
    if re.findall(r'दिनांक (\.+) को', body) != ['.' * 13]:
        raise SetupError('Form-A meeting date must remain exactly 13 literal dots.')
    blocks = Counter(re.sub(r'\s+', '', block) for name, text in parts.items()
                     if not name.startswith('__') for block in re.findall(r'{%(.*?)%}', text, re.S))
    expected = Counter({'trformemberincommittee_members': 3, 'trendfor': 4,
                        'trforiinrange(member_count)': 1, 'ifi<committee_members|length': 3,
                        'endif': 3, 'else': 1})
    if blocks != expected:
        raise SetupError('Form-A table-loop mismatch; preserve the supplied repeated committee and final-member row loops.')


SPEC = DocumentSpec('form_a_registration', '2026-09-24', FIELDS, build_context,
                    template_check=check_template, template_placeholders=TEMPLATE_PLACEHOLDERS,
                    preflight_values=(('member_count', '85'),), header_check=check_headers,
                    row_check=check_row)
