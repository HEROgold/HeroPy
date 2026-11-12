from __future__ import annotations

import contextlib
import subprocess
import sys
import textwrap
import types
import warnings
from typing import TYPE_CHECKING

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm.attributes import set_attribute
from sqlalchemy.pool import StaticPool
from sqlmodel import Field, SQLModel, select

from herogold.orm.core.configure import Storage, configure, declared_annotation_names
from herogold.orm.core.errors import RelationshipConfigurationError
from herogold.orm.core.model import BaseModel
from herogold.orm.core.utils import Relationship

if TYPE_CHECKING:
    from collections.abc import Iterator

    from sqlmodel import Session


class CfgTeam(BaseModel, table=True):
    name: str = ""
    members = Relationship[list["CfgPlayer"]]()


class CfgPlayer(BaseModel, table=True):
    name: str = ""
    team = Relationship["CfgTeam | None"]()  # nothing declared: team_id is generated
    labels = Relationship[list["CfgLabel"]]()
    tags = Relationship[list["CfgTag"]](inverse=None)  # not a pair with CfgTag.first_player
    profile = Relationship["CfgProfile | None"]()


class CfgLabel(BaseModel, table=True):
    text: str = ""


class CfgTag(BaseModel, table=True):
    label: str = ""
    first_player = Relationship["CfgPlayer | None"]()


class CfgProfile(BaseModel, table=True):  # a declared foreign key: this side stores it
    player_id: int | None = Field(default=None, foreign_key="cfgplayer.id", unique=True)
    player = Relationship["CfgPlayer | None"]()


class CfgSale(BaseModel, table=True):
    pass


class CfgSaleProperty(BaseModel, table=True):  # legacy column name
    steam_sale_id: int = Field(foreign_key="cfgsale.id")
    sale = Relationship["CfgSale | None"]()


class CfgSquad(BaseModel, table=True):
    pass


class CfgMatch(BaseModel, table=True):
    home = Relationship["CfgSquad | None"]()
    away = Relationship["CfgSquad"]()


class CfgBadFixture(BaseModel, table=True):  # two declared foreign keys, unrelated names, no pin
    host_id: int | None = Field(default=None, foreign_key="cfgsquad.id")
    guest_id: int | None = Field(default=None, foreign_key="cfgsquad.id")
    home = Relationship["CfgSquad | None"]()


class CfgFixture(BaseModel, table=True):  # the same, pinned by string and by lambda
    host_id: int | None = Field(default=None, foreign_key="cfgsquad.id")
    guest_id: int | None = Field(default=None, foreign_key="cfgsquad.id")
    home = Relationship["CfgSquad | None"](column="host_id")
    away = Relationship["CfgSquad | None"](column=lambda: CfgFixture.guest_id)


class CfgGuild(BaseModel, table=True):
    pass


class CfgPost(BaseModel, table=True):  # a plain int guild_id, unpinned relationship: collision
    guild_id: int | None = None
    guild = Relationship["CfgGuild | None"]()


class CfgPost2(BaseModel, table=True):  # the relationship gets its own column
    guild_id: int | None = None
    guild = Relationship["CfgGuild | None"](column="guild_row_id")


class CfgPost3(BaseModel, table=True):  # the plain int becomes the foreign key on purpose
    guild_id: int | None = None
    guild = Relationship["CfgGuild | None"](column="guild_id")


class CfgNode(BaseModel, table=True):
    name: str = ""
    parent = Relationship["CfgNode | None"]()
    children = Relationship[list["CfgNode"]]()


class CfgCitizen(BaseModel, table=True):  # one-to-one pinned on one side
    passport = Relationship["CfgPassport | None"]()


class CfgPassport(BaseModel, table=True):
    citizen = Relationship["CfgCitizen | None"](column="citizen_id")


class CfgLeft(BaseModel, table=True):  # one-to-one with nothing chosen
    right = Relationship["CfgRight | None"]()


class CfgRight(BaseModel, table=True):
    left = Relationship["CfgLeft | None"]()


class CfgAuthor(BaseModel, table=True):  # ambiguous pairing, resolved with a pin
    books = Relationship[list["CfgBook"]](inverse=lambda: CfgBook.author)
    favourite = Relationship["CfgBook | None"]()


class CfgBook(BaseModel, table=True):
    author = Relationship["CfgAuthor | None"]()


class CfgAuthor2(BaseModel, table=True):  # the same without the pin
    books = Relationship[list["CfgBook2"]]()
    favourite = Relationship["CfgBook2 | None"]()


class CfgBook2(BaseModel, table=True):
    author = Relationship["CfgAuthor2 | None"]()


