from django.urls import path

from ..views import (
    event_create,
    event_delete,
    issue_create,
    issue_link_task,
    issue_resolve,
    issue_unlink_task,
    note_create,
    note_delete,
    project_create,
    project_detail,
    project_edit,
    project_list,
    project_transfer,
    reference_create,
    reference_delete,
    task_complete,
    task_create,
    task_delete,
    task_detail,
    task_edit,
    task_step_delete,
    task_step_edit,
)

urlpatterns = [
    path("", project_list, name="project-list"),
    path("projects/create/", project_create, name="project-create"),
    path("projects/<uuid:pk>/", project_detail, name="project-detail"),
    path("projects/<uuid:pk>/edit/", project_edit, name="project-edit"),
    path("projects/<uuid:pk>/transfer/", project_transfer, name="project-transfer"),
    path("projects/<uuid:pk>/tasks/create/", task_create, name="task-create"),
    path(
        "projects/<uuid:pk>/tasks/<uuid:task_pk>/edit/",
        task_edit,
        name="task-edit",
    ),
    path(
        "projects/<uuid:pk>/tasks/<uuid:task_pk>/complete/",
        task_complete,
        name="task-complete",
    ),
    path(
        "projects/<uuid:pk>/tasks/<uuid:task_pk>/delete/",
        task_delete,
        name="task-delete",
    ),
    path("projects/<uuid:pk>/issues/create/", issue_create, name="issue-create"),
    path(
        "projects/<uuid:pk>/issues/<uuid:issue_pk>/resolve/",
        issue_resolve,
        name="issue-resolve",
    ),
    path("projects/<uuid:pk>/notes/create/", note_create, name="note-create"),
    path(
        "projects/<uuid:pk>/notes/<int:note_pk>/delete/",
        note_delete,
        name="note-delete",
    ),
    path("projects/<uuid:pk>/events/create/", event_create, name="event-create"),
    path(
        "projects/<uuid:pk>/events/<int:event_pk>/delete/",
        event_delete,
        name="event-delete",
    ),
    path(
        "projects/<uuid:pk>/references/create/",
        reference_create,
        name="reference-create",
    ),
    path(
        "projects/<uuid:pk>/references/<int:ref_pk>/delete/",
        reference_delete,
        name="reference-delete",
    ),
    path(
        "projects/<uuid:pk>/tasks/<uuid:task_pk>/",
        task_detail,
        name="task-detail",
    ),
    path(
        "projects/<uuid:pk>/tasks/<uuid:task_pk>/steps/<int:step_pk>/edit/",
        task_step_edit,
        name="task-step-edit",
    ),
    path(
        "projects/<uuid:pk>/tasks/<uuid:task_pk>/steps/<int:step_pk>/delete/",
        task_step_delete,
        name="task-step-delete",
    ),
    path(
        "projects/<uuid:pk>/issues/<uuid:issue_pk>/link-task/",
        issue_link_task,
        name="issue-link-task",
    ),
    path(
        "projects/<uuid:pk>/issues/<uuid:issue_pk>/unlink-task/<uuid:task_pk>/",
        issue_unlink_task,
        name="issue-unlink-task",
    ),
]
