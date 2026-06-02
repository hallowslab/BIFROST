from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect, render

from .forms import (
    EventForm,
    NoteForm,
    ProjectEditForm,
    ProjectFilterForm,
    ProjectForm,
    ProjectTransferForm,
    ReferenceForm,
    TaskForm,
)
from .models import Project, ProjectStatus, Task, Note, Event, Reference
from . import services
from . import permissions


# ---------------------------------------------------------------------------
# Project views
# ---------------------------------------------------------------------------


@login_required
def project_list(request: HttpRequest) -> HttpResponse:
    """List all projects, with search and status filter."""
    form = ProjectFilterForm(request.GET)
    projects = permissions.visible_projects_for(request.user)

    if form.is_valid():
        q = form.cleaned_data.get("q", "").strip()
        status = form.cleaned_data.get("status", "").strip()
        if q:
            projects = projects.filter(name__icontains=q)
        if status:
            projects = projects.filter(status=status)

    projects = projects.order_by("-created_at")

    page_number = request.GET.get("page", 1)
    paginator = Paginator(projects, 15)
    page_obj = paginator.get_page(page_number)

    return render(
        request,
        "bifrost/project_list.html",
        {
            "page_obj": page_obj,
            "filter_form": form,
            "status_choices": ProjectStatus.choices,
        },
    )


@login_required
def project_create(request: HttpRequest) -> HttpResponse | HttpResponseRedirect:
    """Create a new project via service layer."""
    if request.method == "POST":
        form = ProjectForm(request.POST)
        if form.is_valid():
            d = form.cleaned_data
            project = services.create_project(
                name=d["name"],
                owner=d["owner"],
                project_type=d.get("project_type"),
                project_type_custom=d.get("project_type_custom") or None,
                status=d.get("status", ProjectStatus.DRAFT),
                description=d.get("description") or None,
            )
            messages.success(request, f'Project "{project.name}" created.')
            return redirect("bifrost:project-detail", pk=project.pk)
    else:
        # Pre-fill owner with current user
        form = ProjectForm(initial={"owner": request.user})

    return render(request, "bifrost/project_form.html", {"form": form, "action": "Create"})


@login_required
def project_detail(request: HttpRequest, pk) -> HttpResponse:
    """Show a project and all its tasks, notes, events, and references."""
    project = get_object_or_404(permissions.visible_projects_for(request.user), pk=pk)
    if not permissions.can_view_project(request.user, project):
        messages.error(request, "You do not have permission to view this project.")
        return redirect("bifrost:project-list")

    tasks = project.tasks.select_related("assigned_to").order_by("-created_at")
    notes = project.notes.select_related("author").order_by("-created_at")
    events = project.events.select_related("actor", "assigned_to").order_by("-created_at")
    references = project.references.order_by("reference_type", "value")

    return render(
        request,
        "bifrost/project_detail.html",
        {
            "project": project,
            "tasks": tasks,
            "notes": notes,
            "events": events,
            "references": references,
            "can_manage_project": permissions.can_manage_project(request.user, project),
            "can_transfer_project": permissions.can_manage_project(request.user, project),
            "transfer_form": ProjectTransferForm(initial={"owner": project.owner}),
        },
    )


@login_required
def project_edit(request: HttpRequest, pk) -> HttpResponse | HttpResponseRedirect:
    """Edit a project's details. Status changes go through the service layer."""
    project = get_object_or_404(Project, pk=pk)
    if not permissions.can_manage_project(request.user, project):
        messages.error(request, "You do not have permission to edit this project.")
        return redirect("bifrost:project-detail", pk=project.pk)

    if request.method == "POST":
        form = ProjectEditForm(request.POST, instance=project)
        if form.is_valid():
            d = form.cleaned_data
            services.update_project(
                project=project,
                actor=request.user,
                name=d.get("name"),
                project_type=d.get("project_type"),
                project_type_custom=d.get("project_type_custom") or None,
                status=d.get("status"),
                description=d.get("description") or None,
            )
            messages.success(request, "Project updated.")
            return redirect("bifrost:project-detail", pk=project.pk)
    else:
        form = ProjectEditForm(instance=project)

    return render(
        request,
        "bifrost/project_form.html",
        {"form": form, "project": project, "action": "Edit"},
    )


