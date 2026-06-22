
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import (
    CurrentUser,
    AsyncSessionDep,
)
from app.models import (
    Message,
    WorkspaceCreate,
    WorkspacePublic,
)
from app.models.enums import WorkspaceMemberRole
from app.models.workspace import WorkspaceInvatedUsers, WorkspaceMemberInvite
from app.repositories import workspaces, workspace_members, users

router = APIRouter(prefix="/workspaces", tags=["workspaces"])

@router.post(
    "/",
    response_model=WorkspacePublic,
)
async def create_workspace(
    *,
    session: AsyncSessionDep,
    current_user: CurrentUser,
    workspace_in: WorkspaceCreate,
) -> WorkspacePublic:
    """
    Create a new workspace.
    """
    workspace = await workspaces.create(session, owner_id=current_user.id, workspace_in=workspace_in)
    # Tự động thêm owner vào danh sách thành viên
    await workspace_members.add_member(
        session, 
        workspace_id=workspace.id, 
        user_id=current_user.id, 
        role=WorkspaceMemberRole.OWNER
    )
    return WorkspacePublic.model_validate(workspace)

@router.get(
    "/{id}", 
    response_model=WorkspacePublic
)
async def get_workspaces(
    session: AsyncSessionDep,
    current_user: CurrentUser,
    id: UUID,
) -> WorkspacePublic:
    """
    Retrieve workspaces that the current user is a member of.
    """
    result = await workspaces.get_by_id_for_user(session, user_id=current_user.id, workspace_id=id)
    if not result:
        raise HTTPException(status_code=404, detail="Workspace not found or you are not a member.")
    return WorkspacePublic.model_validate(result)

async def _is_workspace_owner(session: AsyncSessionDep, user_id: UUID, workspace_id: UUID) -> bool:
    """
    Helper function to check if a user is the owner of a workspace.
    """
    workspace = await workspaces.get_by_id_for_user(session, workspace_id=workspace_id, user_id=user_id)
    return workspace is not None and workspace.owner_id == user_id

@router.post(
    "/{workspace_id}/members",
    response_model=WorkspaceInvatedUsers,
)
async def invite_users(
    session: AsyncSessionDep,
    current_user: CurrentUser,
    workspace_id: UUID,
    members: list[WorkspaceMemberInvite],
) -> WorkspaceInvatedUsers:
    """
    Invite multiple users to a workspace.
    """
    # Check if the current user is the owner of the workspace
    if not await _is_workspace_owner(session, current_user.id, workspace_id):
        raise HTTPException(status_code=403, detail="Only workspace owners can invite members.")
    
    # check if all user_ids exist in the users table
    requested_ids = [m.user_id for m in members]
    existing_ids = await users.get_existing_ids(session, requested_ids)
    invalid_ids = [uid for uid in requested_ids if uid not in existing_ids]
    if invalid_ids:
        raise HTTPException(
            status_code=422,
            detail={"message": "Invalid user IDs", "invalid_ids": [str(i) for i in invalid_ids]},
        )
    
    # Add members in bulk, skipping those who are already members
    members = await workspace_members.add_members_bulk(
        session, workspace_id=workspace_id, members=members
    )
    return WorkspaceInvatedUsers(
        invited_members=[member.user_id for member in members]
    )

@router.delete(
    "/{workspace_id}/members/{user_id}",
    response_model=Message,
)
async def remove_member(
    session: AsyncSessionDep,
    current_user: CurrentUser,
    workspace_id: UUID,
    user_id: UUID,
) -> Message:
    """
    Remove a member from a workspace.
    """
    # Check if the current user is the owner of the workspace
    if not await _is_workspace_owner(session, current_user.id, workspace_id):
        raise HTTPException(status_code=403, detail="Only workspace owners can remove members.")
    
    # Check if the member to be removed exists
    membership = await workspace_members.get_member(session, workspace_id=workspace_id, user_id=user_id)
    if not membership:
        raise HTTPException(status_code=404, detail="Member not found in this workspace.")
    
    await workspace_members.delete(session, membership)
    return Message(message="User deleted successfully")