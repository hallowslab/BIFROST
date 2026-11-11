import uuid

from django.contrib.auth.models import User
from django.db import models
from django.utils.text import slugify


class ProjectType(models.Model):
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


class IssueStatus(models.TextChoices):
    IDENTIFIED = "identified", "Identified"
    INVESTIGATING = "investigating", "Investigating"
    RESOLVED = "resolved", "Resolved"
    CLOSED = "closed", "Closed"


class EventType(models.TextChoices):
    PROJECT_CREATED = "project_created", "Project Created"
    PROJECT_COMPLETED = "project_completed", "Project Completed"
    PROJECT_TRANSFERRED = "project_transferred", "Project Transferred"
    TASK_CREATED = "task_created", "Task Created"
    TASK_COMPLETED = "task_completed", "Task Completed"
    TASK_DELETED = "task_deleted", "Task Deleted"
    TASK_ASSIGNED = "task_assigned", "Task Assigned"
    ISSUE_IDENTIFIED = "issue_identified", "Issue Identified"
    ISSUE_RESOLVED = "issue_resolved", "Issue Resolved"
    ISSUE_CLOSED = "issue_closed", "Issue Closed"
    RESOLUTION_APPLIED = "resolution_applied", "Resolution Applied"
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


class Project(models.Model):
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
    project_template = models.ForeignKey(
        "ProjectTemplate",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="projects",
        help_text="Optional template this project was created from.",
    )
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
        if self.project_type_custom:
            return self.project_type_custom
        if self.project_type:
            return self.project_type.name
        return "\u2014"


class Task(models.Model):
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
    task_template = models.ForeignKey(
        "TaskTemplate",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tasks",
        help_text="Optional template this task was derived from.",
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


class TaskStep(models.Model):
    task = models.ForeignKey(
        Task,
        on_delete=models.CASCADE,
        related_name="steps",
    )
    order = models.PositiveIntegerField()
    description = models.TextField()
    completed = models.BooleanField(default=False)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return f"Step {self.order}: {self.description[:60]}"


class Issue(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="issues",
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    status = models.CharField(
        max_length=20,
        choices=IssueStatus.choices,
        default=IssueStatus.IDENTIFIED,
        db_index=True,
    )
    identified_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name="identified_issues",
    )
    issue_template = models.ForeignKey(
        "IssueTemplate",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="issues",
        help_text="Optional template this issue matches.",
    )
    tasks = models.ManyToManyField(
        "Task",
        blank=True,
        related_name="issues",
        help_text="Tasks in this project that this issue is linked to.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["project", "status"]),
            models.Index(fields=["status", "created_at"]),
        ]

    def __str__(self):
        return f"{self.title} [{self.get_status_display()}]"


class Resolution(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    issue = models.ForeignKey(
        Issue,
        on_delete=models.CASCADE,
        related_name="resolutions",
    )
    description = models.TextField()
    created_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name="resolutions",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Resolution for {self.issue.title}"


class ResolutionStep(models.Model):
    resolution = models.ForeignKey(
        Resolution,
        on_delete=models.CASCADE,
        related_name="steps",
    )
    order = models.PositiveIntegerField()
    description = models.TextField()
    completed = models.BooleanField(default=False)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return f"Step {self.order}: {self.description[:60]}"


class Note(models.Model):
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
        return f"{self.get_event_type_display()} \u2014 {self.title}"


class Reference(models.Model):
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
