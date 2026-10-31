"""Static typing and deprecation behaviour of ``Relationship`` (ticket #72)."""

from __future__ import annotations

import shutil
import subprocess
import sys
import textwrap
import warnings
from pathlib import Path

import pytest

from herogold.orm.core.utils import Relationship

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"

FIXTURE = """
from __future__ import annotations

from typing import assert_type

from herogold.orm.core.model import BaseModel
from herogold.orm.core.utils import Relationship, SelfRelationship


class TypingTarget72(BaseModel, table=True):
    name: str = "t"


class TypingOwner72(BaseModel, table=True):
    rel = Relationship(TypingTarget72)
    parent = SelfRelationship()


def use(owner: TypingOwner72, target: TypingTarget72) -> None:
    assert_type(TypingOwner72.rel, Relationship[TypingTarget72])
    TypingOwner72.rel.link(owner, target)
    assert_type(owner.rel, TypingTarget72 | None)
    owner.rel = target
    owner.rel = None
    assert_type(owner.parent, TypingOwner72 | None)
    owner.parent = owner
    owner.parent = None
"""


def test_pyrefly_accepts_relationship_models(tmp_path: Path) -> None:
    """A table=True model with Relationship and SelfRelationship type checks cleanly."""
    uvx = shutil.which("uvx")
    if uvx is None:
        pytest.skip("uvx is not available")
    file = tmp_path / "fixture_models.py"
    file.write_text(textwrap.dedent(FIXTURE), encoding="utf-8")
    probe = subprocess.run([uvx, "pyrefly", "--version"], capture_output=True, text=True, check=False)  # noqa: S603
    if probe.returncode != 0:
        pytest.skip("pyrefly is not available")
    shutil.copy(ROOT / "pyrefly.toml", tmp_path / "pyrefly.toml")
    result = subprocess.run(  # noqa: S603
        [
            uvx,
            "pyrefly",
            "check",
            "--search-path",
            str(SRC),
            "--python-interpreter-path",
            sys.executable,
            str(file),
        ],
        capture_output=True,
        text=True,
        check=False,
        cwd=tmp_path,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_optional_keyword_warns() -> None:
    """Passing ``optional=`` explicitly emits a DeprecationWarning."""
    from herogold.orm.models.email import Email  # noqa: PLC0415

    with pytest.warns(DeprecationWarning, match="8.0.0"):
        Relationship(Email, optional=True)


def test_no_optional_keyword_does_not_warn() -> None:
    """Omitting ``optional=`` emits no warning."""
    from herogold.orm.models.email import Email  # noqa: PLC0415

    with warnings.catch_warnings():
        warnings.simplefilter("error")
        Relationship(Email)
