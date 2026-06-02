"""
Bifrost service layer.

This module is the ONLY place that creates Event records. All views must call
functions here instead of directly calling Model.objects.create() or .save()
for any business operation, ensuring a consistent and complete audit trail.
"""

from django.contrib.auth.models import User
from django.utils import timezone

from .models import (
    Event,
    EventType,
    Note,
    Project,
    ProjectStatus,
    ProjectType,
    Reference,
    Task,
    TaskStatus,
)


# ---------------------------------------------------------------------------
# Project services
# ---------------------------------------------------------------------------


def create_project(
    *,
    name: str,
    owner: User,
    project_type: ProjectType | None = None,
    project_type_custom: str | None = None,
    status: str = ProjectStatus.DRAFT,
    description: str | None = None,
) -> Project:
    """
    Create a new Project and emit the 'Project Created' event.
    Always use this function instead of Project.objects.create() directly.
    """
    project = Project.objects.create(
        name=name,
        owner=owner,
        project_type=project_type,
        project_type_custom=project_type_custom,
        status=status,
        description=description,
    )

    Event.objects.create(
        project=project,
        event_type=EventType.PROJECT_CREATED,
        title="Project Created",
        description=f'Project "{name}" was created.',
        actor=owner,
        assigned_to=owner,
    )

    return project


def update_project_status(
    *,
    project: Project,
    new_status: str,
    actor: User,
) -> Project:
    """
    Update a project's status and emit a 'Status Changed' event.
    Also emits 'Project Completed' if transitioning to COMPLETED.
    """
    old_status = project.get_status_display()
    project.status = new_status
    project.save(update_fields=["status", "updated_at"])

    new_status_label = project.get_status_display()

    Event.objects.create(
        project=project,
        event_type=EventType.STATUS_CHANGED,
        title="Status Changed",
        description=f"Status changed from {old_status} to {new_status_label}.",
        actor=actor,
        assigned_to=project.owner,
    )

    if new_status == ProjectStatus.COMPLETED:
        Event.objects.create(
            project=project,
            event_type=EventType.PROJECT_COMPLETED,
            title="Project Completed",
            description=f'Project "{project.name}" was marked as completed.',
            actor=actor,
            assigned_to=project.owner,
        )

    return project


def update_project(
    *,
    project: Project,
    actor: User,
    name: str | None = None,
    project_type: ProjectType | None = None,
    project_type_custom: str | None = None,
    status: str | None = None,
    description: str | None = None,
) -> Project:
    """
    Update project fields. Delegates status changes to update_project_status
    so that status-change events are always emitted.
    """
    old_status = project.status

    update_fields = ["updated_at"]

    if name is not None:
        project.name = name
        update_fields.append("name")
    if project_type is not None or "project_type" in (project_type or ""):
        project.project_type = project_type
        update_fields.append("project_type")
    if project_type_custom is not None:
        project.project_type_custom = project_type_custom
        update_fields.append("project_type_custom")
    if description is not None:
        project.description = description
        update_fields.append("description")

    project.save(update_fields=update_fields)

    if status is not None and status != old_status:
        update_project_status(project=project, new_status=status, actor=actor)

    return project


def transfer_project(*, project: Project, new_owner: User, actor: User) -> Project:
    """Transfer a project to another user and emit an audit event."""
    old_owner = project.owner
    if old_owner.id == new_owner.id:
        return project

    project.owner = new_owner
    project.save(update_fields=["owner", "updated_at"])

    Event.objects.create(
        project=project,
        event_type=EventType.PROJECT_TRANSFERRED,
        title="Project Transferred",
        description=(
            f'Project "{project.name}" was transferred from '
            f"{old_owner.get_full_name() or old_owner.username} to "
            f"{new_owner.get_full_name() or new_owner.username}."
        ),
        actor=actor,
        assigned_to=new_owner,
    )

    return project


# ---------------------------------------------------------------------------
# Task services
# ---------------------------------------------------------------------------


def create_task(
    *,
    project: Project,
    title: str,
    actor: User,
    description: str | None = None,
    status: str = TaskStatus.PENDING,
    assigned_to: User | None = None,
) -> Task:
    """
    Create a new Task for a Project and emit 'Task Created' event.
    """
    task = Task.objects.create(
        project=project,
        title=title,
        description=description,
        status=status,
        assigned_to=assigned_to,
    )

    Event.objects.create(
        project=project,
        event_type=EventType.TASK_CREATED,
        title="Task Created",
        description=f'Task "{title}" was created.',
        actor=actor,
        assigned_to=assigned_to or project.owner,
    )

    return task


