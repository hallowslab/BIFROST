from django.contrib import admin

from .models import (
    Event,
    Note,
    Project,
    ProjectType,
    Reference,
    Task,
)


# ---------------------------------------------------------------------------
# ProjectType admin
# ---------------------------------------------------------------------------


@admin.register(ProjectType)
class ProjectTypeAdmin(admin.ModelAdmin):
    list_display = ("name", "slug")
    search_fields = ("name",)
    prepopulated_fields = {"slug": ("name",)}
    ordering = ("name",)


# ---------------------------------------------------------------------------
# Inlines for ProjectAdmin
# ---------------------------------------------------------------------------


class TaskInline(admin.TabularInline):
    model = Task
    extra = 0
    fields = ("title", "status", "assigned_to", "completed_at")
    readonly_fields = ("completed_at",)
    autocomplete_fields = ("assigned_to",)
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
    """
    Events are read-only in the inline — they should never be edited directly.
    Use the standalone EventAdmin for full inspection.
    """

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


# ---------------------------------------------------------------------------
# ProjectAdmin
# ---------------------------------------------------------------------------


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
    autocomplete_fields = ("owner", "project_type")
    ordering = ("-created_at",)

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
            "Timestamps",
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )

    inlines = [TaskInline, NoteInline, EventInline, ReferenceInline]

    @admin.display(description="Type")
    def display_type(self, obj: Project) -> str:
        return obj.display_type


# ---------------------------------------------------------------------------
# Standalone admin classes
# ---------------------------------------------------------------------------


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
    autocomplete_fields = ("project", "assigned_to")
    ordering = ("-created_at",)


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

    # Events are audit records — no adding, changing, or deleting via admin
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
