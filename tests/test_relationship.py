from __future__ import annotations

import contextlib

import pytest
from herogold.orm.model import SELF, BaseModel
from herogold.orm.utils import Relationship, get_foreign_key


class Other(BaseModel):
    pass

class HasRel(BaseModel):
    # relationship pointing at Other, not optional
    other = Relationship(Other)


class HasOpt(BaseModel):
    # optional relationship
    other = Relationship(Other, optional=True)


class Node(BaseModel):
    # self-referential relationship; ``SELF`` sentinel should be replaced
    parent = Relationship(SELF, optional=True)


@pytest.fixture(autouse=True)
def reset_ids():
    # models use plain attributes; ensure no leftover ids
    yield
    for cls in (Other, HasRel, HasOpt, Node):
        with contextlib.suppress(Exception):
            del cls.__fields__


def test_descriptor_returns_class():
    assert HasRel.other is Other
    assert HasOpt.other is Other
    assert Node.parent is Node


def test_instance_access_required():
    o = Other()
    o.id = 1
    h = HasRel()
    # if no foreign-key attribute, __get__ should raise AttributeError in _get_required
    with pytest.raises(AttributeError):
        _ = h.other
    # set the fk to the actual object and verify retrieval
    object.__setattr__(h, "other_id", o)
    assert h.other is o


def test_instance_access_optional():
    o = Other()
    o.id = 2
    h = HasOpt()
    assert h.other is None

    object.__setattr__(h, "other_id", o)
    assert h.other is o


def test_setting_instance_attribute_forbidden():
    h = HasRel()
    with pytest.raises(AttributeError):
        h.other = Other()


def test_selfref_behavior():
    parent = Node()
    parent.id = 10
    child = Node()
    assert child.parent is None
    object.__setattr__(child, "parent_id", parent)
    assert child.parent is parent


# regression: ensure typing does not break at runtime

def test_foreign_key_helper_accepts_generic():
    # simply call get_foreign_key with a subclass
    assert get_foreign_key(Other, "id") == "other.id"
