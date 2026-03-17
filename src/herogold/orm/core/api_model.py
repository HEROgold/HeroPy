"""Module that provides a base APIModel class for API interactions with SQLModel instances."""
from collections.abc import Generator
from typing import Literal

from sqlmodel import col, select
from sqlmodel.sql._expression_select_cls import SelectOfScalar

try:
    from fastapi import APIRouter, status
except ImportError as e:
    msg = (
        "Failed to import required dependencies for the orm[api] package. "
        "Please ensure that 'api' extra is installed. "
        "You can install them using 'herogold[orm-api]'."
    )
    raise ImportError(msg) from e


from .model import BaseModel


class PaginatedResponse[T: type[BaseModel]]:
    """A simple wrapper for paginated responses."""

    base_url: str = "/"

    def __init__(self, model: T, page: int = 1, size: int = 100) -> None:
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
    def next(self) -> "PaginatedResponse"[T] | None: # pyright: ignore[reportIndexIssue]
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
        offset = (self.page - 1) * self.size
        yield from self.model.session.exec(
            select(self.model).offset(offset).limit(self.size),
        ).all()
        yield from self.next or []

class APIModel[T: type[BaseModel]]:
    """Base APIModel class with custom methods for API interactions."""

    model: T

    def __init__(self, model: T, router: APIRouter) -> None:
        """Initialize the APIModel with a SQLModel instance, adding routes to the provided router."""
        self.model = model
        router.tags = [model.__name__, *router.tags]
        default_responses = {
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
            methods=["PUT"],
            responses=default_responses,
        )
        router.add_api_route(
            "/{_id}",
            self.delete,
            methods=["DELETE"],
            responses=default_responses,
        )

    def _param_builder(self, query_params: dict[str, str]) -> dict[str, str]:
        """Build query parameters for filtering."""
        return {key: value for key, value in query_params.items() if hasattr(self.model, key)}

    def _build_filtered_query(self, query_params: dict[str, str]) -> SelectOfScalar[BaseModel]:
        """Build SQLModel filters based on query parameters."""
        q = select(self.model)
        for key, value in self._param_builder(query_params).items():
            q = q.where(getattr(self.model, key) == value)
        return q

    def get_all(
        self,
        sort: str | None = None,
        order: Literal["asc", "desc"] = "asc",
        page: int = 1,
        limit: int = 100,
        **kwargs: str, # Allows for dynamic fieldname filtering based on query parameters
    ) -> Generator[T]:
        """Get all records with optional sorting, pagination, and filtering."""
        q = self._build_filtered_query(kwargs)

        if sort and hasattr(self.model, sort):
            sort_col = col(getattr(self.model, sort))
            sort_order = sort_col.desc() if order.lower() == "desc" else sort_col.asc()
            q = q.order_by(sort_order)

        yield from PaginatedResponse(self.model, page, size=limit)

    def get(self, _id: int) -> T | int:
        """Get a record by ID."""
        return self.model.get(_id) or status.HTTP_404_NOT_FOUND

    def create(self, item: T) -> T:
        """Create a new record."""
        self.model.add(item)
        return item

    def update(self, item: T) -> None | int:
        """Update an existing record."""
        if not item.id or not self.model.get(item.id):
            return status.HTTP_404_NOT_FOUND
        self.model.update(item)
        return None

    def delete(self, _id: int) -> None | int:
        """Delete a record by ID."""
        if not self.model.get(_id):
            return status.HTTP_404_NOT_FOUND
        inst = self.model.get(_id)
        self.model.delete(inst)
        return None
