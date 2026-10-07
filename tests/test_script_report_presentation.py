"""Static reading is a distinct projection, retaining archive bytes and CSP."""

from contextlib import contextmanager
from types import SimpleNamespace

import pytest

from fastapi import FastAPI
from fastapi.testclient import TestClient

from plotloom.api.project_folder_script import register_project_folder_script_routes
from plotloom.api.project_folder_art import register_project_folder_art_routes
from plotloom.api.project_folder_storyboard_review import register_project_folder_storyboard_review_routes
from plotloom.api.project_folder_cast import register_project_folder_cast_routes
from plotloom.upstream_report_presentation import STATIC_ART_REPORT_STYLE, STATIC_SCRIPT_REPORT_STYLE, static_art_report
from plotloom.upstream_report_presentation import STATIC_STORYBOARD_REPORT_STYLE
from plotloom.upstream_report_presentation import STATIC_CAST_REPORT_STYLE, static_cast_report


def test_static_report_projects_archive_without_permission_or_storage_change() -> None:
    retained = '<!doctype html><html><body><div class="scenes clip">long scenes</div><script>window.bad=true</script></body></html>'

    @contextmanager
    def opened_project(project_id):
        assert project_id == "qa"
        yield SimpleNamespace(script_candidate_report=lambda job: retained)

    app = FastAPI()
    register_project_folder_script_routes(app, opened_project)
    client = TestClient(app)
    url = "/api/v2/projects/qa/script/candidates/job/report"
    archive = client.get(url)
    projected = client.get(url + "?presentation=static")
    assert archive.status_code == projected.status_code == 200
    assert archive.text == retained
    assert projected.text == retained + STATIC_SCRIPT_REPORT_STYLE
    assert client.get(url).text == retained
    assert projected.headers["content-security-policy"] == archive.headers["content-security-policy"] == (
        "sandbox; default-src 'none'; style-src 'unsafe-inline'; img-src data:;")
    assert projected.headers["x-content-type-options"] == "nosniff"
    assert client.get(url + "?presentation=interactive").status_code == 422


def test_art_static_reading_amends_only_owned_start_tags_and_retains_archive() -> None:
    retained = '<!DOCTYPE html>\n<HTML><body><!-- keep --><details class="pr"><summary>A &amp; B</summary><p>&lt;safe&gt; 中文</p></details>\n<button class="zoom" data-src="data:image/png;base64,AA" aria-label="Zoom"><img alt="a &amp; b" src="data:image/png;base64,AA"></button><details class="other">native</details><script>const text="<button class=zoom>";</script></body></HTML>'
    expected = retained.replace('<details class="pr">', '<details class="pr" open>').replace(
        'aria-label="Zoom">', 'aria-label="Zoom" disabled>') + STATIC_ART_REPORT_STYLE
    assert static_art_report(retained) == expected
    assert static_art_report('<details class="pr" open></details><button class="zoom" disabled></button>') == (
        '<details class="pr" open></details><button class="zoom" disabled></button>' + STATIC_ART_REPORT_STYLE)

    @contextmanager
    def opened_project(project_id):
        yield SimpleNamespace(art_candidate_report=lambda job: retained)

    app = FastAPI()
    register_project_folder_art_routes(app, opened_project)
    client = TestClient(app)
    url = "/api/v2/projects/qa/art/candidates/job/report"
    archive = client.get(url)
    projected = client.get(url + "?presentation=static")
    assert archive.text == retained
    assert projected.text == expected
    assert projected.headers["content-security-policy"] == archive.headers["content-security-policy"]
    assert client.get(url).text == retained
    assert client.get(url + "?presentation=interactive").status_code == 422


@pytest.mark.parametrize("separator", ["\r", "\r\n", "\u2028", "\u2029", "\v", "\f"])
@pytest.mark.parametrize("present,style", [(static_art_report, STATIC_ART_REPORT_STYLE), (static_cast_report, STATIC_CAST_REPORT_STYLE)])
def test_prompt_static_reading_preserves_non_lf_text_separators(separator: str, present, style) -> None:
    retained = (
        f'<p>A{separator}B &amp; 中文</p>\n'
        f'<details class="pr" data-note="A{separator}B"><summary>Prompt</summary>'
        f'<p>First{separator}last</p></details>\n'
        f'<p>Middle{separator}retained</p><button class="zoom"><img alt="retained"></button>'
        f'<script>const untouched="A{separator}B";</script>'
    )
    expected = retained.replace(
        f'<details class="pr" data-note="A{separator}B">',
        f'<details class="pr" data-note="A{separator}B" open>',
    ).replace('<button class="zoom">', '<button class="zoom" disabled>')
    assert present(retained) == expected + style


def test_storyboard_static_report_preserves_archive_and_security() -> None:
    retained = '<div class="shots clip">all segments</div><img class="frame" src="segment/f1.png"><script>window.bad=true</script>'

    @contextmanager
    def opened_project(project_id):
        yield SimpleNamespace(storyboard_review_candidate_report=lambda job: retained)

    app = FastAPI()
    register_project_folder_storyboard_review_routes(app, opened_project)
    client = TestClient(app)
    url = "/api/v2/projects/qa/storyboard-source-review/candidates/job/report"
    archive = client.get(url)
    projected = client.get(url + "?presentation=static")
    assert archive.text == retained
    assert projected.text == retained + STATIC_STORYBOARD_REPORT_STYLE
    assert projected.headers["content-security-policy"] == archive.headers["content-security-policy"] == (
        "sandbox; default-src 'none'; style-src 'unsafe-inline'; img-src data:;")
    assert client.get(url).text == retained
    assert client.get(url + "?presentation=interactive").status_code == 422


def test_cast_static_reading_preserves_text_and_disables_only_current_owned_controls() -> None:
    retained = '<p>Keep\rtext &amp; <em>markup</em></p>\n<div class="graph-canvas"><svg><g role="button" tabindex="0">Name</g></svg></div><button class="grow">Relation &amp; text</button><button class="other">Other</button><details class="pr"><summary>Prompt</summary><p>Whole prompt</p></details><button class="zoom"><img src="data:image/png;base64,AA"></button>'
    expected = retained.replace('<div class="graph-canvas">', '<div class="graph-canvas" inert>').replace(
        '<button class="grow">', '<button class="grow" disabled>').replace(
        '<details class="pr">', '<details class="pr" open>').replace(
        '<button class="zoom">', '<button class="zoom" disabled>') + STATIC_CAST_REPORT_STYLE
    assert static_cast_report(retained) == expected
    assert static_cast_report('<div class="graph-canvas" inert></div><button class="grow" disabled>R</button>') == (
        '<div class="graph-canvas" inert></div><button class="grow" disabled>R</button>' + STATIC_CAST_REPORT_STYLE)

    @contextmanager
    def opened_project(project_id):
        yield SimpleNamespace(cast_candidate_report=lambda job: retained)

    app = FastAPI()
    register_project_folder_cast_routes(app, opened_project)
    client = TestClient(app)
    url = "/api/v2/projects/qa/cast/candidates/job/report"
    archive, projected = client.get(url), client.get(url + "?presentation=static")
    assert archive.text == retained
    assert projected.text == expected
    assert projected.headers["content-security-policy"] == archive.headers["content-security-policy"]
    assert client.get(url).text == retained
    assert client.get(url + "?presentation=interactive").status_code == 422
