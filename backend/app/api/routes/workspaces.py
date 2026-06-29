from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException

from app.api.deps import (
    AsyncSessionDep,
    CurrentUser,
    get_current_active_superuser,
    require_workspace_role,
)
from app.core.config import settings
from app.models import (
    CreateWorkspaceRequest,
    Message,
    WorkspaceResponse,
    WorkspacesResponse,
)
from app.models.enums import WorkspaceMemberRole
from app.models.workspace import WorkspaceMember
from app.repositories import (
    projects,
    users,
    workspace_members,
    workspaces,
)
from app.schemas.project import (
    CreateProjectRequest,
    ProjectResponse,
)
from app.schemas.workspace import (
    InviteMemberRequest,
    InviteMembersResponse,
    UpdateWorkspaceRequest,
    WorkspaceMembersResponse,
)
from app.utils import send_email

router = APIRouter(prefix="/workspaces", tags=["workspaces"])

# Dependency alias cho tung muc quyen trong workspace
WorkspaceOwnerDep = Annotated[
    WorkspaceMember, Depends(require_workspace_role(WorkspaceMemberRole.OWNER))
]
WorkspaceEditorDep = Annotated[
    WorkspaceMember, Depends(require_workspace_role(WorkspaceMemberRole.EDITOR))
]
WorkspaceViewerDep = Annotated[
    WorkspaceMember, Depends(require_workspace_role(WorkspaceMemberRole.VIEWER))
]


@router.get(
    "/",
    dependencies=[Depends(get_current_active_superuser)],
    response_model=WorkspacesResponse,
)
async def list_workspaces(
    session: AsyncSessionDep,
    page: int = 0,
    limit: int = 20,
) -> WorkspacesResponse:
    """Lay danh sach tat ca workspace trong he thong. Chi danh cho superuser."""
    result = await workspaces.list_all(session, page=page, limit=limit)
    return WorkspacesResponse(
        data=[WorkspaceResponse.model_validate(w) for w in result.items],
        count=result.total,
    )


@router.get("/me", response_model=WorkspacesResponse)
async def list_my_workspaces(
    session: AsyncSessionDep,
    current_user: CurrentUser,
    page: int = 0,
    limit: int = 20,
) -> WorkspacesResponse:
    """Lay danh sach workspace ma user hien tai la thanh vien (bat ke role)."""
    result = await workspaces.list_for_user(
        session, user_id=current_user.id, page=page, limit=limit
    )
    return WorkspacesResponse(
        data=[WorkspaceResponse.model_validate(w) for w in result.items],
        count=result.total,
    )


@router.post(
    "/",
    response_model=WorkspaceResponse,
    status_code=201,
)
async def create_workspace(
    *,
    session: AsyncSessionDep,
    current_user: CurrentUser,
    workspace_in: CreateWorkspaceRequest,
) -> WorkspaceResponse:
    """Tao workspace moi. Nguoi tao tu dong tro thanh OWNER."""
    workspace = await workspaces.create(
        session, owner_id=current_user.id, workspace_in=workspace_in
    )
    await workspace_members.add_member(
        session,
        workspace_id=workspace.id,
        user_id=current_user.id,
        role=WorkspaceMemberRole.OWNER,
    )
    return WorkspaceResponse.model_validate(workspace)


@router.get("/{workspace_id}", response_model=WorkspaceResponse)
async def get_workspace(
    session: AsyncSessionDep,
    workspace_id: UUID,
    _: WorkspaceViewerDep,
) -> WorkspaceResponse:
    """Lay thong tin workspace. Yeu cau la thanh vien (bat ke role)."""
    workspace = await workspaces.get(session, workspace_id)
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found.")
    return WorkspaceResponse.model_validate(workspace)


@router.patch("/{workspace_id}", response_model=WorkspaceResponse)
async def update_workspace(
    *,
    session: AsyncSessionDep,
    workspace_id: UUID,
    workspace_in: UpdateWorkspaceRequest,
    _: WorkspaceOwnerDep,
) -> WorkspaceResponse:
    """Cap nhat thong tin workspace. Chi OWNER moi co quyen."""
    workspace = await workspaces.get(session, workspace_id)
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found.")
    updated = await workspaces.update(
        session, workspace, workspace_in.model_dump(exclude_unset=True)
    )
    return WorkspaceResponse.model_validate(updated)


