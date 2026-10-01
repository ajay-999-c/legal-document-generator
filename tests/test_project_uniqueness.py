"""Uniqueness is enforced at the write boundary, including concurrent requests."""
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
from fastapi.testclient import TestClient
from web.app import create_app
from web.repository import Project, InMemoryProjectRepository, DuplicateProjectNameError
from web.sheets_repository import SheetsProjectRepository
from tests.test_web_sheets import FakeBook


@pytest.fixture(params=['memory', 'sheets'])
def repo(request):
    if request.param == 'memory':
        return InMemoryProjectRepository()
    book = FakeBook()
    repository = SheetsProjectRepository(lambda: book)
    repository.initialize()
    return repository


def project(key, name, association='Society'):
    return Project(key, {'project_name': name, 'association_name': association})


@pytest.mark.parametrize('name', ['Sample Gardens', ' sample gardens ', 'SAMPLE   GARDENS', 'Sample\tGardens'])
def test_name_unique_regardless_of_id_association_case_or_spaces(repo, name):
    repo.save(project('one', 'Sample Gardens'))
    with pytest.raises(DuplicateProjectNameError):
        repo.save(project('two', name, 'Different society'))
    assert len(repo.list()) == 1


def test_edit_same_project_and_reject_rename_collision(repo):
    repo.save(project('one', 'First'))
    repo.save(project('two', 'Second'))
    first = repo.get('one')
    first.details['association_name'] = 'Updated society'
    repo.save(first)
    first.details['project_name'] = ' second '
    with pytest.raises(DuplicateProjectNameError):
        repo.save(first)
    assert repo.get('one').details['project_name'] == 'First'
    assert repo.get('two').details['project_name'] == 'Second'
    first.details['project_name'] = 'Third'
    repo.save(first)
    assert repo.get('one').details['project_name'] == 'Third'


def test_simultaneous_duplicate_saves_create_one_record(repo):
    barrier = Barrier(2)
    def save(key):
        barrier.wait(timeout=5)
        try:
            repo.save(project(key, 'परीक्षण परियोजना'))
            return 'saved'
        except DuplicateProjectNameError:
            return 'duplicate'
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(save, ['one', 'two']))
    assert sorted(results) == ['duplicate', 'saved']
    assert len(repo.list()) == 1


def test_double_post_retains_form_values_without_overwriting(repo):
    with TestClient(create_app(repository=repo)) as client:
        values = {'project_name': 'TEST Unique', 'association_name': 'Original society'}
        assert client.post('/projects/new', data=values, follow_redirects=False).status_code == 303
        response = client.post('/projects/new', data={**values, 'association_name': 'Second society'})
        assert response.status_code == 409
        assert 'already exists' in response.text
        assert 'Second society' in response.text
        assert len(repo.list()) == 1
        assert repo.list()[0].details['association_name'] == 'Original society'


def test_edit_collision_returns_form_error(repo):
    repo.save(project('one', 'First'))
    repo.save(project('two', 'Second'))
    first = repo.get('one')
    with TestClient(create_app(repository=repo)) as client:
        response = client.post('/projects/one/details', data={
            'project_name': 'Second', 'association_name': 'Society', '_revision': first.revision})
        assert response.status_code == 409
        assert 'already exists' in response.text
    assert repo.get('one').details['project_name'] == 'First'
