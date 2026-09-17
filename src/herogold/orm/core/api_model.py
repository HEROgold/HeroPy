"""Module that provides a base APIModel class for API interactions with SQLModel instances."""

from __future__ import annotations

from collections.abc import Callable, Generator, Sequence
from enum import StrEnum
from typing import TYPE_CHECKING, Any, ClassVar, Literal, TypedDict

from sqlalchemy.sql.elements import SQLCoreOperations
from sqlmodel import Field, SQLModel, col, select

from herogold.imports import ExtraImportContext
from herogold.orm.core.model import CustomData
from herogold.orm.custom_data import DEFAULT_SIZE_LIMIT, OutOfSpaceError, validate_size

with ExtraImportContext("herogold", "orm", "orm", "api"):
    from fastapi import APIRouter, HTTPException, Response, status


from .model import _BaseModel

if TYPE_CHECKING:
    from sqlmodel.sql.expression import SelectOfScalar


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
    page: int = Field(default=1, ge=1)
    limit: int = Field(default=100, ge=1, le=1000)


class PaginatedMeta(TypedDict):
    """TypedDict for the metadata of a paginated response."""

    page: int
    size: int
    total_pages: int
    total_items: int
    next: str | None


class PaginatedResponse[T: _BaseModel]:
    """A simple wrapper for paginated responses."""

    base_url: str = "/"

    def __init__(
        self,
        model: type[T],
        page: int = 1,
        size: int = 100,
        query: SelectOfScalar[T] | None = None,
    ) -> None:
        """Initialize the PaginatedResponse with page, size, and an optional pre-filtered/sorted query.

        When `query` is omitted, falls back to the default unfiltered pagination behavior.
        """
        self.model = model
        self.page = page
        self.size = size
        self._query = query

    def __iter__(self) -> Generator[T]:
        """Iterate over the items for the current page, then yield from the next page if it exists."""
        if self._query is not None:
            offset = (self.page - 1) * self.size
            yield from self.model.session.exec(self._query.offset(offset).limit(self.size)).all()
            return

        if not self.model.id:
            msg = f"Model {self.model.__name__} does not have an 'id' field for pagination."
            raise ValueError(msg)

        offset = (self.model.id - 1) * self.size
        yield from self.model.session.exec(
            select(self.model).where(self.model.id >= offset).limit(self.size),
        ).all()
        yield from self.next or []

    @property
    def total_pages(self) -> int:
        """Calculate the total number of pages based on total items and page size."""
        return (self.model.count() + self.size - 1) // self.size

    @property
    def url(self) -> str:
        """Generate the URL for the current page."""
        return f"{self.base_url}?page={self.page}&size={self.size}"

    @property
    def next(self) -> PaginatedResponse[T] | None:
        """Generate the URL for the next page if it exists."""
        if self.page < self.total_pages:
            return PaginatedResponse[T](self.model, self.page + 1, self.size, query=self._query)
        return None

    @property
    def meta(self) -> PaginatedMeta:
        """Return metadata about the pagination."""
        return {
            "page": self.page,
            "size": self.size,
            "total_pages": self.total_pages,
            "total_items": self.model.count(),
            "next": self.next.url if self.next else None,
        }