@router.delete("/{workspace_id}", response_model=Message)
async def delete_workspace(
    *,
    session: AsyncSessionDep,
    workspace_id: UUID,
    _: WorkspaceOwnerDep,
) -> Message:
    """Xoa workspace va toan bo du lieu lien quan. Chi OWNER moi co quyen."""
    workspace = await workspaces.get(session, workspace_id)
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found.")
    await workspaces.delete(session, workspace)
    return Message(message="Workspace deleted successfully.")


@router.post(
    "/{workspace_id}/members",
    response_model=InviteMembersResponse,
)
async def invite_users(
    *,
    session: AsyncSessionDep,
    background_tasks: BackgroundTasks,
    workspace_id: UUID,
    members: list[InviteMemberRequest],
    _: WorkspaceOwnerDep,
) -> InviteMembersResponse:
    """
    Moi nhieu user vao workspace. Chi OWNER moi co quyen.
    Gui email thong bao cho tung thanh vien duoc moi (neu email duoc cau hinh).
    """
    requested_ids = [m.user_id for m in members]
    existing_ids = await users.get_existing_ids(session, requested_ids)
    invalid_ids = [uid for uid in requested_ids if uid not in existing_ids]
    if invalid_ids:
        raise HTTPException(
            status_code=422,
            detail={
                "message": "Invalid user IDs",
                "invalid_ids": [str(i) for i in invalid_ids],
            },
        )

    added = await workspace_members.add_members_bulk(
        session, workspace_id=workspace_id, members=members
    )

    if settings.emails_enabled and added:
        workspace = await workspaces.get(session, workspace_id)
        workspace_name = workspace.name if workspace else str(workspace_id)
        for member_record in added:
            user = await users.get(session, member_record.user_id)
            if user:
                background_tasks.add_task(
                    send_email,
                    email_to=user.email,
                    subject=f"You are invited to '{workspace_name}'",
                    html_content=(
                        f"<p>Hello {user.full_name or user.email},</p>"
                        f"<p>You have been invited to join the workspace <strong>{workspace_name}</strong> "
                        f"with the role of <strong>{member_record.role.value}</strong>.</p>"
                    ),
                )

    return InviteMembersResponse(invited_members=[m.user_id for m in added])


@router.delete(
    "/{workspace_id}/members/{user_id}",
    response_model=Message,
)
async def remove_member(
    *,
    session: AsyncSessionDep,
    workspace_id: UUID,
    user_id: UUID,
    _: WorkspaceOwnerDep,
) -> Message:
    """Xoa thanh vien khoi workspace. Chi OWNER moi co quyen."""
    membership = await workspace_members.get_member(
        session, workspace_id=workspace_id, user_id=user_id
    )
    if not membership:
        raise HTTPException(
            status_code=404, detail="Member not found in this workspace."
        )
    await workspace_members.delete(session, membership)
    return Message(message="User removed from workspace successfully.")


@router.get(
    "/{workspace_id}/members",
    response_model=WorkspaceMembersResponse,
)
async def list_workspace_members(
    session: AsyncSessionDep,
    workspace_id: UUID,
    current_user: CurrentUser,
    page: int = 0,
    limit: int = 50,
) -> WorkspaceMembersResponse:
    """
    Lay danh sach thanh vien cua workspace.
    Chi danh cho superuser hoac workspace OWNER.
    """
    if not current_user.is_superuser:
        membership = await workspace_members.get_member(
            session, workspace_id=workspace_id, user_id=current_user.id
        )
        if not membership or membership.role != WorkspaceMemberRole.OWNER:
            raise HTTPException(
                status_code=403,
                detail="Only workspace owners or superusers can view member list.",
            )

    result = await workspace_members.list_members(
        session, workspace_id=workspace_id, page=page, limit=limit
    )
    return WorkspaceMembersResponse(
        data=result.items,
        count=result.total,
    )


@router.post(
    "/{workspace_id}/projects",
    response_model=ProjectResponse,
    status_code=201,
)
async def create_project(
    *,
    session: AsyncSessionDep,
    workspace_id: UUID,
    project_in: CreateProjectRequest,
    _: WorkspaceEditorDep,
) -> ProjectResponse:
    """Tao project moi trong workspace. Yeu cau quyen EDITOR tro len."""
    data = project_in.model_dump()
    data["workspace_id"] = workspace_id
    project = await projects.create(session, data)
    return ProjectResponse.model_validate(project)
