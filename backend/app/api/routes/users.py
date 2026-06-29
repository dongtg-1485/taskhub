import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import (
    AsyncSessionDep,
    CurrentUser,
    get_current_active_superuser,
)
from app.core.security import get_password_hash, verify_password
from app.models import (
    Message,
    UpdateCurrentUserRequest,
    UpdatePasswordRequest,
    UpdateUserRequest,
    UserResponse,
    UsersResponse,
)
from app.repositories import users

router = APIRouter(prefix="/users", tags=["users"])


@router.get(
    "/",
    dependencies=[Depends(get_current_active_superuser)],
    response_model=UsersResponse,
)
async def read_users(session: AsyncSessionDep, page: int = 0, limit: int = 100) -> Any:
    """
    Retrieve users.
    """
    result = await users.list(session, page=page, limit=limit)
    return UsersResponse(
        count=result.total,
        data=result.items,
    )


@router.patch("/me", response_model=UserResponse)
async def update_user_me(
    *,
    session: AsyncSessionDep,
    user_in: UpdateCurrentUserRequest,
    current_user: CurrentUser,
) -> Any:
    """
    Update own user.
    """
    if user_in.email:
        existing_user = await users.get_by_email(session=session, email=user_in.email)
        if existing_user and existing_user.id != current_user.id:
            raise HTTPException(
                status_code=409,
                detail="Can not edit info that is already used by another user",
            )
    updated_user = await users.update_user(
        session=session, db_user=current_user, user_in=user_in
    )
    return UserResponse.model_validate(updated_user)


@router.get("/me", response_model=UserResponse)
async def read_user_me(current_user: CurrentUser) -> Any:
    """
    Get current user.
    """
    return current_user


@router.patch("/me/password", response_model=Message)
async def update_password_me(
    *,
    session: AsyncSessionDep,
    body: UpdatePasswordRequest,
    current_user: CurrentUser,
) -> Message:
    """
    Đổi mật khẩu của user hiện tại. Yêu cầu cung cấp mật khẩu hiện tại để xác minh.
    """
    is_valid, _ = verify_password(body.current_password, current_user.hashed_password)
    if not is_valid:
        raise HTTPException(status_code=400, detail="Mật khẩu hiện tại không đúng.")
    new_hashed = get_password_hash(body.new_password)
    await users.update(session, current_user, {"hashed_password": new_hashed})
    return Message(message="Đổi mật khẩu thành công.")


@router.delete("/me", response_model=Message)
async def delete_user_me(session: AsyncSessionDep, current_user: CurrentUser) -> Any:
    """
    Delete own user.
    """
    if current_user.is_superuser:
        raise HTTPException(
            status_code=403, detail="Super users are not allowed to delete themselves"
        )
    await users.delete(session=session, user=current_user)
    return Message(message="User deleted successfully")


@router.get("/{user_id}", response_model=UserResponse)
async def read_user_by_id(
    user_id: uuid.UUID, session: AsyncSessionDep, current_user: CurrentUser
) -> Any:
    """
    Get a specific user by id.
    """
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=403, detail="The user doesn't have enough privileges"
        )
    user = await users.get(session, user_id)
    if not user:
        raise HTTPException(
            status_code=404,
            detail="The user with this id does not exist in the system",
        )
    if user != current_user and not current_user.is_superuser:
        raise HTTPException(status_code=400, detail="Not enough permissions")
    return UserResponse.model_validate(user)


@router.patch(
    "/{user_id}",
    dependencies=[Depends(get_current_active_superuser)],
    response_model=UserResponse,
)
async def update_user(
    *,
    session: AsyncSessionDep,
    user_id: uuid.UUID,
    user_in: UpdateUserRequest,
    current_user: CurrentUser,
) -> Any:
    """
    Update a user.
    """
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=403, detail="The user doesn't have enough privileges"
        )
    db_user = await users.get(session, user_id)
    if not db_user:
        raise HTTPException(
            status_code=404,
            detail="The user with this id does not exist in the system",
        )
    if user_in.email:
        existing_user = await users.get_by_email(session=session, email=user_in.email)
        if existing_user and existing_user.id != user_id:
            raise HTTPException(
                status_code=409, detail="User with this email already exists"
            )

    db_user = await users.update_user(session=session, db_user=db_user, user_in=user_in)
    return db_user


@router.delete("/{user_id}", dependencies=[Depends(get_current_active_superuser)])
async def delete_user(
    session: AsyncSessionDep, current_user: CurrentUser, user_id: uuid.UUID
) -> Message:
    """
    Delete a user.
    """
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=403, detail="The user doesn't have enough privileges"
        )
    user = await users.get(session, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user == current_user:
        raise HTTPException(
            status_code=403, detail="Users are not allowed to delete themselves"
        )
    await users.delete(session=session, user=user)
    return Message(message="User deleted successfully")
