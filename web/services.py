"""Document readiness and shared project values."""
from web.schema import LABELS, PROJECT_DOCUMENTS, MEMBER_DOCUMENTS

BASE = 'project_name association_name association_address completion_certificate_no completion_certificate_date'.split()
REQUIRED = {
    'builder_noc': 'developer_company developer_address developer_name tehsil district_name association_name project_name association_address rera_registration_no completion_certificate_no completion_certificate_date'.split(),
    'noc': BASE + 'project_location rera_registration_no developer_name developer_address developer_company'.split(),
    'affidavit': BASE + 'rera_registration_no developer_name tehsil affidavit_execution_place'.split(),
    'consent': BASE + 'project_location rera_registration_no consent_place'.split(),
    'registration': 'tehsil project_name association_address police_station association_name registration_place registration_signatory_name'.split(),
    'by_law': 'association_name association_address work_area'.split(),
    'form_a': BASE + 'work_area project_location district_name share_capital price_per_share member_count meeting_chairperson_name proposed_by approved_by'.split(),
}


def committee(project):
    return [{**project.members[a['member_id']], 'designation': a['designation']}
            for a in project.committee_members]


def president(project):
    return next((m['member_name'] for m in committee(project) if m['designation'] == 'अध्यक्ष'), '')


def document_key(kind, member_id=None):
    return f'{kind}:{member_id}' if member_id else kind


def document_state(project, kind, member=None):
    values = {**project.details, **project.settings}
    missing = [LABELS[key] for key in REQUIRED[kind] if not values.get(key)]
    if kind == 'noc' and not president(project):
        missing.append('Committee president / अध्यक्ष')
    if kind in MEMBER_DOCUMENTS:
        fields = ['member_name', 'residential_address', 'plot_no']
        if kind == 'affidavit':
            fields += ['father_name', 'age']
            if not any(a['member_id'] == (member or {}).get('member_id') for a in project.committee_members):
                missing.append('Member designation / सदस्य का पद')
        missing += [LABELS[key] for key in fields if not (member or {}).get(key)]
    if kind in ('consent', 'form_a'):
        members = committee(project)
        minimum = 3 if kind == 'form_a' else 5
        if not minimum <= len(members) <= 11:
            missing.append(f'{minimum}–11 committee assignments')
        if kind == 'form_a':
            if any(not m['mobile'] or not m['plot_no'] for m in members):
                missing.append('Committee members’ plot numbers and mobile numbers')
            count = project.settings.get('member_count', '')
            if not count.isascii() or not count.isdigit() or int(count) < max(1, len(members)):
                missing.append('Declared member count must cover the committee')
    key = document_key(kind, member['member_id'] if member else None)
    status = 'Missing Data' if missing else ('Generated' if key in project.generated else 'Ready')
    return {'key': kind, 'label': {**PROJECT_DOCUMENTS, **MEMBER_DOCUMENTS}[kind],
            'status': status, 'missing': missing}


def project_cards(project):
    return [document_state(project, key) for key in PROJECT_DOCUMENTS]