class RequestFilter[T: _BaseModel]:
    """An APIModel that supports filtering, sorting, and pagination."""

    def __init__(self, model: type[T], request: QueryRequest, query: SelectOfScalar[T] | None = None) -> None:
        """Initialize the RequestFilterer with a model, request, and optional query."""
        self.model: type[T] = model
        self.request: QueryRequest = request
        # pyrefly: ignore [bad-assignment]
        self.query: SelectOfScalar[T] = query if query is not None else model.query

    # `v` is intentionally Any: filter values come straight from the request body
    # (QueryFilter.value: Any) and are heterogeneous — scalar for eq/like, iterable for in_.
    _operators: ClassVar[OperatorMap] = {
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

    def filter(self, **kwargs: str) -> RequestFilter[T]:
        """Filter inplace records based on a QueryRequest, applying filters, sorting, and pagination."""
        q = self._kwargs_filter(**kwargs) if kwargs else self.query
        for f in self.request.filters:
            if f.field not in self.model.model_fields:
                continue
            q = self.query.where(self._operators[f.op](col(getattr(self.model, f.field)), f.value))
        return RequestFilter(self.model, self.request, q)

    def sort(self) -> RequestFilter[T]:
        """Sort inplace records based on a QueryRequest, applying sorting and pagination."""
        q = self.query
        if self.request.sort and self.request.sort in self.model.model_fields:
            sort_col = col(getattr(self.model, self.request.sort))
            q = self.query.order_by(sort_col.desc() if self.request.order.lower() == "desc" else sort_col.asc())
        return RequestFilter(self.model, self.request, q)

    def _kwargs_filter(self, **kwargs: str) -> SelectOfScalar[T]:
        """Filter inplace records based on keyword arguments."""
        q = self.query
        for key, value in kwargs.items():
            if not hasattr(self.model, key):
                continue
            q = self.query.where(getattr(self.model, key) == value)
        return q

class CustomDataContainer[T: _BaseModel]:
    """A container for managing custom data associated with a model."""

    def __init__(self, item: T, data: dict[str, Any] | None) -> None:
        """Initialize the CustomDataContainer with a model."""
        self.item = item
        self._data = data

    def validate(self) -> None:
        """Validate the size of ``data`` against the model's custom data size limit."""
        if not self._data:
            return
        limit = getattr(self.item, "custom_data_size_limit", DEFAULT_SIZE_LIMIT)
        if isinstance(err := validate_size(self._data, limit), OutOfSpaceError):
            raise HTTPException(status_code=status.HTTP_413_CONTENT_TOO_LARGE, detail=str(err))

    def set(self) -> None:
        """Persist ``data`` as a linked :class:`CustomData` row.

        Validates the size first; an oversize payload raises ``413``. On success a
        ``CustomData`` row is created and linked to ``item`` via the association
        table (``item.custom_data = row``), so ``item`` must already be persisted.
        The per-model byte budget can be overridden with a ``custom_data_size_limit``
        ClassVar on the model.
        """
        if not self._data:
            return
        self.validate()
        row = CustomData(data=self._data)
        row.add()
        self.item.custom_data = row


class QueryResponse[T: _BaseModel](TypedDict):
    """TypedDict for the response of a QUERY request."""

    items: list[T]
    page: int
    size: int
    total_pages: int
    total_items: int
    next: str | None


type SupportsOperations = Callable[[SQLCoreOperations[Any], Any], SQLCoreOperations[bool]]
type OperatorMap = dict[Operator, SupportsOperations]


class APIModel[T: _BaseModel]:
    """Base APIModel class with custom methods for API interactions."""

    def __init__(self, model: type[T], router: APIRouter) -> None:
        """Initialize the APIModel with a SQLModel instance, adding routes to the provided router."""
        self.model = model
        router.tags = [model.__name__, *router.tags]
        default_responses: dict[int | str, dict[str, Any]] = {
            200: {"description": "Successful Response"},
            404: {"description": "Not Found"},
        }
        # TODO: ensure rollback of failing routes/endpoints
        router.add_api_route(
            "/",
            self.options,
            methods=["OPTIONS"],
            include_in_schema=False,
        )
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
            response_model=Sequence[model],  # ty: ignore[invalid-type-form]
            responses={
                200: {"description": "Successful Response"},
                400: {"description": "Missing or inconsistent Content-Type"},
                406: {"description": "Not Acceptable"},
                415: {"description": "Unsupported Media Type"},
                422: {"description": "Invalid query content"},
            },
        )

    def options(self) -> Response:
        """Advertise the methods supported on the collection endpoint, including QUERY."""
        return Response(status_code=status.HTTP_204_NO_CONTENT, headers={"Allow": "GET, POST, PUT, PATCH, QUERY"})

    def query(self, request: QueryRequest) -> Generator[T]:
        """Run a safe, idempotent query per RFC 10008 (HTTP QUERY)."""
        q = RequestFilter(self.model, request).filter().sort().query
        self.model.logger.debug("QUERY SQL: %s", q, extra={"query": str(q), "request": request})
        yield from PaginatedResponse(self.model, request.page, request.limit, q)

    def get_all(
        self,
        sort: str | None = None,
        order: Literal["asc", "desc"] = "asc",
        page: int = 1,
        limit: int = 100,
        **kwargs: str,  # Allows for dynamic fieldname filtering based on query parameters.
        # ince we support Query, we dont need kwargs here?
    ) -> Generator[T]:
        """Get all records with optional sorting, pagination, and filtering."""
        # TODO: update signature to explicitly define types on sort and kwargs.
        # sort should be a FieldType, and kwargs should be a dict of field names to values.
        request = QueryRequest(filters=[], sort=sort, order=order, page=page, limit=limit)
        q = RequestFilter(self.model, request).filter(**kwargs).query

        if sort and hasattr(self.model, sort):
            sort_col = col(getattr(self.model, sort))
            sort_order = sort_col.desc() if order.casefold() == "desc" else sort_col.asc()
            q = q.order_by(sort_order)

        yield from PaginatedResponse(self.model, page, limit, q)

    def get(self, _id: int) -> T | int:
        """Get a record by ID. Its extra data is available via ``inst.custom_data.data``."""
        inst = self.model.get(_id)
        if inst is None:
            return status.HTTP_404_NOT_FOUND
        return inst

    def create(self, item: T, custom_data: dict[str, Any] | None = None) -> T:
        """Create a new record, then link any ``custom_data`` via the CustomData table."""
        c = CustomDataContainer(item, custom_data)
        c.validate() # Validate before adding to ensure we don't create an item with invalid custom data
        self.model.add(item)  # Create first so item.id exists for the link
        c.set()
        return item

    def update(self, item: T, custom_data: dict[str, Any] | None = None) -> int | None:
        """Update an existing record.

        Item can be a full model instance or a partial update with only the fields to be updated.
        """
        if not item.id or not self.model.get(item.id):
            return status.HTTP_404_NOT_FOUND
        CustomDataContainer(item, custom_data).set()
        self.model.update(item)
        return None

    def delete(self, _id: int) -> int | None:
        """Delete a record by ID."""
        if not self.model.get(_id):
            return status.HTTP_404_NOT_FOUND
        inst = self.model.get(_id)
        self.model.delete(inst)
        return None
