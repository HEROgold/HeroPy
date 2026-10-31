"""Module that provides a base APIModel class for API interactions with SQLModel instances."""

from __future__ import annotations

import inspect
from collections.abc import Callable, Generator, Iterable, Iterator
from enum import StrEnum
from typing import TYPE_CHECKING, Annotated, Any, ClassVar, Literal, Self, TypedDict, override

from sqlalchemy.sql.elements import SQLCoreOperations
from sqlmodel import Field, Session, SQLModel, col, select

from herogold.imports import ExtraImportContext
from herogold.orm.custom_data import OutOfSpaceError, set_custom_data
from herogold.protocols import Filterable, Sortable

with ExtraImportContext("herogold", "orm", "orm", "api"):
    from fastapi import APIRouter, Depends, HTTPException, Response, status


from .core.binding import orm_session
from .core.model import _BaseModel

if TYPE_CHECKING:
    from sqlmodel.sql.expression import SelectOfScalar


def request_session() -> Generator[Session]:
    """Yield one session for a request.

    ``orm_session`` commits when the route returns and rolls back when it raises.
    """
    with orm_session() as session:
        yield session


SessionDep = Annotated[Session, Depends(request_session)]


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
        session: Session | None = None,
    ) -> None:
        """Initialize the PaginatedResponse with page, size, and an optional pre-filtered/sorted query.

        ``session`` is the request's session. Without one, each read opens its own.

        When `query` is omitted, falls back to the default unfiltered pagination behavior.
        """
        self.model = model
        self.page = page
        self.size = size
        self._query = query
        self._session = session

    def _read[R](self, run: Callable[[Session], R]) -> R:
        if self._session is not None:
            return run(self._session)
        with orm_session() as session:
            return run(session)

    def __iter__(self) -> Generator[T]:
        """Iterate over the items for the current page, then yield from the next page if it exists."""
        if self._query is not None:
            offset = (self.page - 1) * self.size
            query = self._query.offset(offset).limit(self.size)
            yield from self._read(lambda session: session.exec(query).all())
            return

        if not self.model.id:
            msg = f"Model {self.model.__name__} does not have an 'id' field for pagination."
            raise ValueError(msg)

        offset = (self.model.id - 1) * self.size
        query = select(self.model).where(self.model.id >= offset).limit(self.size)
        yield from self._read(lambda session: session.exec(query).all())
        yield from self.next or []

    @property
    def total_pages(self) -> int:
        """Calculate the total number of pages based on total items and page size."""
        return (self._read(self.model.count) + self.size - 1) // self.size

    @property
    def url(self) -> str:
        """Generate the URL for the current page."""
        return f"{self.base_url}?page={self.page}&size={self.size}"

    @property
    def next(self) -> PaginatedResponse[T] | None:
        """Generate the URL for the next page if it exists."""
        if self.page < self.total_pages:
            return PaginatedResponse[T](self.model, self.page + 1, self.size, query=self._query, session=self._session)
        return None

    @property
    def meta(self) -> PaginatedMeta:
        """Return metadata about the pagination."""
        return {
            "page": self.page,
            "size": self.size,
            "total_pages": self.total_pages,
            "total_items": self._read(self.model.count),
            "next": self.next.url if self.next else None,
        }