@login_required
def project_transfer(request: HttpRequest, pk) -> HttpResponseRedirect:
    """Transfer project ownership to another user."""
    if request.method != "POST":
        return redirect("bifrost:project-detail", pk=pk)

    project = get_object_or_404(Project, pk=pk)
    if not permissions.can_manage_project(request.user, project):
        messages.error(request, "You do not have permission to transfer this project.")
        return redirect("bifrost:project-detail", pk=project.pk)

    form = ProjectTransferForm(request.POST)
    if not form.is_valid():
        messages.error(request, "Choose a valid new owner.")
        return redirect("bifrost:project-detail", pk=project.pk)

    new_owner = form.cleaned_data["owner"]
    services.transfer_project(project=project, new_owner=new_owner, actor=request.user)
    messages.success(request, f'Project transferred to {new_owner.get_full_name() or new_owner.username}.')
    return redirect("bifrost:project-list")


# ---------------------------------------------------------------------------
# Task views
# ---------------------------------------------------------------------------


@login_required
def task_create(request: HttpRequest, pk) -> HttpResponse | HttpResponseRedirect:
    """Create a task for a project."""
    project = get_object_or_404(Project, pk=pk)
    if not permissions.can_manage_project(request.user, project):
        messages.error(request, "You do not have permission to add tasks to this project.")
        return redirect("bifrost:project-detail", pk=project.pk)

    if request.method == "POST":
        form = TaskForm(request.POST)
        if form.is_valid():
            d = form.cleaned_data
            services.create_task(
                project=project,
                title=d["title"],
                actor=request.user,
                description=d.get("description") or None,
                status=d.get("status"),
                assigned_to=d.get("assigned_to"),
            )
            messages.success(request, f'Task "{d["title"]}" created.')
            return redirect("bifrost:project-detail", pk=project.pk)
    else:
        form = TaskForm()

    return render(
        request,
        "bifrost/task_form.html",
        {"form": form, "project": project, "action": "Add Task"},
    )


@login_required
def task_edit(request: HttpRequest, pk, task_pk) -> HttpResponse | HttpResponseRedirect:
    """Edit an existing task."""
    project = get_object_or_404(permissions.visible_projects_for(request.user), pk=pk)
    task = get_object_or_404(Task, pk=task_pk, project=project)

    if not permissions.can_edit_task(request.user, task):
        messages.error(request, "You do not have permission to edit this task.")
        return redirect("bifrost:project-detail", pk=project.pk)

    if request.method == "POST":
        form = TaskForm(request.POST, instance=task)
        if form.is_valid():
            d = form.cleaned_data
            services.update_task(
                task=task,
                actor=request.user,
                title=d.get("title"),
                description=d.get("description") or None,
                status=d.get("status"),
                assigned_to=d.get("assigned_to"),
            )
            messages.success(request, "Task updated.")
            return redirect("bifrost:project-detail", pk=project.pk)
    else:
        form = TaskForm(instance=task)

    return render(
        request,
        "bifrost/task_form.html",
        {"form": form, "project": project, "task": task, "action": "Edit Task"},
    )


@login_required
def task_complete(
    request: HttpRequest, pk, task_pk
) -> HttpResponseRedirect:
    """Mark a task as completed (POST only)."""
    if request.method != "POST":
        return redirect("bifrost:project-detail", pk=pk)

    project = get_object_or_404(permissions.visible_projects_for(request.user), pk=pk)
    task = get_object_or_404(Task, pk=task_pk, project=project)

    if not permissions.can_edit_task(request.user, task):
        messages.error(request, "You do not have permission to complete this task.")
        return redirect("bifrost:project-detail", pk=project.pk)

    services.complete_task(task=task, actor=request.user)
    messages.success(request, f'Task "{task.title}" marked as completed.')
    return redirect("bifrost:project-detail", pk=project.pk)


# ---------------------------------------------------------------------------
# Note views
# ---------------------------------------------------------------------------


@login_required
def note_create(request: HttpRequest, pk) -> HttpResponse | HttpResponseRedirect:
    """Add a note to a project."""
    project = get_object_or_404(Project, pk=pk)
    if project.owner != request.user and not request.user.is_superuser:
        messages.error(request, "You do not have permission to add notes to this project.")
        return redirect("bifrost:project-detail", pk=project.pk)

    if request.method == "POST":
        form = NoteForm(request.POST)
        if form.is_valid():
            d = form.cleaned_data
            services.create_note(
                project=project,
                title=d["title"],
                content=d["content"],
                author=request.user,
            )
            messages.success(request, f'Note "{d["title"]}" added.')
            return redirect("bifrost:project-detail", pk=project.pk)
    else:
        form = NoteForm()

    return render(
        request,
        "bifrost/note_form.html",
        {"form": form, "project": project},
    )


# ---------------------------------------------------------------------------
# Event views
# ---------------------------------------------------------------------------


