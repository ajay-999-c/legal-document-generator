from datetime import date
from pathlib import Path
from urllib.parse import urlencode

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from starlette.concurrency import run_in_threadpool

from models import RowError
from web.downloads import project_download, members_download
from web.repository import Project, new_id, ConflictError, DuplicateProjectNameError
from web.schema import (PROJECT_GROUPS, PROJECT_FIELDS, MEMBER_FIELDS, SETTINGS_GROUPS,
                        SETTINGS_FIELDS, DESIGNATIONS, MEMBER_DOCUMENTS, PROJECT_DOCUMENTS)
from web.services import committee, president, document_key, document_state, project_cards

router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parents[1] / 'templates'))


def get_project(request, project_id):
    project = request.app.state.repository.get(project_id)
    if project is None:
        raise HTTPException(404, 'Project not found')
    return project


def get_member(project, member_id):
    if member_id not in project.members:
        raise HTTPException(404, 'Member not found in this project')
    return project.members[member_id]


def render(request, template, project=None, status_code=200, **context):
    return templates.TemplateResponse(request=request, name=template, status_code=status_code, context={
        'project': project, 'active': '', 'storage_mode': getattr(request.app.state.repository, 'mode', 'demo'), 'message': request.query_params.get('message', ''),
        'error': '', 'president': president(project) if project else '',
        'project_groups': PROJECT_GROUPS, 'member_fields': MEMBER_FIELDS,
        'committee': committee(project) if project else [],
        'member_designations': {a['member_id']: a['designation'] for a in project.committee_members} if project else {},
        'settings_groups': SETTINGS_GROUPS, 'designations': DESIGNATIONS, **context,
    })


def check_revision(request, project, form):
    if getattr(request.app.state.repository, 'mode', 'demo') == 'sheets' and form.get('_revision') != project.revision:
        raise ConflictError('This form is out of date. Reload the project before saving. Your submitted changes were not applied.')


def redirect(path, message=''):
    return RedirectResponse(path + ('?' + urlencode({'message': message}) if message else ''), status_code=303)


def read_values(form, fields, required=()):
    values = {f.key: str(form.get(f.key, '')).strip() for f in fields}
    errors = []
    for f in fields:
        value = values[f.key]
        if f.key in required and not value:
            errors.append(f'{f.label} is required.')
        if len(value) > 2000:
            errors.append(f'{f.label} must be at most 2,000 characters.')
        if not value:
            continue
        if f.kind == 'date':
            try:
                if date.fromisoformat(value).isoformat() != value:
                    raise ValueError
            except ValueError:
                errors.append('Enter a valid completion certificate date.')
        if f.kind == 'number':
            if not value.isascii() or not value.isdigit() or not 1 <= int(value) <= (120 if f.key == 'age' else 1000000):
                errors.append(f'{f.label}: enter a positive whole number' + (' from 1 to 120.' if f.key == 'age' else '.'))
        if f.kind == 'email' and ('@' not in value or ' ' in value):
            errors.append('Enter a valid association email address.')
    return values, ' '.join(errors)


@router.get('/')
@router.get('/projects')
def projects(request: Request, q: str = ''):
    projects = request.app.state.repository.list()
    projects = [p for p in projects if q.casefold() in (p.details['project_name'] + ' ' + p.details['association_name']).casefold()]
    return render(request, 'projects.html', projects=projects, q=q)


@router.get('/projects/new')
def new_project(request: Request):
    return render(request, 'project_form.html', values={}, creating=True)


@router.post('/projects/new')
async def create_project(request: Request):
    values, error = read_values(await request.form(), (*PROJECT_FIELDS, *SETTINGS_FIELDS), ('project_name', 'association_name'))
    if error:
        return render(request, 'project_form.html', values=values, creating=True, error=error, status_code=422)
    project = Project(new_id(), {f.key: values[f.key] for f in PROJECT_FIELDS},
                      settings={f.key: values[f.key] for f in SETTINGS_FIELDS})
    try:
        await run_in_threadpool(request.app.state.repository.save, project)
    except DuplicateProjectNameError as exc:
        return render(request, 'project_form.html', values=values, creating=True, error=str(exc), status_code=409)
    return redirect(f'/projects/{project.project_id}', 'Project created.')


@router.get('/projects/{project_id}')
def overview(request: Request, project_id: str):
    project = get_project(request, project_id)
    return render(request, 'overview.html', project, active='overview', cards=project_cards(project))


