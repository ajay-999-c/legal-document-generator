"""Replace this repository boundary when persistence is approved."""
from copy import deepcopy
from dataclasses import dataclass, field
from typing import Protocol
from uuid import uuid4
from threading import RLock
import unicodedata


@dataclass
class Project:
    project_id: str
    details: dict[str, str]
    members: dict[str, dict[str, str]] = field(default_factory=dict)
    committee_members: list[dict[str, str]] = field(default_factory=list)
    settings: dict[str, str] = field(default_factory=dict)
    generated: set[str] = field(default_factory=set)
    revision: str = ""


class RepositoryError(Exception):
    """Safe operator-facing storage error; never exposes cloud exception details."""


class ConflictError(RepositoryError):
    pass


class DuplicateProjectNameError(ConflictError):
    pass


def project_name_key(name):
    """Ignore case and accidental whitespace; preserve the displayed name."""
    return ' '.join(unicodedata.normalize('NFC', name).split()).casefold()


def check_project_name(project, projects):
    key = project_name_key(project.details.get('project_name', ''))
    if not key:
        raise RepositoryError('Project name is required.')
    if any(p.project_id != project.project_id and
           project_name_key(p.details.get('project_name', '')) == key for p in projects):
        raise DuplicateProjectNameError(
            'A project with this name already exists. Open it from Projects to update it. '
            'इस नाम की परियोजना पहले से मौजूद है। नई duplicate entry नहीं बनाई गई।')


class ProjectRepository(Protocol):
    def list(self) -> list[Project]: ...
    def get(self, project_id: str) -> Project | None: ...
    def save(self, project: Project) -> None: ...


class InMemoryProjectRepository:
    mode = "demo"

    def __init__(self, projects=()):
        self._lock = RLock()
        self._projects = {p.project_id: deepcopy(p) for p in projects}

    def list(self):
        with self._lock:
            return deepcopy(list(self._projects.values()))

    def get(self, project_id):
        with self._lock:
            return deepcopy(self._projects.get(project_id))

    def save(self, project):
        with self._lock:
            check_project_name(project, self._projects.values())
            self._projects[project.project_id] = deepcopy(project)


def new_id():
    return uuid4().hex
