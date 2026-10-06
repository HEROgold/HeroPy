from __future__ import annotations

import shutil
import subprocess
from io import BytesIO
from typing import TYPE_CHECKING
from zipfile import ZipFile

import pytest
from httpxyz import Client, MockTransport, Request, Response

from herogold.auto_update.connectors import HTTP, GitCheckout, GitHubRelease
from herogold.auto_update.sources import Github, Source

if TYPE_CHECKING:
    from pathlib import Path

GIT = shutil.which("git")


def _git(cwd: Path, *args: str) -> None:
    assert GIT is not None
    subprocess.run(  # noqa: S603
        [GIT, "-c", "user.name=test", "-c", "user.email=test@example.com", *args],
        cwd=cwd,
        check=True,
        capture_output=True,
    )


def _commit(repo: Path, name: str) -> None:
    (repo / name).write_text(name)
    _git(repo, "add", name)
    _git(repo, "commit", "-m", f"add {name}")
    _git(repo, "push", "origin", "HEAD:main")


@pytest.mark.skipif(GIT is None, reason="git is not installed")
def test_git_checkout_fast_forwards_to_upstream(tmp_path: Path) -> None:
    remote, upstream, local = tmp_path / "remote.git", tmp_path / "upstream", tmp_path / "local"
    _git(tmp_path, "init", "--bare", "--initial-branch=main", str(remote))
    _git(tmp_path, "clone", str(remote), str(upstream))
    _git(upstream, "checkout", "-b", "main")
    _commit(upstream, "first.txt")
    _git(tmp_path, "clone", str(remote), str(local))
    connector = GitCheckout(Source("https://example.com/owner/repo"), local)

    assert not connector.has_update

    _commit(upstream, "second.txt")
    assert connector.has_update

    downloaded = connector.download()
    assert not isinstance(downloaded, Exception)
    assert downloaded.install().success
    assert (local / "second.txt").read_text() == "second.txt"
    assert not connector.has_update


def _zipball() -> bytes:
    buffer = BytesIO()
    with ZipFile(buffer, "w") as archive:
        archive.writestr("owner-repo-abc123/pkg/new.txt", "new")
    return buffer.getvalue()


def _github_client() -> Client:
    def handler(request: Request) -> Response:
        if request.url.path == "/repos/owner/repo/releases/latest":
            return Response(
                200,
                json={"tag_name": "v2.0.0", "zipball_url": "https://api.github.com/repos/owner/repo/zipball/v2.0.0"},
            )
        if request.url.path == "/repos/owner/repo/zipball/v2.0.0":
            return Response(200, content=_zipball())
        return Response(404)

    return Client(transport=MockTransport(handler))


@pytest.mark.parametrize(("installed", "expected"), [("1.0.0", True), ("2.0.0", False), ("v2.0.0", False)])
def test_github_release_compares_latest_tag(tmp_path: Path, installed: str, *, expected: bool) -> None:
    source = Github("https://github.com/owner/repo")
    connector = GitHubRelease(source, tmp_path, installed, client=_github_client())

    assert connector.has_update is expected


def test_github_release_installs_archive_contents(tmp_path: Path) -> None:
    source = Github("https://github.com/owner/repo")
    connector = GitHubRelease(source, tmp_path, "1.0.0", client=_github_client())

    downloaded = connector.download()
    assert not isinstance(downloaded, Exception)
    assert downloaded.install().success
    assert (tmp_path / "pkg" / "new.txt").read_text() == "new"
    assert not (tmp_path / "owner-repo-abc123").exists()


def test_http_writes_download_to_destination(tmp_path: Path) -> None:
    client = Client(transport=MockTransport(lambda _request: Response(200, content=b"payload")))
    destination = tmp_path / "file.bin"
    connector = HTTP(Source("https://example.com/file.bin"), destination, client=client)

    downloaded = connector.download()
    assert not isinstance(downloaded, Exception)
    assert downloaded.install().success
    assert destination.read_bytes() == b"payload"


def test_github_source_api_url() -> None:
    source = Github("https://github.com/owner/repo/releases")
    assert source.api_latest_release == "https://api.github.com/repos/owner/repo/releases/latest"
    assert str(source) == "https://github.com/owner/repo"
