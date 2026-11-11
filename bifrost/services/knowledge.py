from ..models.knowledge import (
    IssueTemplate,
    ProjectTemplate,
    TaskTemplate,
)


def create_project_template(
    *,
    name: str,
    description: str | None = None,
) -> ProjectTemplate:
    return ProjectTemplate.objects.create(
        name=name,
        description=description,
    )


def create_task_template(
    *,
    project_template: ProjectTemplate,
    title: str,
    description: str | None = None,
    order: int = 0,
) -> TaskTemplate:
    return TaskTemplate.objects.create(
        project_template=project_template,
        title=title,
        description=description,
        order=order,
    )


def create_issue_template(
    *,
    title: str,
    description: str,
    category: str | None = None,
) -> IssueTemplate:
    return IssueTemplate.objects.create(
        title=title,
        description=description,
        category=category,
    )
