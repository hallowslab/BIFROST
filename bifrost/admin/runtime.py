from django.contrib import admin, messages

from .. import services
from ..models.runtime import (
    Event,
    Issue,
    Note,
    Project,
    ProjectType,
    Reference,
    Resolution,
    ResolutionStep,
    Task,
    TaskStep,
)


def promote_projects_to_templates(modeladmin, request, queryset):
    for project in queryset:
        services.promote_project_to_template(project=project, admin=request.user)
    messages.success(request, f"{queryset.count()} project(s) promoted to templates.")


promote_projects_to_templates.short_description = "Promote selected projects to templates"


def promote_tasks_to_templates(modeladmin, request, queryset):
    for task in queryset:
        services.promote_task_to_template(task=task, admin=request.user)
    messages.success(request, f"{queryset.count()} task(s) promoted to templates.")


promote_tasks_to_templates.short_description = "Promote selected tasks to templates"


def promote_issues_to_templates(modeladmin, request, queryset):
    for issue in queryset:
        services.promote_issue_to_template(issue=issue, admin=request.user)
    messages.success(request, f"{queryset.count()} issue(s) promoted to templates.")


promote_issues_to_templates.short_description = "Promote selected issues to templates"


@admin.register(ProjectType)
class ProjectTypeAdmin(admin.ModelAdmin):
    list_display = ("name", "slug")
    search_fields = ("name",)
    prepopulated_fields = {"slug": ("name",)}
    ordering = ("name",)


class TaskInline(admin.TabularInline):
    model = Task
    extra = 0
    fields = ("title", "status", "assigned_to", "completed_at")
    readonly_fields = ("completed_at",)
    autocomplete_fields = ("assigned_to",)
    show_change_link = True
    ordering = ("-created_at",)


class TaskStepInline(admin.TabularInline):
    model = TaskStep
    extra = 1
    fields = ("order", "description", "completed")
    ordering = ("order",)


class IssueInline(admin.TabularInline):
    model = Issue
    extra = 0
    fields = ("title", "status", "identified_by", "created_at")
    readonly_fields = ("created_at",)
    autocomplete_fields = ("identified_by",)
    show_change_link = True
    ordering = ("-created_at",)


class NoteInline(admin.TabularInline):
    model = Note
    extra = 0
    fields = ("title", "author", "created_at")
    readonly_fields = ("author", "created_at")
    show_change_link = True
    ordering = ("-created_at",)


class EventInline(admin.TabularInline):
    model = Event
    extra = 0
    fields = ("created_at", "event_type", "title", "actor", "assigned_to")
    readonly_fields = ("created_at", "event_type", "title", "actor", "assigned_to")
    ordering = ("-created_at",)
    show_change_link = True

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class ReferenceInline(admin.TabularInline):
    model = Reference
    extra = 0
    fields = ("reference_type", "value")
    ordering = ("reference_type", "value")


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "display_type",
        "status",
        "owner",
        "created_at",
        "updated_at",
    )
    list_filter = ("status", "project_type", "owner", "created_at")
    search_fields = ("name", "project_type_custom", "description", "owner__username")
    readonly_fields = ("id", "created_at", "updated_at")
    autocomplete_fields = ("owner", "project_type", "project_template")
    ordering = ("-created_at",)
    actions = [promote_projects_to_templates]

    fieldsets = (
        (
            "Identity",
            {
                "fields": (
                    "id",
                    "name",
                    "project_type",
                    "project_type_custom",
                    "status",
                    "owner",
                )
            },
        ),
        (
            "Details",
            {"fields": ("description",)},
        ),
        (
            "Knowledge Link",
            {"fields": ("project_template",), "classes": ("collapse",)},
        ),
        (
            "Timestamps",
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )

    inlines = [TaskInline, IssueInline, NoteInline, EventInline, ReferenceInline]

    @admin.display(description="Type")
    def display_type(self, obj: Project) -> str:
        return obj.display_type


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "project",
        "status",
        "assigned_to",
        "created_at",
        "completed_at",
    )
    list_filter = ("status", "assigned_to", "created_at")
    search_fields = ("title", "project__name", "assigned_to__username")
    readonly_fields = ("id", "created_at", "completed_at")
    autocomplete_fields = ("project", "assigned_to", "task_template")
    ordering = ("-created_at",)
    actions = [promote_tasks_to_templates]
    inlines = [TaskStepInline]


@admin.register(TaskStep)
class TaskStepAdmin(admin.ModelAdmin):
    list_display = ("task", "order", "description", "completed")
    list_filter = ("completed",)
    ordering = ("task", "order")


@admin.register(Issue)
class IssueAdmin(admin.ModelAdmin):
    list_display = ("title", "project", "status", "identified_by", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("title", "project__name", "identified_by__username")
    readonly_fields = ("id", "created_at", "updated_at")
    autocomplete_fields = ("project", "identified_by", "issue_template", "tasks")
    filter_horizontal = ("tasks",)
    ordering = ("-created_at",)
    actions = [promote_issues_to_templates]


class ResolutionStepInline(admin.TabularInline):
    model = ResolutionStep
    extra = 1
    fields = ("order", "description", "completed")
    ordering = ("order",)


@admin.register(Resolution)
class ResolutionAdmin(admin.ModelAdmin):
    list_display = ("issue", "created_by", "created_at")
    readonly_fields = ("created_at",)
    autocomplete_fields = ("issue", "created_by")
    ordering = ("-created_at",)
    inlines = [ResolutionStepInline]


@admin.register(Note)
class NoteAdmin(admin.ModelAdmin):
    list_display = ("title", "project", "author", "created_at")
    list_filter = ("author", "created_at")
    search_fields = ("title", "content", "project__name", "author__username")
    readonly_fields = ("id", "created_at")
    autocomplete_fields = ("project", "author")
    ordering = ("-created_at",)


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = (
        "created_at",
        "event_type",
        "title",
        "project",
        "actor",
        "assigned_to",
    )
    list_filter = ("event_type", "created_at")
    search_fields = ("title", "description", "project__name", "actor__username")
    readonly_fields = (
        "id",
        "project",
        "event_type",
        "title",
        "description",
        "actor",
        "assigned_to",
        "created_at",
    )
    ordering = ("-created_at",)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Reference)
class ReferenceAdmin(admin.ModelAdmin):
    list_display = ("reference_type", "value", "project")
    list_filter = ("reference_type",)
    search_fields = ("value", "project__name")
    readonly_fields = ("id",)
    autocomplete_fields = ("project",)
    ordering = ("reference_type", "value")