class CfgCrate(BaseModel, table=True):  # forward reference to a table with a custom name
    warehouse = Relationship["CfgWarehouse | None"]()


class CfgWarehouse(BaseModel, table=True):
    __tablename__ = "cfg_custom_wh"


class CfgAuthor3(BaseModel, table=True):  # the pin sits on the single side
    books = Relationship[list["CfgBook3"]]()


class CfgBook3(BaseModel, table=True):
    author = Relationship["CfgAuthor3 | None"](inverse=lambda: CfgAuthor3.books)


class CfgStudent(BaseModel, table=True):  # many-to-many
    courses = Relationship[list["CfgCourse"]]()


class CfgCourse(BaseModel, table=True):
    students = Relationship[list["CfgStudent"]]()


MODELS = [
    CfgTeam, CfgPlayer, CfgLabel, CfgTag, CfgProfile, CfgSale, CfgSaleProperty, CfgSquad, CfgMatch, CfgBadFixture,
    CfgFixture, CfgGuild, CfgPost, CfgPost2, CfgPost3, CfgNode, CfgCitizen, CfgPassport, CfgLeft, CfgRight,
    CfgAuthor, CfgBook, CfgAuthor2, CfgBook2, CfgCrate, CfgWarehouse, CfgAuthor3, CfgBook3, CfgStudent, CfgCourse,
]  # fmt: skip

COLUMN_BEFORE_CONFIGURE = "team_id" in CfgPlayer.__table__.columns


@pytest.fixture(scope="module", autouse=True)
def errors() -> dict[str, str]:
    try:
        configure(MODELS)
    except RelationshipConfigurationError as exc:
        return exc.errors
    return {}


def fks(model: type, column: str) -> list[str]:
    return [fk.target_fullname for fk in model.__table__.c[column].foreign_keys]


def test_column_is_absent_before_configure() -> None:
    assert not COLUMN_BEFORE_CONFIGURE


def test_configure_generates_the_id_column() -> None:
    assert "team_id" in CfgPlayer.__table__.columns
    assert fks(CfgPlayer, "team_id") == ["cfgteam.id"]
    assert CfgPlayer.__table__.c.team_id.nullable
    assert CfgPlayer.team.placement.storage is Storage.OWNER_COLUMN
    assert CfgTeam.members.placement.storage is Storage.TARGET_COLUMN
    assert CfgTeam.members.placement.column == "team_id"
    assert CfgTeam.members.pair is CfgPlayer.team


def test_required_relationship_generates_a_not_null_column() -> None:
    assert not CfgMatch.__table__.c.away_id.nullable
    assert CfgMatch.__table__.c.home_id.nullable


def test_class_annotations_are_untouched() -> None:
    assert "team_id" not in declared_annotation_names(CfgPlayer)


def test_forward_reference_to_a_custom_table_name() -> None:
    assert fks(CfgCrate, "warehouse_id") == ["cfg_custom_wh.id"]


def test_two_relationships_to_one_target_get_their_own_columns() -> None:
    assert (CfgMatch.home.placement.column, CfgMatch.away.placement.column) == ("home_id", "away_id")


def test_column_pin_by_string_and_by_lambda(errors: dict[str, str]) -> None:
    assert (CfgFixture.home.placement.column, CfgFixture.away.placement.column) == ("host_id", "guest_id")
    assert "CfgFixture.home" not in errors
    assert "home_id" not in CfgFixture.__table__.columns


def test_two_declared_foreign_keys_without_a_pin_raise(errors: dict[str, str]) -> None:
    assert "column=" in errors["CfgBadFixture.home"]


def test_the_only_declared_foreign_key_is_reused() -> None:
    assert CfgSaleProperty.sale.placement.column == "steam_sale_id"
    assert "sale_id" not in CfgSaleProperty.__table__.columns


def test_plain_column_with_the_default_name_raises(errors: dict[str, str]) -> None:
    assert "CfgPost.guild" in errors
    assert "column='guild_id'" in errors["CfgPost.guild"]
    assert not CfgPost.__table__.c.guild_id.foreign_keys


def test_pin_to_another_name_generates_a_separate_column() -> None:
    assert "guild_row_id" in CfgPost2.__table__.columns
    assert CfgPost2.guild.placement.column == "guild_row_id"
    assert not CfgPost2.__table__.c.guild_id.foreign_keys


def test_pin_on_a_plain_column_attaches_the_foreign_key() -> None:
    assert fks(CfgPost3, "guild_id") == ["cfgguild.id"]


