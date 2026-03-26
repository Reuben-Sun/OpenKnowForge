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
    ui_dir = docs_dir / 'ui'
    ui_zh_dir = ui_dir / 'zh'
    ui_en_dir = ui_dir / 'en'
    ui_notes_zh_dir = ui_zh_dir / 'notes'
    ui_notes_en_dir = ui_en_dir / 'notes'
    en_note_entries_dir = ui_notes_en_dir / 'entries'
    project_dir = docs_dir / 'project'
    user_notes_dir = project_dir / 'entries'
    images_dir = project_dir / 'images'
    legacy_notes_dir = docs_dir / 'notes'
    legacy_user_notes_dir = legacy_notes_dir / 'entries'
    legacy_images_dir = docs_dir / 'assets' / 'images'
    public_dir = docs_dir / 'public'

    monkeypatch.setattr(note_ingestor, 'ROOT_DIR', root)
    monkeypatch.setattr(note_ingestor, 'DOCS_DIR', docs_dir)
    monkeypatch.setattr(note_ingestor, 'UI_DIR', ui_dir)
    monkeypatch.setattr(note_ingestor, 'UI_ZH_DIR', ui_zh_dir)
    monkeypatch.setattr(note_ingestor, 'UI_EN_DIR', ui_en_dir)
    monkeypatch.setattr(note_ingestor, 'UI_NOTES_ZH_DIR', ui_notes_zh_dir)
    monkeypatch.setattr(note_ingestor, 'UI_NOTES_EN_DIR', ui_notes_en_dir)
    monkeypatch.setattr(note_ingestor, 'EN_NOTE_ENTRIES_DIR', en_note_entries_dir)
    monkeypatch.setattr(note_ingestor, 'PROJECT_DIR', project_dir)
    monkeypatch.setattr(note_ingestor, 'USER_NOTES_DIR', user_notes_dir)
    monkeypatch.setattr(note_ingestor, 'IMAGES_DIR', images_dir)
    monkeypatch.setattr(note_ingestor, 'LEGACY_NOTES_DIR', legacy_notes_dir)
    monkeypatch.setattr(note_ingestor, 'LEGACY_USER_NOTES_DIR', legacy_user_notes_dir)
    monkeypatch.setattr(note_ingestor, 'LEGACY_IMAGES_DIR', legacy_images_dir)
    monkeypatch.setattr(note_ingestor, 'PUBLIC_DIR', public_dir)
    monkeypatch.setattr(note_ingestor, 'ZH_NOTES_INDEX_PATH', ui_notes_zh_dir / 'index.md')
    monkeypatch.setattr(note_ingestor, 'EN_NOTES_INDEX_PATH', ui_notes_en_dir / 'index.md')
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
    assert 'word_count: 3' in note_text
    assert 'image_count: 1' in note_text
    assert '<img src="/project/images/' in note_text

    notes_index_text = (tmp_path / 'docs' / 'ui' / 'zh' / 'notes' / 'index.md').read_text(encoding='utf-8')
    assert '<NotesCards />' in notes_index_text
    en_alias_path = tmp_path / 'docs' / 'ui' / 'en' / 'notes' / 'entries' / f'{slug}.md'
    assert en_alias_path.exists()
    alias_text = en_alias_path.read_text(encoding='utf-8')
    assert f'../../../../project/entries/{slug}.md' in alias_text
    assert 'sidebar: false' not in alias_text

    image_files = list((tmp_path / 'docs' / 'project' / 'images').glob('*.png'))
    assert len(image_files) == 1

    search_index_path = tmp_path / 'docs' / 'public' / 'search-index.json'
    assert search_index_path.exists()
    search_index = json.loads(search_index_path.read_text(encoding='utf-8'))
    assert search_index['notes'][0]['title'] == 'Graph Theory'
    assert search_index['notes'][0]['link'] == f'/notes/entries/{slug}'
    assert 'math' in search_index['notes'][0]['tags']
    assert search_index['notes'][0]['updated_at'] == '2026-03-26T10:00:00+00:00'
    assert search_index['notes'][0]['word_count'] == 3
    assert search_index['notes'][0]['image_count'] == 1

    assert payload['created_at'] == '2026-03-26T10:00:00+00:00'
    assert payload['updated_at'] == '2026-03-26T10:00:00+00:00'
    assert payload['submitted_at'] == '2026-03-26T10:00:00+00:00'
    assert payload['word_count'] == 3
    assert payload['image_count'] == 1
    assert payload['uploaded_image_count'] == 1


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
    assert note['word_count'] == 2
    assert note['image_count'] == 0


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
    edit_payload = edit_resp.json()['result']
    assert edit_payload['word_count'] == 2
    assert edit_payload['image_count'] == 0
    assert edit_payload['uploaded_image_count'] == 0

    edited_note = client.get(f'/note/{a_slug}').json()['result']
    assert edited_note['content'] == 'alpha updated'
    assert edited_note['status'] == 'published'
    assert edited_note['created_at'] == '2026-03-26T09:00:00+00:00'
    assert edited_note['updated_at'] == '2026-03-26T12:30:00+00:00'
    assert edited_note['word_count'] == 2
    assert edited_note['image_count'] == 0

    list_resp = client.get('/notes')
    assert list_resp.status_code == 200
    listed = list_resp.json()['result']
    assert listed[0]['slug'] == a_slug
    assert listed[1]['slug'] == b_slug


