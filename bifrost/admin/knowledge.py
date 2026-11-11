from django.contrib import admin

from ..models.knowledge import (
    IssueTemplate,
    ProjectTemplate,
    TaskTemplate,
)


class TaskTemplateInline(admin.TabularInline):
    model = TaskTemplate
    extra = 1
    fields = ("order", "title", "description")
    ordering = ("order", "title")


@admin.register(ProjectTemplate)
class ProjectTemplateAdmin(admin.ModelAdmin):
    list_display = ("name", "created_at", "updated_at")
    search_fields = ("name", "description")
    readonly_fields = ("id", "created_at", "updated_at")
    ordering = ("name",)
    inlines = [TaskTemplateInline]


@admin.register(TaskTemplate)
class TaskTemplateAdmin(admin.ModelAdmin):
    list_display = ("title", "project_template", "order", "created_at")
    list_filter = ("project_template",)
    search_fields = ("title", "description")
    readonly_fields = ("id", "created_at")
    autocomplete_fields = ("project_template",)
    ordering = ("project_template", "order", "title")


@admin.register(IssueTemplate)
class IssueTemplateAdmin(admin.ModelAdmin):
    list_display = ("title", "category", "created_at")
    list_filter = ("category",)
    search_fields = ("title", "description")
    readonly_fields = ("id", "created_at")
    ordering = ("title",)