@router.get('/projects/{project_id}/details')
def details(request: Request, project_id: str):
    project = get_project(request, project_id)
    return render(request, 'project_form.html', project, active='details', values={**project.details, **project.settings}, creating=False)


@router.post('/projects/{project_id}/details')
async def save_details(request: Request, project_id: str):
    project = await run_in_threadpool(get_project, request, project_id)
    form = await request.form()
    check_revision(request, project, form)
    values, error = read_values({**project.settings, **form}, (*PROJECT_FIELDS, *SETTINGS_FIELDS), ('project_name', 'association_name'))
    if error:
        return render(request, 'project_form.html', project, active='details', values=values, creating=False, error=error, status_code=422)
    project.details = {f.key: values[f.key] for f in PROJECT_FIELDS}
    project.settings = {f.key: values[f.key] for f in SETTINGS_FIELDS}
    project.generated.clear()
    try:
        await run_in_threadpool(request.app.state.repository.save, project)
    except DuplicateProjectNameError as exc:
        return render(request, 'project_form.html', project, active='details', values=values,
                      creating=False, error=str(exc), status_code=409)
    return redirect(f'/projects/{project_id}/details', 'Project details saved. Document readiness refreshed.')


@router.get('/projects/{project_id}/members')
def members(request: Request, project_id: str, q: str = ''):
    project = get_project(request, project_id)
    matches = [m for m in project.members.values() if q.casefold() in ' '.join(m.values()).casefold()]
    return render(request, 'members.html', project, active='members', members=matches, q=q)


@router.get('/projects/{project_id}/members/new')
def new_member(request: Request, project_id: str):
    return render(request, 'member_form.html', get_project(request, project_id), active='members', values={}, editing=False)


@router.get('/projects/{project_id}/members/{member_id}/edit')
def edit_member(request: Request, project_id: str, member_id: str):
    project = get_project(request, project_id)
    return render(request, 'member_form.html', project, active='members', values={**get_member(project, member_id), 'designation': next((a['designation'] for a in project.committee_members if a['member_id'] == member_id), '')}, editing=True)


@router.post('/projects/{project_id}/members/new')
@router.post('/projects/{project_id}/members/{member_id}/edit')
async def save_member(request: Request, project_id: str, member_id: str | None = None):
    project = await run_in_threadpool(get_project, request, project_id)
    if member_id:
        get_member(project, member_id)
    form = await request.form()
    check_revision(request, project, form)
    values, error = read_values(form, MEMBER_FIELDS, ('member_name',))
    existing = next((a for a in project.committee_members if a['member_id'] == member_id), None)
    designation = str(form.get('designation', existing['designation'] if existing else '')).strip()
    if designation:
        error = ' '.join(filter(None, (error, assignment_error(project, member_id, designation))))
    if error:
        return render(request, 'member_form.html', project, active='members', values={**values, 'designation': designation},
                      editing=bool(member_id), error=error, status_code=422)
    member_id = member_id or new_id()
    project.members[member_id] = {**values, 'member_id': member_id}
    if existing:
        if designation:
            existing['designation'] = designation
        else:
            project.committee_members.remove(existing)
    elif designation:
        project.committee_members.append({'member_id': member_id, 'designation': designation})
    project.generated.clear()
    await run_in_threadpool(request.app.state.repository.save, project)
    return redirect(f'/projects/{project_id}/members/{member_id}', 'Member saved. Both document types reuse this record.')


@router.get('/projects/{project_id}/members/{member_id}')
def member_detail(request: Request, project_id: str, member_id: str):
    project = get_project(request, project_id)
    member = get_member(project, member_id)
    return render(request, 'member_detail.html', project, active='members', member=member,
                  cards=[document_state(project, key, member) for key in MEMBER_DOCUMENTS])


def assignment_error(project, member_id, designation):
    error = ''
    if designation not in DESIGNATIONS:
        error = 'Select a listed designation.'
    elif designation == 'अध्यक्ष' and any(a['designation'] == designation and a['member_id'] != member_id for a in project.committee_members):
        error = 'A president is already assigned. Change or remove that assignment before choosing another president.'
    elif len(project.committee_members) >= 11 and not any(a['member_id'] == member_id for a in project.committee_members):
        error = 'The committee supports up to 11 members.'
    return error


