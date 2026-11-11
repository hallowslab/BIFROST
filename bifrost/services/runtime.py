from django.contrib.auth.models import User
from django.utils import timezone

from ..models.runtime import (
    Event,
    EventType,
    Issue,
    IssueStatus,
    Note,
    Project,
    ProjectStatus,
    ProjectType,
    Reference,
    Resolution,
    ResolutionStep,
    Task,
    TaskStep,
    TaskStatus,
)


def create_project(
    *,
    name: str,
    owner: User,
    project_type: ProjectType | None = None,
    project_type_custom: str | None = None,
    status: str = ProjectStatus.DRAFT,
    description: str | None = None,
) -> Project:
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


def create_task(
    *,
    project: Project,
    title: str,
    actor: User,
    description: str | None = None,
    status: str = TaskStatus.PENDING,
    assigned_to: User | None = None,
) -> Task:
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
    update_fields = []

    if title is not None:
        task.title = title
        update_fields.append("title")
    if description is not None:
        task.description = description
        update_fields.append("description")
    if assigned_to is not None:
        old_assignee = task.assigned_to
        task.assigned_to = assigned_to
        update_fields.append("assigned_to")

    if update_fields:
        task.save(update_fields=update_fields)

    if assigned_to is not None and old_assignee != assigned_to:
        Event.objects.create(
            project=task.project,
            event_type=EventType.TASK_ASSIGNED,
            title="Task Assigned",
            description=f'Task "{task.title}" assigned to {assigned_to.get_full_name() or assigned_to.username}.',
            actor=actor,
            assigned_to=assigned_to,
        )

    if status is not None and status != task.status:
        if status == TaskStatus.COMPLETED:
            complete_task(task=task, actor=actor)
        else:
            task.status = status
            task.save(update_fields=["status"])

    return task


def add_task_step(
    *,
    task: Task,
    order: int,
    description: str,
) -> TaskStep:
    return TaskStep.objects.create(
        task=task,
        order=order,
        description=description,
    )


def create_issue(
    *,
    project: Project,
    title: str,
    identified_by: User,
    description: str | None = None,
    status: str = IssueStatus.IDENTIFIED,
) -> Issue:
    issue = Issue.objects.create(
        project=project,
        title=title,
        description=description,
        status=status,
        identified_by=identified_by,
    )

    Event.objects.create(
        project=project,
        event_type=EventType.ISSUE_IDENTIFIED,
        title="Issue Identified",
        description=f'Issue "{title}" was identified.',
        actor=identified_by,
        assigned_to=project.owner,
    )

    return issue


def update_issue_status(
    *,
    issue: Issue,
    new_status: str,
    actor: User,
) -> Issue:
    old_status = issue.get_status_display()
    issue.status = new_status
    issue.save(update_fields=["status", "updated_at"])

    event_type = EventType.STATUS_CHANGED
    title = "Status Changed"
    if new_status == IssueStatus.RESOLVED:
        event_type = EventType.ISSUE_RESOLVED
        title = "Issue Resolved"
    elif new_status == IssueStatus.CLOSED:
        event_type = EventType.ISSUE_CLOSED
        title = "Issue Closed"

    Event.objects.create(
        project=issue.project,
        event_type=event_type,
        title=title,
        description=f'Issue "{issue.title}" changed from {old_status} to {issue.get_status_display()}.',
        actor=actor,
        assigned_to=issue.project.owner,
    )

    return issue


def create_resolution(
    *,
    issue: Issue,
    description: str,
    created_by: User,
) -> Resolution:
    resolution = Resolution.objects.create(
        issue=issue,
        description=description,
        created_by=created_by,
    )

    if issue.status not in (IssueStatus.RESOLVED, IssueStatus.CLOSED):
        update_issue_status(issue=issue, new_status=IssueStatus.RESOLVED, actor=created_by)

    Event.objects.create(
        project=issue.project,
        event_type=EventType.RESOLUTION_APPLIED,
        title="Resolution Applied",
        description=f'Resolution applied to issue "{issue.title}".',
        actor=created_by,
        assigned_to=issue.project.owner,
    )

    return resolution


def add_resolution_step(
    *,
    resolution: Resolution,
    order: int,
    description: str,
) -> ResolutionStep:
    return ResolutionStep.objects.create(
        resolution=resolution,
        order=order,
        description=description,
    )


def create_note(
    *,
    project: Project,
    title: str,
    content: str,
    author: User,
) -> Note:
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


def create_event(
    *,
    project: Project,
    event_type: str,
    title: str,
    actor: User,
    description: str | None = None,
    assigned_to: User | None = None,
) -> Event:
    return Event.objects.create(
        project=project,
        event_type=event_type,
        title=title,
        description=description,
        actor=actor,
        assigned_to=assigned_to or project.owner,
    )


def create_reference(
    *,
    project: Project,
    reference_type: str,
    value: str,
    actor: User,
) -> Reference:
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


def delete_task(*, task: Task, actor: User) -> None:
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
    event.delete()
