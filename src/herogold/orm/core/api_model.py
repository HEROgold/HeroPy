"""Module that provides a base APIModel class for API interactions with SQLModel instances."""

from __future__ import annotations

from collections.abc import Callable, Generator, Sequence
from enum import StrEnum
from typing import TYPE_CHECKING, Any, ClassVar, Literal

from sqlmodel import SQLModel, col, select

from herogold.orm.core.model import BaseModel, CustomData, _BaseModel
from herogold.orm.custom_data import DEFAULT_SIZE_LIMIT, OutOfSpaceError, validate_size

if TYPE_CHECKING:
    from sqlalchemy import ColumnElement
    from sqlalchemy.sql.elements import SQLColumnExpression
    from sqlmodel.sql.expression import SelectOfScalar

try:
    from fastapi import APIRouter, HTTPException, status
except ImportError as e:
    msg = (
        "Failed to import required dependencies for the orm[api] package. "
        "Please ensure that 'api' extra is installed. "
        "You can install them using 'herogold[orm-api]'."
    )
    raise ImportError(msg) from e



class Operator(StrEnum):
    """Comparison operators supported by the QUERY endpoint (RFC 10008)."""

    eq = "eq"
    ne = "ne"
    gt = "gt"
    ge = "ge"
    lt = "lt"
    le = "le"
    like = "like"
    ilike = "ilike"
    in_ = "in"


class QueryFilter(SQLModel):
    """A single field filter for a QUERY request body."""

    field: str
    op: Operator = Operator.eq
    value: Any


class QueryRequest(SQLModel):
    """Body for a QUERY request: filters plus sorting and pagination."""

    filters: list[QueryFilter] = []
    sort: str | None = None
    order: Literal["asc", "desc"] = "asc"
    page: int = 1
    limit: int = 100


class PaginatedResponse[T: _BaseModel]:
    """A simple wrapper for paginated responses."""

    base_url: str = "/"

    def __init__(self, model: type[T], page: int = 1, size: int = 100) -> None:
        """Initialize the PaginatedResponse with page, size, and total items."""
        self.model = model
        self.page = page
        self.size = size

    @property
    def total_pages(self) -> int:
        """Calculate the total number of pages based on total items and page size."""
        return (self.model.count() + self.size - 1) // self.size

    @property
    def url(self) -> str:
        """Generate the URL for the current page."""
        return f"{self.base_url}?page={self.page}&size={self.size}"

    @property
    def next(self) -> PaginatedResponse[T] | None:  # pyright: ignore[reportIndexIssue]
        """Generate the URL for the next page if it exists."""
        if self.page < self.total_pages:
            return PaginatedResponse[T](self.model, self.page + 1)
        return None

    @property
    def meta(self) -> dict[str, int | str | None]:
        """Return metadata about the pagination."""
        return {
            "page": self.page,
            "size": self.size,
            "total_pages": self.total_pages,
            "total_items": self.model.count(),
            "next": self.next.url if self.next else None,
        }

    def __iter__(self) -> Generator[T]:
        """Iterate over the items for the current page."""
        if self.model.id is None:
            msg_0 = "Model instance must have an 'id' attribute set for pagination."
            raise ValueError(msg_0)
        offset = (self.model.id - 1) * self.size
        yield from self.model.session.exec(
            select(self.model).where(self.model.id >= offset).limit(self.size),
        ).all()
        yield from self.next or []


