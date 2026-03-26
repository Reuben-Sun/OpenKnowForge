from __future__ import annotations

import base64
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import api.ingestors.note_ingestor as note_ingestor
from api.main import app


def _override_paths(monkeypatch: pytest.MonkeyPatch, root: Path) -> None:
    docs_dir = root / 'docs'
    notes_dir = docs_dir / 'notes'
    images_dir = docs_dir / 'assets' / 'images'
    public_dir = docs_dir / '.vitepress' / 'public'

    monkeypatch.setattr(note_ingestor, 'ROOT_DIR', root)
    monkeypatch.setattr(note_ingestor, 'DOCS_DIR', docs_dir)
    monkeypatch.setattr(note_ingestor, 'NOTES_DIR', notes_dir)
    monkeypatch.setattr(note_ingestor, 'IMAGES_DIR', images_dir)
    monkeypatch.setattr(note_ingestor, 'PUBLIC_DIR', public_dir)
    monkeypatch.setattr(note_ingestor, 'NOTES_INDEX_PATH', notes_dir / 'index.md')
    monkeypatch.setattr(note_ingestor, 'SEARCH_INDEX_PATH', public_dir / 'search-index.json')


def _disable_git_commit(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_commit(self: note_ingestor.NoteIngestor, slug: str, action: str) -> dict[str, object]:
        return {
            'committed': False,
            'message': f'disabled in test for {action}:{slug}',
            'hash': '',
            'committed_at': '',
        }

    monkeypatch.setattr(note_ingestor.NoteIngestor, '_git_commit', fake_commit)


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    _override_paths(monkeypatch, tmp_path)
    _disable_git_commit(monkeypatch)
    return TestClient(app)


def test_post_note_creates_markdown_assets_and_indexes(client: TestClient, tmp_path: Path) -> None:
    image_bytes = b'unit-test-image'
    image_data_url = 'data:image/png;base64,' + base64.b64encode(image_bytes).decode('ascii')

    response = client.post(
        '/note',
        json={
            'title': 'Graph Theory',
            'content': 'Graphs model relationships.',
            'tags': ['math', 'graph'],
            'images': [image_data_url],
            'type': 'concept',
            'status': 'draft',
            'related': ['combinatorics'],
            'submitted_at': '2026-03-26T10:00:00+00:00',
        },
    )

    assert response.status_code == 200
    payload = response.json()['result']
    slug = payload['slug']

    note_path = tmp_path / payload['note_path']
    assert note_path.exists()
    note_text = note_path.read_text(encoding='utf-8')
    assert '# Graph Theory' in note_text
    assert 'title: Graph Theory' in note_text
    assert 'created_at: ' in note_text
    assert 'updated_at: ' in note_text
    assert 'submitted_at: ' in note_text
    assert '<img src="/assets/images/' in note_text

    notes_index_text = (tmp_path / 'docs' / 'notes' / 'index.md').read_text(encoding='utf-8')
    assert 'class="notes-cards"' in notes_index_text
    assert f'/notes/{slug}' in notes_index_text

    image_files = list((tmp_path / 'docs' / 'assets' / 'images').glob('*.png'))
    assert len(image_files) == 1

    search_index_path = tmp_path / 'docs' / '.vitepress' / 'public' / 'search-index.json'
    assert search_index_path.exists()
    search_index = json.loads(search_index_path.read_text(encoding='utf-8'))
    assert search_index['notes'][0]['title'] == 'Graph Theory'
    assert 'math' in search_index['notes'][0]['tags']
    assert search_index['notes'][0]['updated_at'] == '2026-03-26T10:00:00+00:00'

    assert payload['created_at'] == '2026-03-26T10:00:00+00:00'
    assert payload['updated_at'] == '2026-03-26T10:00:00+00:00'
    assert payload['submitted_at'] == '2026-03-26T10:00:00+00:00'


def test_get_note_returns_structured_note(client: TestClient) -> None:
    create = client.post(
        '/note',
        json={
            'title': 'Read API Test',
            'content': 'Initial content',
            'tags': ['api'],
            'images': [],
            'type': 'note',
            'status': 'draft',
            'related': [],
            'submitted_at': '2026-03-26T09:00:00+00:00',
        },
    )
    assert create.status_code == 200
    slug = create.json()['result']['slug']

    response = client.get(f'/note/{slug}')
    assert response.status_code == 200

    note = response.json()['result']
    assert note['slug'] == slug
    assert note['title'] == 'Read API Test'
    assert note['content'] == 'Initial content'
    assert note['created_at'] == '2026-03-26T09:00:00+00:00'
    assert note['updated_at'] == '2026-03-26T09:00:00+00:00'


def test_put_note_updates_last_edited_and_sorting(client: TestClient) -> None:
    a_resp = client.post(
        '/note',
        json={
            'title': 'Alpha Note',
            'content': 'alpha',
            'tags': ['series'],
            'images': [],
            'type': 'note',
            'status': 'draft',
            'related': [],
            'submitted_at': '2026-03-26T09:00:00+00:00',
        },
    )
    assert a_resp.status_code == 200
    a_slug = a_resp.json()['result']['slug']

    b_resp = client.post(
        '/note',
        json={
            'title': 'Beta Note',
            'content': 'beta',
            'tags': ['series'],
            'images': [],
            'type': 'note',
            'status': 'draft',
            'related': [],
            'submitted_at': '2026-03-26T10:00:00+00:00',
        },
    )
    assert b_resp.status_code == 200
    b_slug = b_resp.json()['result']['slug']

    edit_resp = client.put(
        f'/note/{a_slug}',
        json={
            'content': 'alpha updated',
            'status': 'published',
            'submitted_at': '2026-03-26T12:30:00+00:00',
        },
    )
    assert edit_resp.status_code == 200

    edited_note = client.get(f'/note/{a_slug}').json()['result']
    assert edited_note['content'] == 'alpha updated'
    assert edited_note['status'] == 'published'
    assert edited_note['created_at'] == '2026-03-26T09:00:00+00:00'
    assert edited_note['updated_at'] == '2026-03-26T12:30:00+00:00'

    list_resp = client.get('/notes')
    assert list_resp.status_code == 200
    listed = list_resp.json()['result']
    assert listed[0]['slug'] == a_slug
    assert listed[1]['slug'] == b_slug


def test_post_note_rejects_invalid_image_payload(client: TestClient) -> None:
    response = client.post(
        '/note',
        json={
            'title': 'Broken Image Note',
            'content': 'content',
            'tags': [],
            'images': ['not-a-valid-image-format'],
            'type': 'note',
            'status': 'draft',
            'related': [],
        },
    )

    assert response.status_code == 400
    assert 'images entries must be data URLs' in response.json()['detail']


def test_post_note_empty_title_fails_validation(client: TestClient) -> None:
    response = client.post(
        '/note',
        json={
            'title': '',
            'content': 'content',
            'tags': [],
            'images': [],
            'type': 'note',
            'status': 'draft',
            'related': [],
        },
    )

    assert response.status_code == 422
