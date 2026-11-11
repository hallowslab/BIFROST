from django.contrib.auth.models import User

from ..models.knowledge import (
    IssueTemplate,
    ProjectTemplate,
    TaskTemplate,
)
from ..models.runtime import (
    Issue,
    Project,
    Task,
)


def promote_project_to_template(
    *,
    project: Project,
    admin: User,
) -> ProjectTemplate:
    template = ProjectTemplate.objects.create(
        name=project.name,
        description=project.description,
    )
    for task in project.tasks.all():
        TaskTemplate.objects.create(
            project_template=template,
            title=task.title,
            description=task.description,
        )
    return template


def promote_task_to_template(
    *,
    task: Task,
    admin: User,
) -> TaskTemplate:
    template, _ = _ensure_project_template(task.project, admin)
    return TaskTemplate.objects.create(
        project_template=template,
        title=task.title,
        description=task.description,
    )


def _ensure_project_template(project: Project, admin: User) -> tuple:
    if project.project_template_id:
        return project.project_template, False
    template = ProjectTemplate.objects.create(
        name=project.name,
        description=f"Auto-created from project {project.name}",
    )
    project.project_template = template
    project.save(update_fields=["project_template"])
    return template, True


def promote_issue_to_template(
    *,
    issue: Issue,
    admin: User,
) -> IssueTemplate:
    return IssueTemplate.objects.create(
        title=issue.title,
        description=issue.description or "",
    )


# Note: there is no knowledge-base Resolution/ResolutionStep template model in
# bifrost.models.knowledge, so a resolution cannot be promoted to a template.
# Only Issue, Project, and Task templates exist.
