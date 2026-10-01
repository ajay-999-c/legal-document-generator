"""Explicit discover → review → load flow for historical response data."""
from fastapi import APIRouter, Request, HTTPException
from starlette.concurrency import run_in_threadpool
from web.legacy_import import LegacySource, build_plan
from web.repository import ConflictError, project_name_key
from web.schema import PROJECT_FIELDS, SETTINGS_FIELDS, LABELS
from web.routes.ui import render, redirect, read_values

router = APIRouter()


def candidates(request):
    source = getattr(request.app.state, 'legacy_source', None)
    if source is None:
        if getattr(request.app.state.repository, 'mode', 'demo') != 'sheets':
            return [], ['Previous projects are available in Google Sheets mode. Restart without LEGAL_WEB_STORAGE=demo.']
        source = LegacySource(request.app.state.repository)
    return source.read()


def existing_project(repository, candidate):
    projects = repository.list()
    exact = next((p for p in projects if p.project_id == candidate.project_id), None)
    if exact:
        return exact
    matches = [p for p in projects if project_name_key(p.details.get('project_name','')) == project_name_key(candidate.project_name)]
    if len(matches) > 1:
        raise ConflictError('Several saved projects have this project name. Open the correct project from the dashboard; no import was made.')
    return matches[0] if matches else None


def find_candidate(request, key):
    items, warnings = candidates(request)
    candidate = next((c for c in items if c.key == key), None)
    if candidate is None:
        raise HTTPException(404, 'Previous project not found')
    return candidate, warnings


@router.get('/projects/load')
def load_projects(request: Request, q: str = ''):
    items, warnings = candidates(request)
    projects = request.app.state.repository.list()
    matches = [c for c in items if q.casefold() in (c.project_name+' '+c.association_name).casefold()]
    loaded = {}
    for candidate in matches:
        saved = [p for p in projects if p.project_id == candidate.project_id or
                 project_name_key(p.details.get('project_name','')) == project_name_key(candidate.project_name)]
        if len(saved) == 1:
            loaded[candidate.key] = saved[0].project_id
    return render(request,'load_projects.html',candidates=matches,warnings=warnings,q=q,loaded=loaded)


@router.get('/projects/load/{key}')
def preview_project(request: Request, key: str):
    candidate,warnings = find_candidate(request,key)
    existing = existing_project(request.app.state.repository,candidate)
    if existing:
        return redirect(f'/projects/{existing.project_id}', 'This project is already in your workspace. Its saved data has not been overwritten.')
    plan = build_plan(candidate)
    return render(request,'import_review.html',candidate=candidate,plan=plan,
                  values={**plan['project'].details,**plan['project'].settings},
                  warnings=warnings+plan['warnings'],labels=LABELS)


def commit_import(request, key, form):
    candidate,warnings = find_candidate(request,key)
    existing = existing_project(request.app.state.repository,candidate)
    if existing:
        return redirect(f'/projects/{existing.project_id}', 'This project is already loaded. Saved data was left unchanged.')
    if form.get('_source_revision') != candidate.fingerprint:
        raise ConflictError('The source responses changed since this preview. Open Load Previous Project again to review the latest data.')
    plan = build_plan(candidate)
    values,error = read_values(form,(*PROJECT_FIELDS,*SETTINGS_FIELDS),('project_name','association_name'))
    # Identity stays tied to the reviewed source; rename after loading if needed.
    if values['project_name'] != candidate.project_name or (candidate.association_name and values['association_name'] != candidate.association_name):
        error += ' Project and association names must match the selected source. Rename the project after loading.'
    if error:
        return render(request,'import_review.html',candidate=candidate,plan=plan,values=values,
                      warnings=warnings+plan['warnings'],labels=LABELS,error=error,status_code=422)
    project = plan['project']
    project.details = {f.key:values[f.key] for f in PROJECT_FIELDS}
    project.settings = {f.key:values[f.key] for f in SETTINGS_FIELDS}
    request.app.state.repository.save(project)
    return redirect(f'/projects/{project.project_id}',
                    f'Previous project loaded with {len(project.members)} members and {len(project.committee_members)} committee assignments. Original response sheets were not changed. Review any missing member details before generation.')


@router.post('/projects/load/{key}')
async def import_project(request: Request, key: str):
    form = await request.form()
    return await run_in_threadpool(commit_import,request,key,form)