def test_put_note_cleans_removed_local_images(client: TestClient, tmp_path: Path) -> None:
    image_bytes = b'image-for-update-cleanup'
    image_data_url = 'data:image/png;base64,' + base64.b64encode(image_bytes).decode('ascii')

    create_resp = client.post(
        '/note',
        json={
            'title': 'Cleanup On Update',
            'content': 'has image',
            'tags': ['cleanup'],
            'images': [image_data_url],
            'type': 'note',
            'status': 'published',
            'related': [],
            'submitted_at': '2026-03-26T12:00:00+00:00',
        },
    )
    assert create_resp.status_code == 200
    slug = create_resp.json()['result']['slug']

    image_files = list((tmp_path / 'docs' / 'project' / 'images').glob('*.png'))
    assert len(image_files) == 1
    assert image_files[0].exists()

    update_resp = client.put(
        f'/note/{slug}',
        json={
            'content': 'updated without image references',
            'submitted_at': '2026-03-26T12:30:00+00:00',
        },
    )
    assert update_resp.status_code == 200
    updated_payload = update_resp.json()['result']
    assert len(updated_payload['removed_images']) == 1
    assert updated_payload['image_count'] == 0

    assert not image_files[0].exists()


def test_search_notes_filters_by_query_and_tag(client: TestClient) -> None:
    client.post(
        '/note',
        json={
            'title': 'KL Divergence Formula',
            'content': 'Information theory distance between distributions.',
            'tags': ['math', 'information-theory'],
            'images': [],
            'type': 'concept',
            'status': 'published',
            'related': [],
            'submitted_at': '2026-03-26T11:00:00+00:00',
        },
    )
    client.post(
        '/note',
        json={
            'title': 'Rust Lifetime Notes',
            'content': 'Borrow checker and ownership.',
            'tags': ['rust', 'lang'],
            'images': [],
            'type': 'note',
            'status': 'published',
            'related': [],
            'submitted_at': '2026-03-26T11:30:00+00:00',
        },
    )

    query_resp = client.get('/notes/search', params={'q': 'divergence'})
    assert query_resp.status_code == 200
    query_notes = query_resp.json()['result']
    assert len(query_notes) == 1
    assert query_notes[0]['title'] == 'KL Divergence Formula'
    assert query_notes[0]['word_count'] > 0
    assert query_notes[0]['image_count'] == 0

    tag_resp = client.get('/notes/search', params={'tag': 'rust'})
    assert tag_resp.status_code == 200
    tag_notes = tag_resp.json()['result']
    assert len(tag_notes) == 1
    assert tag_notes[0]['title'] == 'Rust Lifetime Notes'
    assert tag_notes[0]['word_count'] > 0
    assert tag_notes[0]['image_count'] == 0


def test_delete_note_removes_file_and_assets(client: TestClient, tmp_path: Path) -> None:
    image_bytes = b'image-for-delete-test'
    image_data_url = 'data:image/png;base64,' + base64.b64encode(image_bytes).decode('ascii')

    create_resp = client.post(
        '/note',
        json={
            'title': 'Delete Me',
            'content': 'to be removed',
            'tags': ['cleanup'],
            'images': [image_data_url],
            'type': 'note',
            'status': 'published',
            'related': [],
            'submitted_at': '2026-03-26T11:45:00+00:00',
        },
    )
    assert create_resp.status_code == 200
    payload = create_resp.json()['result']
    slug = payload['slug']

    image_files = list((tmp_path / 'docs' / 'project' / 'images').glob('*.png'))
    assert len(image_files) == 1
    assert (tmp_path / payload['note_path']).exists()

    delete_resp = client.delete(f'/note/{slug}')
    assert delete_resp.status_code == 200
    delete_result = delete_resp.json()['result']
    assert delete_result['slug'] == slug
    assert delete_result['note_path'] == payload['note_path']
    assert len(delete_result['deleted_images']) == 1

    assert not (tmp_path / payload['note_path']).exists()
    assert not image_files[0].exists()

    read_deleted = client.get(f'/note/{slug}')
    assert read_deleted.status_code == 404

    listed = client.get('/notes').json()['result']
    assert slug not in [item['slug'] for item in listed]


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


def test_existing_note_stats_are_backfilled_once(client: TestClient, tmp_path: Path) -> None:
    legacy_note_path = tmp_path / 'docs' / 'project' / 'entries' / 'legacy.md'
    legacy_note_path.parent.mkdir(parents=True, exist_ok=True)
    legacy_note_path.write_text(
        '\n'.join(
            [
                '---',
                'title: Legacy Note',
                'tags:',
                '  - legacy',
                'created_at: 2026-03-26T08:00:00+00:00',
                'updated_at: 2026-03-26T08:00:00+00:00',
                'submitted_at: 2026-03-26T08:00:00+00:00',
                'date: 2026-03-26',
                'type: note',
                'status: published',
                'related: []',
                '---',
                '',
                '# Legacy Note',
                '',
                'legacy content line',
                '',
                '![legacy image](/project/images/legacy.png)',
                '',
            ]
        ),
        encoding='utf-8',
    )

    list_resp = client.get('/notes')
    assert list_resp.status_code == 200
    listed = list_resp.json()['result']
    legacy_item = next(item for item in listed if item['slug'] == 'legacy')
    assert legacy_item['word_count'] == 3
    assert legacy_item['image_count'] == 1

    refreshed = legacy_note_path.read_text(encoding='utf-8')
    assert 'word_count: 3' in refreshed
    assert 'image_count: 1' in refreshed
