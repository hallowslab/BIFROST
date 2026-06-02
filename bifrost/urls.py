from django.urls import path

from . import views

app_name = "bifrost"

urlpatterns = [
    # Project list (home)
    path("", views.project_list, name="project-list"),

    # Project CRUD
    path("projects/create/", views.project_create, name="project-create"),
    path("projects/<uuid:pk>/", views.project_detail, name="project-detail"),
    path("projects/<uuid:pk>/edit/", views.project_edit, name="project-edit"),
    path("projects/<uuid:pk>/transfer/", views.project_transfer, name="project-transfer"),

    # Tasks
    path("projects/<uuid:pk>/tasks/create/", views.task_create, name="task-create"),
    path(
        "projects/<uuid:pk>/tasks/<uuid:task_pk>/edit/",
        views.task_edit,
        name="task-edit",
    ),
    path(
        "projects/<uuid:pk>/tasks/<uuid:task_pk>/complete/",
        views.task_complete,
        name="task-complete",
    ),
    path(
        "projects/<uuid:pk>/tasks/<uuid:task_pk>/delete/",
        views.task_delete,
        name="task-delete",
    ),

    # Notes
    path("projects/<uuid:pk>/notes/create/", views.note_create, name="note-create"),
    path(
        "projects/<uuid:pk>/notes/<int:note_pk>/delete/",
        views.note_delete,
        name="note-delete",
    ),

    # Events (manual)
    path("projects/<uuid:pk>/events/create/", views.event_create, name="event-create"),
    path(
        "projects/<uuid:pk>/events/<int:event_pk>/delete/",
        views.event_delete,
        name="event-delete",
    ),

    # References
    path(
        "projects/<uuid:pk>/references/create/",
        views.reference_create,
        name="reference-create",
    ),
    path(
        "projects/<uuid:pk>/references/<int:ref_pk>/delete/",
        views.reference_delete,
        name="reference-delete",
    ),
]