class APIModel[T: _BaseModel]:
    """Base APIModel class with custom methods for API interactions."""

    def __init__(self, model: type[T], router: APIRouter) -> None:
        """Initialize the APIModel with a SQLModel instance, adding routes to the provided router."""
        self.model = model
        router.tags = [model.__name__, *router.tags]
        default_responses: dict[int | str, dict[str, str]] = {
            200: {"description": "Successful Response"},
            404: {"description": "Not Found"},
        }
        router.add_api_route(
            "/",
            self.get_all,
            methods=["GET"],
            response_model=Generator[T],
            responses=default_responses,
        )
        router.add_api_route(
            "/{_id}",
            self.get,
            methods=["GET"],
            response_model=T,
            responses=default_responses,
        )
        router.add_api_route(
            "/",
            self.create,
            methods=["POST"],
            response_model=T,
            responses={
                201: {"description": "Created"},
                400: {"description": "Bad Request"},
            },
        )
        router.add_api_route(
            "/",
            self.update,
            methods=["PUT", "PATCH"],
            responses=default_responses,
        )
        router.add_api_route(
            "/{_id}",
            self.delete,
            methods=["DELETE"],
            responses=default_responses,
        )
        router.add_api_route(
            "/",
            self.query,
            methods=["QUERY"],
            response_model=list[model],  # ty:ignore[invalid-type-form]
            responses=default_responses,
        )

    def _param_builder(self, query_params: dict[str, str]) -> dict[str, str]:
        """Build query parameters for filtering."""
        return {key: value for key, value in query_params.items() if hasattr(self.model, key)}

    def _build_filtered_query(self, query_params: dict[str, str]) -> SelectOfScalar[T]:
        """Build SQLModel filters based on query parameters."""
        q = select(self.model)
        for key, value in self._param_builder(query_params).items():
            q = q.where(getattr(self.model, key) == value)
        return q

    def _persist_custom_data(self, item: T, data: dict[str, Any] | None) -> None:
        """Persist ``data`` as a linked :class:`CustomData` row.

        Validates the size first; an oversize payload raises ``413``. On success a
        ``CustomData`` row is created and linked to ``item`` via the association
        table (``item.custom_data = row``), so ``item`` must already be persisted.
        The per-model byte budget can be overridden with a ``custom_data_size_limit``
        ClassVar on the model.
        """
        if not data:
            return
        limit = getattr(self.model, "custom_data_size_limit", DEFAULT_SIZE_LIMIT)
        if isinstance(err := validate_size(data, limit), OutOfSpaceError):
            raise HTTPException(status_code=status.HTTP_413_CONTENT_TOO_LARGE, detail=str(err))
        row = CustomData(data=dict(data))
        row.add()
        item.custom_data = row

    # `v` is intentionally Any: filter values come straight from the request body
    # (QueryFilter.value: Any) and are heterogeneous — scalar for eq/like, iterable for in_.
    _operators: ClassVar[dict[Operator, Callable[[SQLColumnExpression[Any], Any], ColumnElement[bool]]]] = {
        Operator.eq: lambda c, v: c == v,
        Operator.ne: lambda c, v: c != v,
        Operator.gt: lambda c, v: c > v,
        Operator.ge: lambda c, v: c >= v,
        Operator.lt: lambda c, v: c < v,
        Operator.le: lambda c, v: c <= v,
        Operator.like: lambda c, v: c.like(v),
        Operator.ilike: lambda c, v: c.ilike(v),
        Operator.in_: lambda c, v: c.in_(v),
    }

    def query(self, request: QueryRequest) -> Sequence[T]:
        """Run a safe, idempotent query per RFC 10008 (HTTP QUERY)."""
        # TODO: preferably, this module does not use any sql.
        # Only using the Model's methods
        self.model.logger.debug("QUERY %s: %s", self.model.__name__, request, extra={"request": request})
        q = select(self.model).where(self.model.deleted_at == None)  # noqa: E711
        for f in request.filters:
            if not hasattr(self.model, f.field):
                continue
            q = q.where(self._operators[f.op](col(getattr(self.model, f.field)), f.value))
        if request.sort and hasattr(self.model, request.sort):
            sort_col = col(getattr(self.model, request.sort))
            q = q.order_by(sort_col.desc() if request.order.lower() == "desc" else sort_col.asc())
        offset = (request.page - 1) * request.limit
        return self.model.session.exec(q.offset(offset).limit(request.limit)).all()

    def get_all(
        self,
        sort: str | None = None,
        order: Literal["asc", "desc"] = "asc",
        page: int = 1,
        limit: int = 100,
        **kwargs: str,  # Allows for dynamic fieldname filtering based on query parameters
    ) -> Generator[T]:
        """Get all records with optional sorting, pagination, and filtering."""
        q = self._build_filtered_query(kwargs)

        if sort and hasattr(self.model, sort):
            sort_col = col(getattr(self.model, sort))
            sort_order = sort_col.desc() if order.lower() == "desc" else sort_col.asc()
            q = q.order_by(sort_order)

        yield from PaginatedResponse(self.model, page, size=limit)

    def get(self, _id: int) -> T | int:
        """Get a record by ID. Its extra data is available via ``inst.custom_data.data``."""
        inst = self.model.get(_id)
        if inst is None:
            return status.HTTP_404_NOT_FOUND
        return inst

    def create(self, item: T, custom_data: dict[str, Any] | None = None) -> T:
        """Create a new record, then link any ``custom_data`` via the CustomData table."""
        self.model.add(item)  # persist first so item.id exists for the link
        self._persist_custom_data(item, custom_data)
        return item

    def update(self, item: T, custom_data: dict[str, Any] | None = None) -> None | int:
        """Update an existing record.

        Item can be a full model instance or a partial update with only the fields to be updated.
        """
        if not item.id or not self.model.get(item.id):
            return status.HTTP_404_NOT_FOUND
        self.model.update(item)
        self._persist_custom_data(item, custom_data)
        return None

    def delete(self, _id: int) -> None | int:
        """Delete a record by ID."""
        if not self.model.get(_id):
            return status.HTTP_404_NOT_FOUND
        inst = self.model.get(_id)
        self.model.delete(inst)
        return None
