"""Module that provides a base APIModel class for API interactions with SQLModel instances."""

from __future__ import annotations

from collections.abc import Callable, Generator, Iterable
from enum import StrEnum
from typing import TYPE_CHECKING, Any, ClassVar, Literal, TypedDict

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.sql.elements import SQLCoreOperations
from sqlmodel import Field, SQLModel, col, select

from herogold.imports import ExtraImportContext
from herogold.orm.core.model import ExtraData

with ExtraImportContext("herogold", "orm", "orm", "api"):
    from fastapi import APIRouter, HTTPException, Response, status


from .model import BaseModel

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


class PaginatedResponse[T: BaseModel]:
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

    def __iter__(self) -> Generator[T]:
        """Iterate over the items for the current page."""
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


class QueryResponse[T: BaseModel](TypedDict):
    """TypedDict for the response of a QUERY request."""

    items: list[T]
    page: int
    size: int
    total_pages: int
    total_items: int
    next: str | None


type SupportsOperations = Callable[[SQLCoreOperations[Any], Any], SQLCoreOperations[bool]]
type OperatorMap = dict[Operator, SupportsOperations]


class APIModel[T: BaseModel]:
    """Base APIModel class with custom methods for API interactions."""

    def __init__(self, model: type[T], router: APIRouter) -> None:
        """Initialize the APIModel with a SQLModel instance, adding routes to the provided router."""
        self.model = model
        router.tags = [model.__name__, *router.tags]
        default_responses: dict[int | str, dict[str, Any]] = {
            200: {"description": "Successful Response"},
            404: {"description": "Not Found"},
        }
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
            response_model=QueryResponse[model],  # ty: ignore[invalid-type-form]
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

    def _param_builder(self, query_params: dict[str, str]) -> dict[str, str]:
        """Build query parameters for filtering."""
        return {key: value for key, value in query_params.items() if hasattr(self.model, key)}

    def _build_filtered_query(self, query_params: dict[str, str]) -> SelectOfScalar[T]:
        """Build SQLModel filters based on query parameters."""
        q = select(self.model)
        for key, value in self._param_builder(query_params).items():
            q = q.where(getattr(self.model, key) == value)
        return q

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

    def validate_query_filters(self, filters: Iterable[QueryFilter]) -> Generator[QueryFilter, None, None]:
        """Pre-query validation for the QUERY endpoint."""
        for f in filters:
            if f.field not in self.model.model_fields:
                msg = f"Unknown filter field: {f.field!r}"
                raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, msg)
            yield f

    def query(self, request: QueryRequest) -> QueryResponse[T]:
        """Run a safe, idempotent query per RFC 10008 (HTTP QUERY)."""
        self.model.logger.debug("QUERY %s: %s", self.model.__name__, request, extra={"request": request})
        q = select(self.model).where(self.model.deleted_at == None)  # noqa: E711

        if request.sort and request.sort not in self.model.model_fields:
            msg = f"Unknown sort field: {request.sort!r}"
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, msg)

        for f in self.validate_query_filters(request.filters):
            try:
                q = q.where(self._operators[f.op](col(getattr(self.model, f.field)), f.value))
            except (TypeError, ValueError, SQLAlchemyError) as e:
                msg = f"Invalid value for field {f.field!r} with operator {f.op!r}: {e}"
                raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, msg) from e

        if request.sort:
            sort_col = col(getattr(self.model, request.sort))
            sort_order = sort_col.desc if request.order.casefold() == "desc" else sort_col.asc
            q = q.order_by(sort_order())

        paginated = PaginatedResponse(self.model, request.page, request.limit, query=q)
        return {"items": list(paginated), **paginated.meta}

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
            sort_order = sort_col.desc() if order.casefold() == "desc" else sort_col.asc()
            q = q.order_by(sort_order)

        yield from PaginatedResponse(self.model, page, size=limit)

    def get(self, _id: int) -> T | int:
        """Get a record by ID."""
        return self.model.get(_id) or status.HTTP_404_NOT_FOUND

    def create(self, item: T) -> T:
        """Create a new record."""
        if extras := getattr(item, "extra", None):
            item.extra = ExtraData(data=extras)
        self.model.add(item)
        return item

    def update(self, item: T) -> int | None:
        """Update an existing record.

        Item can be a full model instance or a partial update with only the fields to be updated.
        """
        if not item.id or not self.model.get(item.id):
            return status.HTTP_404_NOT_FOUND
        if extras := getattr(item, "extra", None):
            item.extra = ExtraData(data=extras)
        self.model.update(item)
        return None

    def delete(self, _id: int) -> int | None:
        """Delete a record by ID."""
        if not self.model.get(_id):
            return status.HTTP_404_NOT_FOUND
        inst = self.model.get(_id)
        self.model.delete(inst)
        return None