@login_required
def event_create(request: HttpRequest, pk) -> HttpResponse | HttpResponseRedirect:
    """Manually create an event for a project."""
    project = get_object_or_404(Project, pk=pk)
    if not request.user.is_superuser:
        messages.error(request, "Only admins can manually log timeline events.")
        return redirect("bifrost:project-detail", pk=project.pk)

    if request.method == "POST":
        form = EventForm(request.POST)
        if form.is_valid():
            d = form.cleaned_data
            services.create_event(
                project=project,
                event_type=d["event_type"],
                title=d["title"],
                actor=request.user,
                description=d.get("description") or None,
                assigned_to=d.get("assigned_to"),
            )
            messages.success(request, "Event recorded.")
            return redirect("bifrost:project-detail", pk=project.pk)
    else:
        form = EventForm()

    return render(
        request,
        "bifrost/event_form.html",
        {"form": form, "project": project},
    )


# ---------------------------------------------------------------------------
# Reference views
# ---------------------------------------------------------------------------


@login_required
def reference_create(request: HttpRequest, pk) -> HttpResponse | HttpResponseRedirect:
    """Add an external reference to a project."""
    project = get_object_or_404(Project, pk=pk)
    if project.owner != request.user and not request.user.is_superuser:
        messages.error(
            request, "You do not have permission to add references to this project."
        )
        return redirect("bifrost:project-detail", pk=project.pk)

    if request.method == "POST":
        form = ReferenceForm(request.POST)
        if form.is_valid():
            d = form.cleaned_data
            services.create_reference(
                project=project,
                reference_type=d["reference_type"],
                value=d["value"],
                actor=request.user,
            )
            messages.success(request, "Reference added.")
            return redirect("bifrost:project-detail", pk=project.pk)
    else:
        form = ReferenceForm()

    return render(
        request,
        "bifrost/reference_form.html",
        {"form": form, "project": project},
    )


# ---------------------------------------------------------------------------
# Deletion views
# ---------------------------------------------------------------------------


@login_required
def task_delete(request: HttpRequest, pk, task_pk) -> HttpResponseRedirect:
    """Delete an existing task."""
    if request.method != "POST":
        return redirect("bifrost:project-detail", pk=pk)

    project = get_object_or_404(Project, pk=pk)
    task = get_object_or_404(Task, pk=task_pk, project=project)

    if project.owner != request.user and not request.user.is_superuser:
        messages.error(request, "You do not have permission to delete this task.")
        return redirect("bifrost:project-detail", pk=project.pk)

    services.delete_task(task=task, actor=request.user)
    messages.success(request, f'Task "{task.title}" deleted.')
    return redirect("bifrost:project-detail", pk=project.pk)


@login_required
def note_delete(request: HttpRequest, pk, note_pk) -> HttpResponseRedirect:
    """Delete an existing note."""
    if request.method != "POST":
        return redirect("bifrost:project-detail", pk=pk)

    project = get_object_or_404(Project, pk=pk)
    note = get_object_or_404(Note, pk=note_pk, project=project)

    if project.owner != request.user and not request.user.is_superuser:
        messages.error(request, "You do not have permission to delete this note.")
        return redirect("bifrost:project-detail", pk=project.pk)

    services.delete_note(note=note, actor=request.user)
    messages.success(request, "Note deleted.")
    return redirect("bifrost:project-detail", pk=project.pk)


@login_required
def reference_delete(request: HttpRequest, pk, ref_pk) -> HttpResponseRedirect:
    """Delete an existing reference."""
    if request.method != "POST":
        return redirect("bifrost:project-detail", pk=pk)

    project = get_object_or_404(Project, pk=pk)
    ref = get_object_or_404(Reference, pk=ref_pk, project=project)

    if project.owner != request.user and not request.user.is_superuser:
        messages.error(request, "You do not have permission to delete this reference.")
        return redirect("bifrost:project-detail", pk=project.pk)

    services.delete_reference(reference=ref, actor=request.user)
    messages.success(request, "Reference deleted.")
    return redirect("bifrost:project-detail", pk=project.pk)


@login_required
def event_delete(request: HttpRequest, pk, event_pk) -> HttpResponseRedirect:
    """Delete an existing timeline event (admin only)."""
    if request.method != "POST":
        return redirect("bifrost:project-detail", pk=pk)

    project = get_object_or_404(Project, pk=pk)
    event = get_object_or_404(Event, pk=event_pk, project=project)

    if not request.user.is_superuser:
        messages.error(request, "Only admins can delete timeline events.")
        return redirect("bifrost:project-detail", pk=project.pk)

    services.delete_event(event=event)
    messages.success(request, "Event deleted.")
    return redirect("bifrost:project-detail", pk=project.pk)
