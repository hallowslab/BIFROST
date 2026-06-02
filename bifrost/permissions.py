from django.contrib.auth.models import User
from django.db.models import Q, QuerySet

from .models import Project, Task


def visible_projects_for(user: User) -> QuerySet[Project]:
    """Projects a user may view."""
    queryset = Project.objects.select_related("owner", "project_type")
    if user.is_superuser:
        return queryset
    return queryset.filter(Q(owner=user) | Q(tasks__assigned_to=user)).distinct()


def can_view_project(user: User, project: Project) -> bool:
    """Return True when the user may open the project detail page."""
    if user.is_superuser:
        return True
    return project.owner_id == user.id or project.tasks.filter(assigned_to=user).exists()


def can_manage_project(user: User, project: Project) -> bool:
    """Return True when the user may edit or transfer the project."""
    return user.is_superuser or project.owner_id == user.id


def can_edit_task(user: User, task: Task) -> bool:
    """Return True when the user may edit or complete a task."""
    if user.is_superuser:
        return True
    return task.project.owner_id == user.id or task.assigned_to_id == user.id