def complete_task(*, task: Task, actor: User) -> Task:
    """
    Mark a Task as completed.
    Sets completed_at, updates status to COMPLETED, and emits a
    'Task Completed' event on the parent Project.
    """
    task.status = TaskStatus.COMPLETED
    task.completed_at = timezone.now()
    task.save(update_fields=["status", "completed_at"])

    Event.objects.create(
        project=task.project,
        event_type=EventType.TASK_COMPLETED,
        title="Task Completed",
        description=f'Task "{task.title}" was completed.',
        actor=actor,
        assigned_to=task.assigned_to,
    )

    return task


def update_task(
    *,
    task: Task,
    actor: User,
    title: str | None = None,
    description: str | None = None,
    status: str | None = None,
    assigned_to: User | None = None,
) -> Task:
    """
    Update task fields. Delegates completion to complete_task() so that
    completion events are always emitted.
    """
    update_fields = []

    if title is not None:
        task.title = title
        update_fields.append("title")
    if description is not None:
        task.description = description
        update_fields.append("description")
    if assigned_to is not None:
        task.assigned_to = assigned_to
        update_fields.append("assigned_to")

    if update_fields:
        task.save(update_fields=update_fields)

    if status is not None and status != task.status:
        if status == TaskStatus.COMPLETED:
            complete_task(task=task, actor=actor)
        else:
            task.status = status
            task.save(update_fields=["status"])

    return task


# ---------------------------------------------------------------------------
# Note services
# ---------------------------------------------------------------------------


def create_note(
    *,
    project: Project,
    title: str,
    content: str,
    author: User,
) -> Note:
    """
    Create a Note and emit a 'Note Added' event.
    """
    note = Note.objects.create(
        project=project,
        title=title,
        content=content,
        author=author,
    )

    Event.objects.create(
        project=project,
        event_type=EventType.NOTE_ADDED,
        title="Note Added",
        description=f'Note "{title}" was added.',
        actor=author,
        assigned_to=project.owner,
    )

    return note


# ---------------------------------------------------------------------------
# Event services
# ---------------------------------------------------------------------------


def create_event(
    *,
    project: Project,
    event_type: str,
    title: str,
    actor: User,
    description: str | None = None,
    assigned_to: User | None = None,
) -> Event:
    """
    Manually create an Event (e.g. 'Issue Identified', 'Other').
    Auto-events (Project Created, Task Completed, etc.) should not be
    triggered through this function from the UI — they are created
    automatically by the relevant service functions.
    """
    return Event.objects.create(
        project=project,
        event_type=event_type,
        title=title,
        description=description,
        actor=actor,
        assigned_to=assigned_to or project.owner,
    )


# ---------------------------------------------------------------------------
# Reference services
# ---------------------------------------------------------------------------


def create_reference(
    *,
    project: Project,
    reference_type: str,
    value: str,
    actor: User,
) -> Reference:
    """
    Create a Reference link for a Project.
    """
    ref = Reference.objects.create(
        project=project,
        reference_type=reference_type,
        value=value,
    )

    Event.objects.create(
        project=project,
        event_type=EventType.REFERENCE_ADDED,
        title="Reference Added",
        description=f'Reference "{ref.get_reference_type_display()}: {value}" was added.',
        actor=actor,
        assigned_to=project.owner,
    )

    return ref


# ---------------------------------------------------------------------------
# Deletion services
# ---------------------------------------------------------------------------


def delete_task(*, task: Task, actor: User) -> None:
    """
    Delete a Task and emit a 'Task Deleted' event.
    """
    title = task.title
    project = task.project
    task.delete()

    Event.objects.create(
        project=project,
        event_type=EventType.TASK_DELETED,
        title="Task Deleted",
        description=f'Task "{title}" was deleted.',
        actor=actor,
        assigned_to=project.owner,
    )


def delete_note(*, note: Note, actor: User) -> None:
    """
    Delete a Note and emit a 'Note Deleted' event.
    """
    title = note.title
    project = note.project
    note.delete()

    Event.objects.create(
        project=project,
        event_type=EventType.NOTE_DELETED,
        title="Note Deleted",
        description=f'Note "{title}" was deleted.',
        actor=actor,
        assigned_to=project.owner,
    )


def delete_reference(*, reference: Reference, actor: User) -> None:
    """
    Delete a Reference and emit a 'Reference Deleted' event.
    """
    val = reference.value
    ref_type = reference.get_reference_type_display()
    project = reference.project
    reference.delete()

    Event.objects.create(
        project=project,
        event_type=EventType.REFERENCE_DELETED,
        title="Reference Deleted",
        description=f'Reference "{ref_type}: {val}" was deleted.',
        actor=actor,
        assigned_to=project.owner,
    )


def delete_event(*, event: Event) -> None:
    """
    Delete a Timeline Event (admin only, direct DB deletion).
    """
    event.delete()