class RequestFilter[T: _BaseModel](Filterable, Sortable):
    """Filter and sort a model's query from a QueryRequest.

    ``filter()`` and ``sort()`` return new instances, and iterating executes the
    query, so the result can be passed straight to ``sorted()``, ``map()``, etc.
    """

    def __init__(
        self,
        model: type[T],
        request: QueryRequest,
        query: SelectOfScalar[T] | None = None,
        session: Session | None = None,
    ) -> None:
        """Initialize the RequestFilterer with a model, request, optional query and request session."""
        self.session: Session | None = session
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

    def __iter__(self) -> Iterator[T]:
        """Execute the query and yield the matching records."""
        if self.session is not None:
            yield from self.session.exec(self.query).all()
            return
        with orm_session() as session:
            yield from session.exec(self.query).all()

    @override
    def filter(self, **kwargs: object) -> Self:
        """Return a copy with ``kwargs`` equality filters and the request's filters applied."""
        q = self._kwargs_filter(**kwargs) if kwargs else self.query
        for f in self.request.filters:
            if f.field not in self.model.model_fields:
                raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=f"Invalid filter field: {f.field}")  # noqa: E501
            operator = self._operators.get(f.op)
            if f.op is Operator.in_ and not isinstance(f.value, Iterable):
                raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=f"Invalid value for 'in' operator: {f.value}")  # noqa: E501
            if not operator:
                raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=f"Invalid filter operator: {f.op}")  # noqa: E501
            q = q.where(operator(col(getattr(self.model, f.field)), f.value))
        return type(self)(self.model, self.request, q, self.session)

    @override
    def sort(self) -> Self:
        """Return a copy ordered by the request's sort field and order."""
        q = self.query
        if self.request.sort and self.request.sort not in self.model.model_fields:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=f"Invalid sort field: {self.request.sort}")  # noqa: E501
        if self.request.sort and self.request.sort in self.model.model_fields:
            sort_col = col(getattr(self.model, self.request.sort))
            q = self.query.order_by(sort_col.desc() if self.request.order.casefold() == "desc" else sort_col.asc())
        return type(self)(self.model, self.request, q, self.session)

    def _kwargs_filter(self, **kwargs: object) -> SelectOfScalar[T]:
        """Build the query with an equality filter per known field in ``kwargs``."""
        q = self.query
        for key, value in kwargs.items():
            if not hasattr(self.model, key):
                continue
            q = q.where(getattr(self.model, key) == value)
        return q

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
            self._typed(self.create),
            methods=["POST"],
            response_model=T,
            responses={
                201: {"description": "Created"},
                400: {"description": "Bad Request"},
            },
        )
        router.add_api_route(
            "/",
            self._typed(self.update),
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
            response_model=QueryResponse[T],
            responses={
                200: {"description": "Successful Response"},
                400: {"description": "Missing or inconsistent Content-Type"},
                406: {"description": "Not Acceptable"},
                415: {"description": "Unsupported Media Type"},
                422: {"description": "Invalid query content"},
            },
        )

    def _typed(self, route: Callable[..., Any]) -> Callable[..., Any]:
        """Return ``route`` with its ``item`` parameter annotated as the model class.

        FastAPI cannot read a body schema from the unresolved type variable ``T``.
        """
        signature = inspect.signature(route)
        params = [p.replace(annotation=self.model) if p.name == "item" else p for p in signature.parameters.values()]

        def endpoint(*args: Any, **kwargs: Any) -> Any:  # noqa: ANN401
            return route(*args, **kwargs)

        endpoint.__signature__ = signature.replace(parameters=params)  # pyrefly: ignore [missing-attribute]
        endpoint.__name__ = route.__name__
        endpoint.__doc__ = route.__doc__
        return endpoint

    def options(self) -> Response:
        """Advertise the methods supported on the collection endpoint, including QUERY."""
        return Response(status_code=status.HTTP_204_NO_CONTENT, headers={"Allow": "GET, POST, PUT, PATCH, QUERY"})

    def query(self, request: QueryRequest, session: SessionDep) -> QueryResponse[T]:
        """Run a safe, idempotent query per RFC 10008 (HTTP QUERY)."""
        q = RequestFilter(self.model, request, session=session).filter().sort().query
        self.model.logger.debug("QUERY SQL: %s", q, extra={"query": str(q), "request": request})
        page = PaginatedResponse(self.model, request.page, request.limit, q, session)
        return {"items": list(page), **page.meta}

    def get_all(
        self,
        sort: str | None = None,
        order: Literal["asc", "desc"] = "asc",
        page: int = 1,
        limit: int = 100,
        *,
        session: SessionDep,
        **kwargs: str,  # Allows for dynamic fieldname filtering based on query parameters.
        # ince we support Query, we dont need kwargs here?
    ) -> Generator[T]:
        """Get all records with optional sorting, pagination, and filtering."""
        # TODO(HEROgold): update signature to explicitly define types on sort and kwargs.  # noqa: TD003
        # sort should be a FieldType, and kwargs should be a dict of field names to values.
        request = QueryRequest(filters=[], sort=sort, order=order, page=page, limit=limit)
        q = RequestFilter(self.model, request, session=session).filter(**kwargs).query

        if sort and hasattr(self.model, sort):
            sort_col = col(getattr(self.model, sort))
            sort_order = sort_col.desc() if order.casefold() == "desc" else sort_col.asc()
            q = q.order_by(sort_order)

        yield from PaginatedResponse(self.model, page, limit, q, session)

    def get(self, _id: int, session: SessionDep) -> T | int:
        """Get a record by ID. Its extra data is available via ``inst.custom_data.data``."""
        inst = self.model.get(_id, session=session)
        if inst is None:
            return status.HTTP_404_NOT_FOUND
        return inst

    def create(self, item: T, custom_data: dict[str, Any] | None = None, *, session: SessionDep) -> T:
        """Create a record, then link any ``custom_data``.

        An oversize payload raises 413, which rolls back the request's transaction
        so the item is not stored.
        """
        item.add(session=session)  # Create first so item.id exists for the link
        self._set_custom_data(item, custom_data, session)
        return item

    def update(self, item: T, custom_data: dict[str, Any] | None = None, *, session: SessionDep) -> int | None:
        """Update an existing record.

        Item can be a full model instance or a partial update with only the fields to be updated.
        An oversize ``custom_data`` raises 413 and rolls back the whole update.
        """
        if not item.id or not self.model.get(item.id, session=session):
            return status.HTTP_404_NOT_FOUND
        self._set_custom_data(item, custom_data, session)
        item.update(session=session)
        return None

    def delete(self, _id: int, session: SessionDep) -> int | None:
        """Delete a record by ID."""
        inst = self.model.get(_id, session=session)
        if not inst:
            return status.HTTP_404_NOT_FOUND
        inst.delete(session=session)
        return None

    @staticmethod
    def _set_custom_data(item: _BaseModel, custom_data: dict[str, Any] | None, session: Session) -> None:
        if not custom_data:
            return
        try:
            set_custom_data(item, custom_data, session=session)
        except OutOfSpaceError as err:
            raise HTTPException(status_code=status.HTTP_413_CONTENT_TOO_LARGE, detail=str(err)) from err
