"""Module that provides a base APIModel class for API interactions with SQLModel instances."""
import logging
from collections.abc import Generator, Sequence

from sqlmodel import select

try:
    from fastapi import APIRouter, status
except ImportError as e:
    msg = (
        "Failed to import required dependencies for the orm[api] package. "
        "Please ensure that 'api' extra is installed. "
        "You can install them using 'herogold[orm-api]'."
    )
    raise ImportError(msg) from e


from herogold.orm.model import BaseModel


class PaginatedResponse[T: type[BaseModel]]:
    """A simple wrapper for paginated responses."""

    base_url: str = "/"
    size = 100

    def __init__(self, model: T, page: int = 1) -> None:
        """Initialize the PaginatedResponse with page, size, and total items."""
        self.model = model
        self.page = page

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

    def get_all(self) -> Generator[T]:
        """Get all records, paginated."""
        offset = 0
        while self.model.count() > offset * PaginatedResponse.size:
            yield from PaginatedResponse(self.model, page=offset)
            offset += 1

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
