"""``/api/v1/users`` routes.

Every handler here follows the same shape: parse the HTTP request into a
command/query, dispatch it through the :class:`Mediator`, map the resulting
DTO onto a response schema. No business logic, no SQLAlchemy, no domain
rules — see ``docs/api.md`` and PRD §29 for why routes must stay this thin.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.application.common.dto.pagination import Page
from app.application.common.mediator import Mediator
from app.application.common.request_context import RequestContext
from app.application.users.commands.deactivate_user import DeactivateUserCommand
from app.application.users.commands.register_user import RegisterUserCommand
from app.application.users.commands.rename_user import RenameUserCommand
from app.application.users.dto.user_dto import UserDTO
from app.application.users.queries.get_user import GetUserQuery
from app.application.users.queries.list_users import ListUsersQuery
from app.presentation.api.dependencies.mediator import get_mediator, get_request_context
from app.presentation.api.dependencies.pagination import PaginationParams, pagination_params
from app.presentation.api.schemas.common.pagination import PageResponse
from app.presentation.api.schemas.users.requests import (
    DeactivateUserRequest,
    RegisterUserRequest,
    RenameUserRequest,
)
from app.presentation.api.schemas.users.responses import UserResponse

router = APIRouter(prefix="/users", tags=["users"])

MediatorDep = Annotated[Mediator, Depends(get_mediator)]
ContextDep = Annotated[RequestContext, Depends(get_request_context)]


@router.post(
    "",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
)
async def register_user(
    body: RegisterUserRequest, mediator: MediatorDep, context: ContextDep
) -> UserResponse:
    command = RegisterUserCommand(email=body.email, display_name=body.display_name)
    result: UserDTO = await mediator.send(command, context)
    return UserResponse.model_validate(result)


@router.get("/{user_id}", response_model=UserResponse, summary="Get a user by id")
async def get_user(user_id: str, mediator: MediatorDep, context: ContextDep) -> UserResponse:
    result: UserDTO = await mediator.send(GetUserQuery(user_id=user_id), context)
    return UserResponse.model_validate(result)


@router.get("", response_model=PageResponse[UserResponse], summary="List users")
async def list_users(
    mediator: MediatorDep,
    context: ContextDep,
    pagination: Annotated[PaginationParams, Depends(pagination_params)],
) -> PageResponse[UserResponse]:
    query = ListUsersQuery(offset=pagination.offset, limit=pagination.limit)
    page: Page[UserDTO] = await mediator.send(query, context)
    return PageResponse.from_page(page, UserResponse)


@router.patch("/{user_id}", response_model=UserResponse, summary="Rename a user")
async def rename_user(
    user_id: str, body: RenameUserRequest, mediator: MediatorDep, context: ContextDep
) -> UserResponse:
    command = RenameUserCommand(user_id=user_id, new_display_name=body.display_name)
    result: UserDTO = await mediator.send(command, context)
    return UserResponse.model_validate(result)


@router.delete("/{user_id}", response_model=UserResponse, summary="Deactivate a user")
async def deactivate_user(
    user_id: str, body: DeactivateUserRequest, mediator: MediatorDep, context: ContextDep
) -> UserResponse:
    command = DeactivateUserCommand(user_id=user_id, reason=body.reason)
    result: UserDTO = await mediator.send(command, context)
    return UserResponse.model_validate(result)
