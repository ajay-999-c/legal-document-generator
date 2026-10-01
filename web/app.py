"""Run with python -m web.app. Local, single-process UI with Sheets persistence."""
from pathlib import Path
import os
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.trustedhost import TrustedHostMiddleware
from web import __version__
from web.mock_data import mock_repository
from web.repository import RepositoryError, ConflictError
from web.routes.ui import router, templates
from web.routes.imports import router as import_router


def create_app(repository=None, *, storage="demo"):
    if storage not in ("demo", "sheets"):
        raise ValueError("LEGAL_WEB_STORAGE must be demo or sheets")
    if repository is None and storage == "sheets":
        from web.sheets_repository import SheetsProjectRepository
        repository = SheetsProjectRepository()
    app = FastAPI(title='Legal Document Manager · Local prototype', version=__version__, docs_url=None, redoc_url=None)
    app.state.repository = repository if repository is not None else mock_repository()
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=['127.0.0.1', 'localhost', 'testserver'])
    app.mount('/static', StaticFiles(directory=str(Path(__file__).parent / 'static')), name='static')
    app.include_router(import_router)
    app.include_router(router)

    @app.exception_handler(RepositoryError)
    async def storage_error(request: Request, exc):
        return templates.TemplateResponse(request=request, name='storage_error.html',
            context={'project': None, 'message': '', 'error': '', 'storage_message': str(exc),
                     'storage_mode': getattr(app.state.repository, 'mode', 'demo')},
            status_code=409 if isinstance(exc, ConflictError) else 503)

    @app.middleware('http')
    async def local_forms(request: Request, call_next):
        origin = request.headers.get('origin')
        if request.method == 'POST' and origin and origin != str(request.base_url).rstrip('/'):
            return HTMLResponse('Cross-origin form submissions are not allowed.', status_code=403)
        return await call_next(request)

    @app.exception_handler(404)
    async def not_found(request: Request, exc):
        return templates.TemplateResponse(request=request, name='error.html', context={'message': '', 'error': '', 'project': None, 'storage_mode': getattr(app.state.repository, 'mode', 'demo')}, status_code=404)

    return app


app = create_app(storage=os.environ.get("LEGAL_WEB_STORAGE", "sheets"))

if __name__ == '__main__':
    import uvicorn
    uvicorn.run('web.app:app', host='127.0.0.1', port=8000)