def test_one_to_one_is_owned_by_the_side_with_column() -> None:
    assert CfgPassport.citizen.placement.storage is Storage.OWNER_COLUMN
    assert CfgCitizen.passport.placement.storage is Storage.TARGET_COLUMN
    assert "citizen_id" in CfgPassport.__table__.columns
    assert "passport_id" not in CfgCitizen.__table__.columns


def test_one_to_one_is_owned_by_the_side_with_a_declared_foreign_key() -> None:
    assert CfgProfile.player.placement.storage is Storage.OWNER_COLUMN
    assert CfgPlayer.profile.placement.storage is Storage.TARGET_COLUMN
    assert "profile_id" not in CfgPlayer.__table__.columns


def test_one_to_one_with_nothing_chosen_raises_on_both_sides(errors: dict[str, str]) -> None:
    assert "CfgLeft.right" in errors
    assert "CfgRight.left" in errors
    assert "column=" in errors["CfgLeft.right"]


def test_inverse_pin_resolves_an_ambiguous_pair(errors: dict[str, str]) -> None:
    assert CfgAuthor.books.pair is CfgBook.author
    assert CfgAuthor.books.placement.storage is Storage.TARGET_COLUMN
    assert "CfgAuthor.books" not in errors
    assert "CfgAuthor.favourite" not in errors
    assert CfgAuthor.favourite.placement.column == "favourite_id"  # the pinned pair no longer competes for it


def test_inverse_pin_on_the_single_side() -> None:
    assert CfgBook3.author.pair is CfgAuthor3.books
    assert CfgBook3.author.placement.column == "author_id"


def test_ambiguous_pairing_raises_for_every_member(errors: dict[str, str]) -> None:
    for label in ("CfgAuthor2.books", "CfgAuthor2.favourite", "CfgBook2.author"):
        assert label in errors
        assert "inverse=" in errors[label]
    assert "author_id" not in CfgBook2.__table__.columns


def test_ambiguous_relationship_cannot_be_read(errors: dict[str, str]) -> None:
    with pytest.raises(LookupError, match="inverse="):
        CfgBook2().author  # noqa: B018


def test_inverse_none_opts_out_of_pairing() -> None:
    assert CfgPlayer.tags.placement.storage is Storage.LINK
    assert CfgTag.first_player.placement.column == "first_player_id"
    assert CfgTag.first_player.pair is None


def test_lone_list_gets_a_link_table() -> None:
    assert CfgPlayer.labels.placement.storage is Storage.LINK
    assert CfgPlayer.labels.placement.table.name in SQLModel.metadata.tables


def test_many_to_many_shares_one_link_table() -> None:
    assert CfgStudent.courses.placement.storage is Storage.LINK
    assert CfgStudent.courses.placement.table is CfgCourse.students.placement.table
    assert CfgStudent.courses.pair is CfgCourse.students


def test_self_reference_pairs_parent_and_children() -> None:
    assert CfgNode.children.pair is CfgNode.parent
    assert CfgNode.parent.placement.column == "parent_id"
    assert fks(CfgNode, "parent_id") == ["cfgnode.id"]


def test_generated_column_works_in_constructor_attribute_and_where(session: Session) -> None:
    team = CfgTeam(name="t")
    session.add(team)
    session.flush()
    player = CfgPlayer(name="p", team_id=team.id)
    session.add(player)
    session.flush()
    assert player.team_id == team.id
    assert len(session.exec(select(CfgPlayer).where(CfgPlayer.team_id == team.id)).all()) == 1
    set_attribute(player, "team_id", None)
    session.flush()
    assert player.team_id is None


def test_generated_column_is_not_a_pydantic_field(session: Session) -> None:
    player = CfgPlayer(name="p", team_id=None)
    assert "team_id" not in player.model_dump()
    assert "team_id" not in CfgPlayer.model_fields


def test_second_call_changes_nothing() -> None:
    before = {m.__name__: list(m.__table__.columns.keys()) for m in MODELS}
    tables = set(SQLModel.metadata.tables)
    placements = {m: [d.placement for d in vars(m).values() if isinstance(d, Relationship)] for m in MODELS}
    with pytest.raises(RelationshipConfigurationError):
        configure(MODELS)  # the ambiguous groups raise again, the rest is untouched
    assert {m.__name__: list(m.__table__.columns.keys()) for m in MODELS} == before
    assert set(SQLModel.metadata.tables) == tables
    assert placements == {m: [d.placement for d in vars(m).values() if isinstance(d, Relationship)] for m in MODELS}


class CfgIdemTeam(BaseModel, table=True):
    members = Relationship[list["CfgIdemPlayer"]]()


class CfgIdemPlayer(BaseModel, table=True):
    team = Relationship["CfgIdemTeam | None"]()


