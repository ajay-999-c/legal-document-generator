"""Render browser attachments in memory; never use the desktop output folder."""
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import quote
from zipfile import ZIP_DEFLATED, ZipFile

from fastapi.responses import Response

from document_generator import render_bytes, safe_component, validate_values
from document_registry import SPECS
from web.services import committee, president

TEMPLATES = {
    'noc': 'Noc_Template.docx', 'registration': 'Registration_Template.docx',
    'by_law': 'By_Law_Template.docx', 'form_a': 'Form_A_Registration_Template.docx',
    'affidavit': 'Affidavit_Template.docx', 'consent': 'Consent_Template.docx',
}
DOCX_TYPE = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'


def render_document(project, kind, member=None):
    spec = SPECS['form_a_registration' if kind == 'form_a' else kind]
    values = {**project.details, **project.settings}
    member = member or {}
    if kind == 'noc':
        values.update(recipient_name=values.get('developer_name', ''), signatory_name=president(project))
    elif kind == 'registration':
        values.update(place=values.get('registration_place', ''),
                      signatory_name=values.get('registration_signatory_name', ''))
    elif kind == 'affidavit':
        values.update(name=member.get('member_name', ''), father_name=member.get('father_name', ''),
                      age=member.get('age', ''), address=member.get('residential_address', ''),
                      plot_no=member.get('plot_no', ''), city=values.get('affidavit_execution_place', ''),
                      member_designation=next((a['designation'] for a in project.committee_members
                                               if a['member_id'] == member.get('member_id')), ''))
    elif kind == 'consent':
        values.update(applicant_name=member.get('member_name', ''),
                      applicant_address=member.get('residential_address', ''),
                      signatory_name=member.get('member_name', ''), plot_no=member.get('plot_no', ''),
                      registration_no=values.get('rera_registration_no', ''),
                      certificate_no=values.get('completion_certificate_no', ''),
                      certificate_date=values.get('completion_certificate_date', ''),
                      place=values.get('consent_place', ''))
    elif kind == 'form_a':
        values['management_committee_address'] = values.get('project_location', '')
    if kind in ('consent', 'form_a'):
        prefix = 'member' if kind == 'consent' else 'committee_member'
        parts = ('name', 'designation') if kind == 'consent' else ('name', 'designation', 'plot_no', 'mobile')
        for i, person in enumerate(committee(project), 1):
            for part in parts:
                values[f'{prefix}_{i}_{part}'] = person.get('member_name' if part == 'name' else part, '')
    # Restrict the input to the adapter contract, including blank optional slots.
    values = {field.parameter: values.get(field.parameter, '') for field in spec.fields}
    values = validate_values(spec, values, SimpleNamespace(input_date_format='%Y-%m-%d'),
                             SimpleNamespace(document_date_format='%d-%m-%Y', blank_document_date='..........'))
    template = Path(__file__).resolve().parents[1] / 'templates' / TEMPLATES[kind]
    return render_bytes(template, spec.context_builder(values))


def attachment(data, filename, media_type):
    return Response(data, media_type=media_type, headers={
        'Content-Disposition': f"attachment; filename*=UTF-8''{quote(filename, safe='')}",
        'Cache-Control': 'no-store',
        'X-Content-Type-Options': 'nosniff',
    })


def project_download(project, kind):
    data = render_document(project, kind)
    return attachment(data, f'{kind}_{safe_component(project.details["project_name"])}.docx', DOCX_TYPE)


def members_download(project, kind):
    stream = BytesIO()
    with ZipFile(stream, 'w', ZIP_DEFLATED) as archive:
        for index, member in enumerate(project.members.values(), 1):
            data = render_document(project, kind, member)
            archive.writestr(f'{kind}_{index}_{safe_component(member["member_name"])}.docx', data)
    return attachment(stream.getvalue(), f'{kind}_{safe_component(project.details["project_name"])}.zip',
                      'application/zip')