@router.get('/projects/{project_id}/committee')
def committee_page(request: Request, project_id: str):
    project = get_project(request, project_id)
    return redirect(f'/projects/{project_id}/members#committee')


@router.post('/projects/{project_id}/committee')
async def save_assignment(request: Request, project_id: str):
    project = await run_in_threadpool(get_project, request, project_id)
    form = await request.form()
    check_revision(request, project, form)
    member_id, designation = str(form.get('member_id', '')), str(form.get('designation', '')).strip()
    get_member(project, member_id)
    error = assignment_error(project, member_id, designation)
    if error:
        return render(request, 'members.html', project, active='members', members=list(project.members.values()), q='', error=error, status_code=422)
    existing = next((a for a in project.committee_members if a['member_id'] == member_id), None)
    if existing:
        existing['designation'] = designation
    else:
        project.committee_members.append({'member_id': member_id, 'designation': designation})
    project.generated.clear()
    await run_in_threadpool(request.app.state.repository.save, project)
    return redirect(f'/projects/{project_id}/members', 'Committee assignment saved.')


@router.post('/projects/{project_id}/committee/{member_id}/remove')
async def remove_assignment(request: Request, project_id: str, member_id: str):
    project = await run_in_threadpool(get_project, request, project_id)
    check_revision(request, project, await request.form())
    get_member(project, member_id)
    project.committee_members = [a for a in project.committee_members if a['member_id'] != member_id]
    project.generated.clear()
    await run_in_threadpool(request.app.state.repository.save, project)
    return redirect(f'/projects/{project_id}/members', 'Committee assignment removed. The member record is retained.')


@router.get('/projects/{project_id}/documents')
def documents(request: Request, project_id: str):
    project = get_project(request, project_id)
    return render(request, 'documents.html', project, active='documents', cards=project_cards(project), values=project.settings)


@router.post('/projects/{project_id}/documents/settings')
async def save_settings(request: Request, project_id: str):
    project = await run_in_threadpool(get_project, request, project_id)
    form = await request.form()
    check_revision(request, project, form)
    values, error = read_values(form, SETTINGS_FIELDS)
    if error:
        return render(request, 'project_form.html', project, active='details', values={**project.details, **values}, creating=False, error=error, status_code=422)
    project.settings = values
    project.generated.clear()
    await run_in_threadpool(request.app.state.repository.save, project)
    return redirect(f'/projects/{project_id}/details', 'Project details saved. Document readiness refreshed.')


@router.post('/projects/{project_id}/documents/{kind}/generate')
async def generate_project(request: Request, project_id: str, kind: str):
    project = await run_in_threadpool(get_project, request, project_id)
    check_revision(request, project, await request.form())
    if kind not in PROJECT_DOCUMENTS:
        raise HTTPException(404, 'Unknown project document')
    state = document_state(project, kind)
    if state['missing']:
        return redirect(f'/projects/{project_id}/documents', 'Cannot generate: ' + '; '.join(state['missing']))
    try:
        download = await run_in_threadpool(project_download, project, kind)
    except RowError as exc:
        return redirect(f'/projects/{project_id}/documents', 'Cannot generate: ' + str(exc))
    project.generated.add(document_key(kind))
    await run_in_threadpool(request.app.state.repository.save, project)
    return download


@router.post('/projects/{project_id}/members/generate')
async def generate_members(request: Request, project_id: str):
    project = await run_in_threadpool(get_project, request, project_id)
    form = await request.form()
    check_revision(request, project, form)
    kind = str(form.get('kind', ''))
    if kind not in MEMBER_DOCUMENTS:
        raise HTTPException(400, 'Select Affidavit or Consent')
    if 'member_id' in form:
        raise HTTPException(400, 'Member selection is no longer supported. Generate for all project members.')
    members = list(project.members.values())
    if not members:
        return redirect(f'/projects/{project_id}/members', 'Add members before generating documents.')
    incomplete = [m for m in members if document_state(project, kind, m)['missing']]
    if incomplete:
        return redirect(f'/projects/{project_id}/members',
                        f'{len(incomplete)} member(s) need more data. Complete their details before generating for all members. No documents were generated.')
    try:
        download = await run_in_threadpool(members_download, project, kind)
    except RowError as exc:
        return redirect(f'/projects/{project_id}/members', 'Cannot generate: ' + str(exc))
    for member in members:
        project.generated.add(document_key(kind, member['member_id']))
    await run_in_threadpool(request.app.state.repository.save, project)
    return download