def test_configure_is_idempotent() -> None:
    configure([CfgIdemTeam, CfgIdemPlayer])
    columns = list(CfgIdemPlayer.__table__.columns.keys())
    placement = CfgIdemPlayer.team.placement
    configure([CfgIdemTeam, CfgIdemPlayer])
    assert list(CfgIdemPlayer.__table__.columns.keys()) == columns
    assert columns.count("team_id") == 1
    assert CfgIdemPlayer.team.placement is placement


def test_model_imported_between_two_calls() -> None:
    module = types.ModuleType("cfg_incremental")
    sys.modules[module.__name__] = module
    try:
        exec(  # noqa: S102
            "from herogold.orm.core.model import BaseModel\n"
            "from herogold.orm.core.utils import Relationship\n"
            "class CfgEarly(BaseModel, table=True):\n"
            "    later = Relationship['CfgLater | None']()\n",
            module.__dict__,
        )
        early = module.CfgEarly
        configure([early])  # CfgLater does not exist yet: deferred, no error
        assert not early.later.configured
        assert "later_id" not in early.__table__.columns
        exec(  # noqa: S102
            "class CfgLater(BaseModel, table=True):\n"
            "    items = Relationship[list['CfgEarly']]()\n",
            module.__dict__,
        )
        configure([early, module.CfgLater])
        assert early.later.configured
        assert fks(early, "later_id") == ["cfglater.id"]
        assert module.CfgLater.items.pair is early.later
    finally:
        del sys.modules[module.__name__]


class CfgWTeam(BaseModel, table=True):
    members = Relationship[list["CfgWPlayer"]]()


class CfgWPlayer(BaseModel, table=True):
    team = Relationship["CfgWTeam | None"]()


@pytest.fixture
def scratch_engine() -> Iterator[object]:
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    yield engine
    engine.dispose()


def test_warnings_before_configure_then_silence_after(scratch_engine: object) -> None:
    with pytest.raises(AttributeError, match=r"CfgWPlayer\.team_id is generated by the relationship CfgWPlayer\.team"):
        CfgWPlayer.team_id  # noqa: B018
    with pytest.raises(AttributeError, match=r"configure\(\) has not run"):
        CfgWPlayer(name="x").team_id  # noqa: B018
    with pytest.warns(UserWarning, match=r"configure\(\) has not run"), pytest.raises(RuntimeError, match="configure"):
        CfgWPlayer(name="x").team  # noqa: B018

    class CfgPing(BaseModel, table=True):  # a new mapper, so the next use runs SQLAlchemy's configure step
        pass

    with pytest.warns(UserWarning, match=r"configure\(\) has not run.*first query"):
        CfgPing()
    with pytest.warns(UserWarning, match=r"configure\(\) has not run.*create_all"):
        SQLModel.metadata.create_all(scratch_engine, tables=[CfgWPlayer.__table__])
    assert "team_id" not in CfgWPlayer.__table__.columns

    configure([CfgWTeam, CfgWPlayer])
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        CfgWPlayer.team_id  # noqa: B018
        assert CfgWPlayer(name="x").team_id is None
        CfgWPlayer(name="x").team  # noqa: B018
    with pytest.raises(AttributeError) as unrelated:
        CfgWPlayer.nonsense  # noqa: B018
    assert "generated" not in str(unrelated.value)


def test_alembic_sees_the_generated_column() -> None:
    pytest.importorskip("alembic")
    from alembic.autogenerate import compare_metadata  # noqa: PLC0415
    from alembic.migration import MigrationContext  # noqa: PLC0415

    old = create_engine("sqlite://")
    with old.begin() as conn:
        conn.exec_driver_sql(f"create table {CfgPlayer.__tablename__} (id integer primary key, name varchar not null)")
        diffs = compare_metadata(MigrationContext.configure(conn), SQLModel.metadata)
    flat = [d for diff in diffs for d in (diff if isinstance(diff, list) else [diff])]
    assert any(d[0] == "add_column" and d[3].name == "team_id" for d in flat)


class _QuotedRef:
    team_id: "UndefinedTeam | None"  # noqa: UP037, F821
    name: str


def test_declared_annotation_names_finds_a_quoted_undefined_forward_ref() -> None:
    assert declared_annotation_names(_QuotedRef) == {"team_id", "name"}


def test_declared_annotation_names_ignores_inherited_and_undeclared_names() -> None:
    class Child(_QuotedRef):
        extra: int

    assert declared_annotation_names(Child) == {"extra"}
    assert declared_annotation_names(CfgPlayer) >= {"name"}


