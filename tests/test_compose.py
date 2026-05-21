import json
from pathlib import Path

import pytest

from wt.compose import (
    Status,
    compute_status,
    extract_webapp_url,
    find_compose_dir,
    parse_ps_output,
)

FIXTURES = Path(__file__).parent / "fixtures"


def _load(name: str) -> list[dict]:
    return json.loads((FIXTURES / name).read_text())


def test_compute_status_all_running():
    assert compute_status(_load("ps_all_running.json")) is Status.RUNNING


def test_compute_status_all_stopped():
    assert compute_status(_load("ps_all_stopped.json")) is Status.STOPPED


def test_compute_status_mixed():
    assert compute_status(_load("ps_mixed.json")) is Status.PARTIAL


def test_compute_status_empty():
    assert compute_status(_load("ps_empty.json")) is Status.STOPPED


def test_extract_url_prefers_backend():
    services = _load("ps_all_running.json")
    assert extract_webapp_url(services) == "http://localhost:8045"


def test_extract_url_falls_back_to_web():
    services = _load("ps_no_backend_has_web.json")
    assert extract_webapp_url(services) == "http://localhost:3000"


def test_extract_url_single_service_single_port():
    services = _load("ps_single_service.json")
    assert extract_webapp_url(services) == "http://localhost:9000"


def test_extract_url_none_when_stopped():
    services = _load("ps_all_stopped.json")
    assert extract_webapp_url(services) is None


def test_extract_url_none_when_empty():
    services = _load("ps_empty.json")
    assert extract_webapp_url(services) is None


def test_extract_url_none_when_no_publishers():
    services = [{"Service": "backend", "State": "running", "Publishers": []}]
    assert extract_webapp_url(services) is None


def test_parse_ps_output_handles_jsonl():
    jsonl = (
        '{"Service": "backend", "State": "running", "Publishers": [{"PublishedPort": 8045}]}\n'
        '{"Service": "postgres", "State": "running", "Publishers": [{"PublishedPort": 8047}]}\n'
    )
    services = parse_ps_output(jsonl)
    assert len(services) == 2
    assert services[0]["Service"] == "backend"


def test_parse_ps_output_handles_array():
    text = json.dumps(_load("ps_all_running.json"))
    services = parse_ps_output(text)
    assert len(services) == 4


@pytest.mark.parametrize("text", ["", "   \n  "])
def test_parse_ps_output_handles_empty_string(text: str):
    assert parse_ps_output(text) == []


def test_find_compose_dir_root(tmp_path: Path):
    (tmp_path / "compose.yaml").write_text("")
    assert find_compose_dir(tmp_path) == tmp_path


def test_find_compose_dir_subdir(tmp_path: Path):
    (tmp_path / "backend").mkdir()
    (tmp_path / "backend" / "compose.yaml").write_text("")
    assert find_compose_dir(tmp_path) == tmp_path / "backend"


def test_find_compose_dir_root_wins_over_subdir(tmp_path: Path):
    (tmp_path / "compose.yaml").write_text("")
    (tmp_path / "backend").mkdir()
    (tmp_path / "backend" / "compose.yaml").write_text("")
    assert find_compose_dir(tmp_path) == tmp_path


def test_find_compose_dir_none_when_missing(tmp_path: Path):
    assert find_compose_dir(tmp_path) is None


def test_find_compose_dir_does_not_descend_past_depth_one(tmp_path: Path):
    nested = tmp_path / "a" / "b"
    nested.mkdir(parents=True)
    (nested / "compose.yaml").write_text("")
    assert find_compose_dir(tmp_path) is None


def test_find_compose_dir_skips_hidden_subdirs(tmp_path: Path):
    hidden = tmp_path / ".git"
    hidden.mkdir()
    (hidden / "compose.yaml").write_text("")
    assert find_compose_dir(tmp_path) is None


def test_find_compose_dir_alphabetical_when_multiple_subdirs(tmp_path: Path):
    (tmp_path / "zebra").mkdir()
    (tmp_path / "alpha").mkdir()
    (tmp_path / "zebra" / "compose.yaml").write_text("")
    (tmp_path / "alpha" / "compose.yaml").write_text("")
    assert find_compose_dir(tmp_path) == tmp_path / "alpha"


def test_find_compose_dir_accepts_alternate_filenames(tmp_path: Path):
    (tmp_path / "backend").mkdir()
    (tmp_path / "backend" / "docker-compose.yml").write_text("")
    assert find_compose_dir(tmp_path) == tmp_path / "backend"
