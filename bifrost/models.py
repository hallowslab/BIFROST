import uuid

from django.contrib.auth.models import User
from django.db import models
from django.utils.text import slugify


# ---------------------------------------------------------------------------
# Admin-managed project type catalogue
# ---------------------------------------------------------------------------


class ProjectType(models.Model):
    """
    Admin-managed catalogue of project types.
    New entries can be added through the Django admin without code changes.
    """

    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=120, unique=True, blank=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "Project Type"
        verbose_name_plural = "Project Types"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


# ---------------------------------------------------------------------------
# Choices
# ---------------------------------------------------------------------------


class ProjectStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    PLANNED = "planned", "Planned"
    IN_PROGRESS = "in_progress", "In Progress"
    BLOCKED = "blocked", "Blocked"
    COMPLETED = "completed", "Completed"
    ARCHIVED = "archived", "Archived"


class TaskStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    IN_PROGRESS = "in_progress", "In Progress"
    COMPLETED = "completed", "Completed"
    CANCELLED = "cancelled", "Cancelled"


class EventType(models.TextChoices):
    PROJECT_CREATED = "project_created", "Project Created"
    PROJECT_COMPLETED = "project_completed", "Project Completed"
    PROJECT_TRANSFERRED = "project_transferred", "Project Transferred"
    TASK_CREATED = "task_created", "Task Created"
    TASK_COMPLETED = "task_completed", "Task Completed"
    TASK_DELETED = "task_deleted", "Task Deleted"
    ISSUE_IDENTIFIED = "issue_identified", "Issue Identified"
    STATUS_CHANGED = "status_changed", "Status Changed"
    NOTE_ADDED = "note_added", "Note Added"
    NOTE_DELETED = "note_deleted", "Note Deleted"
    REFERENCE_ADDED = "reference_added", "Reference Added"
    REFERENCE_DELETED = "reference_deleted", "Reference Deleted"
    OTHER = "other", "Other"


class ReferenceType(models.TextChoices):
    WHMCS_TICKET = "whmcs_ticket", "WHMCS Ticket"
    GIT_REPOSITORY = "git_repository", "Git Repository"
    CUSTOMER_ID = "customer_id", "Customer ID"
    EXTERNAL_JOB_ID = "external_job_id", "External Job ID"
    OTHER = "other", "Other"


# ---------------------------------------------------------------------------
# Core models
# ---------------------------------------------------------------------------


class Project(models.Model):
    """
    Central unit of work in Bifrost.

    project_type links to the admin-managed ProjectType catalogue.
    project_type_custom allows a free-text override when the predefined
    list does not cover an edge case.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    project_type = models.ForeignKey(
        ProjectType,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="projects",
    )
    project_type_custom = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Optional free-text type if the catalogue does not have a match.",
    )
    status = models.CharField(
        max_length=20,
        choices=ProjectStatus.choices,
        default=ProjectStatus.DRAFT,
        db_index=True,
    )
    owner = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name="owned_projects",
    )
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "created_at"]),
            models.Index(fields=["owner", "status"]),
        ]

    def __str__(self):
        return self.name

    @property
    def display_type(self) -> str:
        """Return the effective project type label for display."""
        if self.project_type_custom:
            return self.project_type_custom
        if self.project_type:
            return self.project_type.name
        return "—"


class Task(models.Model):
    """
    Actionable work item belonging to a Project.

    assigned_to represents current responsibility.
    completed_at is set by the service layer when status → COMPLETED.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="tasks",
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    status = models.CharField(
        max_length=20,
        choices=TaskStatus.choices,
        default=TaskStatus.PENDING,
        db_index=True,
    )
    assigned_to = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_tasks",
        help_text="Who currently holds responsibility for this task.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["project", "status"]),
        ]

    def __str__(self):
        return f"{self.title} [{self.get_status_display()}]"


class Note(models.Model):
    """
    Operational knowledge store for a Project.
    Used for observations, decisions, technical context, and history.
    """

    id = models.BigAutoField(primary_key=True)
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="notes",
    )
    title = models.CharField(max_length=255)
    content = models.TextField()
    author = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name="bifrost_notes",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title


class Event(models.Model):
    """
    Immutable timeline entry for a Project.

    actor  — the user who performed the action.
    assigned_to — who held responsibility at the time of the event.

    Events should only be created through the services layer to preserve
    a clean audit trail.
    """

    id = models.BigAutoField(primary_key=True)
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="events",
    )
    event_type = models.CharField(
        max_length=30,
        choices=EventType.choices,
        default=EventType.OTHER,
        db_index=True,
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    actor = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="bifrost_events_as_actor",
        help_text="User who performed the action that triggered this event.",
    )
    assigned_to = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="bifrost_events_as_assignee",
        help_text="Who held responsibility for the project at the time of this event.",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["project", "created_at"]),
            models.Index(fields=["event_type", "created_at"]),
        ]

    def __str__(self):
        return f"{self.get_event_type_display()} — {self.title}"


class Reference(models.Model):
    """
    Link to an external system or identifier for a Project.
    Examples: WHMCS tickets, Git repositories, customer IDs.
    """

    id = models.BigAutoField(primary_key=True)
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="references",
    )
    reference_type = models.CharField(
        max_length=20,
        choices=ReferenceType.choices,
        default=ReferenceType.OTHER,
        db_index=True,
    )
    value = models.CharField(max_length=500)

    class Meta:
        ordering = ["reference_type", "value"]

    def __str__(self):
        return f"{self.get_reference_type_display()}: {self.value}"