@pytest.mark.skipif(sys.version_info < (3, 14), reason="unquoted forward references need deferred annotations (3.14+)")
def test_declared_annotation_names_finds_an_unquoted_undefined_forward_ref() -> None:
    namespace: dict[str, object] = {}
    exec("class Unquoted:\n    team_id: UndefinedTeam | None\n    name: str\n", namespace)  # noqa: S102

    assert declared_annotation_names(namespace["Unquoted"]) == {"team_id", "name"}  # type: ignore[arg-type]


def test_configure_module_imports_without_annotationlib() -> None:
    code = textwrap.dedent(
        """
        import sys
        import herogold.orm.core.loading, herogold.orm.core.utils, herogold.orm.core.errors  # dependencies first
        for name in [m for m in sys.modules if m.startswith("herogold.orm.core.configure")]:
            del sys.modules[name]
        sys.modules["annotationlib"] = None  # makes "import annotationlib" raise ImportError
        import herogold.orm.core.configure
        """,
    )
    result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=False)  # noqa: S603

    assert result.returncode == 0, result.stderr


class ScopeTeam(BaseModel, table=True):
    players = Relationship[list["ScopePlayer"]]()


class ScopePlayer(BaseModel, table=True):
    team = Relationship["ScopeTeam | None"]()


def test_partial_scope_still_pairs_with_the_partner_outside_it() -> None:
    configure([ScopeTeam])
    assert ScopePlayer.team.pair is ScopeTeam.players
    assert "team_id" in ScopePlayer.__table__.columns
    assert ScopeTeam.players.placement.storage is Storage.TARGET_COLUMN
    configure([ScopePlayer])
    with contextlib.suppress(RelationshipConfigurationError):  # the module's ambiguous fixtures raise again
        configure()
    assert list(ScopePlayer.__table__.columns.keys()).count("team_id") == 1
    assert fks(ScopePlayer, "team_id") == ["scopeteam.id"]
    assert "scopeteam_players" not in SQLModel.metadata.tables


class InvA(BaseModel, table=True):
    bs = Relationship[list["InvB"]](inverse=lambda: InvB.a)


class InvB(BaseModel, table=True):
    a = Relationship["InvA | None"](inverse=lambda: Missing.x)  # ty: ignore[unresolved-reference]  # noqa: F821


def test_partner_inverse_that_raises_is_collected_not_raised_raw() -> None:
    with pytest.raises(RelationshipConfigurationError) as caught:
        configure([InvA, InvB])
    assert "InvA.bs" in caught.value.errors
    assert "InvB.a" in caught.value.errors
    assert "could not be evaluated" in caught.value.errors["InvB.a"]


class CompositeOwner(BaseModel, table=True):
    region: str = Field(default="", primary_key=True)
    owner_of = Relationship["CompositeTarget | None"]()


class CompositeTarget(BaseModel, table=True):
    pass


def test_composite_primary_key_on_the_owner_is_rejected() -> None:
    with pytest.raises(RelationshipConfigurationError) as caught:
        configure([CompositeOwner, CompositeTarget])
    message = caught.value.errors["CompositeOwner.owner_of"]
    assert "composite primary key" in message
    assert "CompositeOwner" in message
    assert "owner_of_id" not in CompositeOwner.__table__.columns


class FkIndexTeam(BaseModel, table=True):
    name: str = ""
    members = Relationship[list["FkIndexMember"]]()


class FkIndexMember(BaseModel, table=True):
    team = Relationship["FkIndexTeam | None"]()


configure([FkIndexTeam, FkIndexMember])


def test_direct_target_column_write_does_not_scan_the_identity_map(
    session: Session, monkeypatch: pytest.MonkeyPatch,
) -> None:
    teams = [FkIndexTeam(name=f"t{i}") for i in range(2000)]
    session.add_all(teams)
    session.commit()
    first, second = teams[0], teams[1]
    assert [m.id for m in first.members] == []  # cached empty list on the first team
    calls: list[int] = []
    identity_map_type = type(session.identity_map)
    original = identity_map_type.values
    monkeypatch.setattr(identity_map_type, "values", lambda self: (calls.append(1), original(self))[1])
    second_id, first_id = second.id, first.id  # reading an expired row would autoflush the pending ones
    pending = [FkIndexMember() for _ in range(200)]
    session.add_all(pending)
    for member in pending:
        set_attribute(member, "team_id", second_id)
    assert calls == []

    session.flush()
    monkeypatch.undo()
    set_attribute(pending[0], "team_id", first_id)  # a persistent row whose old key is known: a keyed lookup only
    assert [m.id for m in first.members] == [pending[0].id]
    assert pending[0].id not in [m.id for m in second.members]
