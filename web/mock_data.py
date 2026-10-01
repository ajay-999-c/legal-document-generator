"""Entirely fictional fixtures; never reads Sheets, credentials or config.yaml."""
from web.repository import Project, InMemoryProjectRepository


def mock_repository():
    project = Project('demo', {
        'project_name': 'TEST · Sample Gardens', 'project_location': 'Demo Nagar',
        'association_name': 'TEST Sample Residents Association',
        'association_address': 'Plot 000, Example Road, Demo Nagar',
        'work_area': 'Sample Gardens test campus', 'association_email': 'office@example.invalid',
        'developer_company': 'TEST Example Developers', 'developer_name': 'TEST Developer Representative', 'developer_address': '00, Demo Business Park',
        'rera_registration_no': 'TEST-RERA-000', 'completion_certificate_no': 'TEST-CC-000',
        'completion_certificate_date': '2025-01-15', 'tehsil': 'Demo Authority',
        'district_name': 'Demo District', 'police_station': 'Demo Police Station',
    })
    names = ['परीक्षण सदस्य एक', 'परीक्षण सदस्य दो', 'परीक्षण सदस्य तीन', 'परीक्षण सदस्य चार', 'परीक्षण सदस्य पाँच']
    for i, name in enumerate(names, 1):
        member_id = f'm{i}'
        project.members[member_id] = {
            'member_id': member_id, 'member_name': name, 'father_name': f'परीक्षण पिता {i}',
            'age': str(30 + i), 'residential_address': f'TEST House {i}, Example Road',
            'plot_no': f'00{i}', 'mobile': f'000000000{i}',
        }
    project.committee_members = [
        {'member_id': f'm{i}', 'designation': role}
        for i, role in enumerate(('अध्यक्ष', 'उपाध्यक्ष', 'सचिव', 'कोषाध्यक्ष', 'सदस्य'), 1)
    ]
    project.settings = {
        'affidavit_execution_place': 'Demo Nagar', 'consent_place': 'Demo Nagar',
        'registration_place': 'Demo Nagar', 'registration_signatory_name': names[0],
        'share_capital': '10000', 'price_per_share': '100', 'member_count': '5',
        'meeting_chairperson_name': names[0], 'proposed_by': names[1], 'approved_by': names[2],
    }
    return InMemoryProjectRepository([project])
