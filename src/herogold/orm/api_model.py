"""Module that provides a base APIModel class for API interactions with SQLModel instances."""

import logging
from collections.abc import Sequence

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
            response_model=Sequence[T],
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

    def get_all(self) -> Sequence[T]:
        """Get all records."""
        self.model.logger = logging.getLogger(self.model.__name__)
        return self.model.get_all()

    def get(self, _id: int) -> T | int:
        """Get a record by ID."""
        self.model.logger = logging.getLogger(self.model.__name__)
        return self.model.get(_id) or status.HTTP_404_NOT_FOUND

    def create(self, item: T) -> T:
        """Create a new record."""
        self.model.logger = logging.getLogger(self.model.__name__)
        self.model.add(item)
        return item

    def update(self, item: T) -> None | int:
        """Update an existing record."""
        self.model.logger = logging.getLogger(self.model.__name__)
        if not item.id or not self.model.get(item.id):
            return status.HTTP_404_NOT_FOUND
        self.model.update(item)
        return None

    def delete(self, _id: int) -> None | int:
        """Delete a record by ID."""
        if not self.model.get(_id):
            return status.HTTP_404_NOT_FOUND
        self.model.logger = logging.getLogger(self.model.__name__)
        inst = self.model.get(_id)
        self.model.delete(inst)
        return None
