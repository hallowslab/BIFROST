from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect, render

from .. import permissions
from .. import services
from ..forms.runtime import (
    EventForm,
    IssueForm,
    IssueLinkTaskForm,
    NoteForm,
    ProjectEditForm,
    ProjectFilterForm,
    ProjectForm,
    ProjectTransferForm,
    ReferenceForm,
    ResolutionForm,
    TaskForm,
    TaskStepForm,
)
from ..models.runtime import (
    Event,
    Issue,
    Note,
    Project,
    ProjectStatus,
    Reference,
    Task,
    TaskStep,
)


@login_required
def project_list(request: HttpRequest) -> HttpResponse:
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
            if d.get("project_template"):
                project.project_template = d["project_template"]
                project.save(update_fields=["project_template"])
            messages.success(request, f'Project "{project.name}" created.')
            return redirect("bifrost:project-detail", pk=project.pk)
    else:
        form = ProjectForm(initial={"owner": request.user})

    return render(request, "bifrost/project_form.html", {"form": form, "action": "Create"})


@login_required
def project_detail(request: HttpRequest, pk) -> HttpResponse:
    project = get_object_or_404(permissions.visible_projects_for(request.user), pk=pk)
    if not permissions.can_view_project(request.user, project):
        messages.error(request, "You do not have permission to view this project.")
        return redirect("bifrost:project-list")

    tasks = project.tasks.select_related("assigned_to").order_by("-created_at")
    issues = project.issues.select_related("identified_by").prefetch_related(
        "resolutions__steps"
    ).order_by("-created_at")
    notes = project.notes.select_related("author").order_by("-created_at")
    events = project.events.select_related("actor", "assigned_to").order_by("-created_at")
    references = project.references.order_by("reference_type", "value")

    return render(
        request,
        "bifrost/project_detail.html",
        {
            "project": project,
            "tasks": tasks,
            "issues": issues,
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


@login_required
def task_create(request: HttpRequest, pk) -> HttpResponse | HttpResponseRedirect:
    project = get_object_or_404(Project, pk=pk)
    if not permissions.can_manage_project(request.user, project):
        messages.error(request, "You do not have permission to add tasks to this project.")
        return redirect("bifrost:project-detail", pk=project.pk)

    if request.method == "POST":
        form = TaskForm(request.POST)
        if form.is_valid():
            d = form.cleaned_data
            task = services.create_task(
                project=project,
                title=d["title"],
                actor=request.user,
                description=d.get("description") or None,
                status=d.get("status"),
                assigned_to=d.get("assigned_to"),
            )
            if d.get("task_template"):
                task.task_template = d["task_template"]
                task.save(update_fields=["task_template"])
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


@login_required
def issue_create(request: HttpRequest, pk) -> HttpResponse | HttpResponseRedirect:
    project = get_object_or_404(Project, pk=pk)
    if not permissions.can_manage_project(request.user, project):
        messages.error(request, "You do not have permission to add issues to this project.")
        return redirect("bifrost:project-detail", pk=project.pk)

    if request.method == "POST":
        form = IssueForm(request.POST)
        if form.is_valid():
            d = form.cleaned_data
            issue = services.create_issue(
                project=project,
                title=d["title"],
                identified_by=d.get("identified_by") or request.user,
                description=d.get("description") or None,
                status=d.get("status"),
            )
            if d.get("issue_template"):
                issue.issue_template = d["issue_template"]
                issue.save(update_fields=["issue_template"])
            messages.success(request, f'Issue "{d["title"]}" identified.')
            return redirect("bifrost:project-detail", pk=project.pk)
    else:
        form = IssueForm(initial={"identified_by": request.user})

    return render(
        request,
        "bifrost/issue_form.html",
        {"form": form, "project": project, "action": "Identify Issue"},
    )


@login_required
def issue_resolve(
    request: HttpRequest, pk, issue_pk
) -> HttpResponse | HttpResponseRedirect:
    project = get_object_or_404(Project, pk=pk)
    issue = get_object_or_404(Issue, pk=issue_pk, project=project)

    if not permissions.can_manage_project(request.user, project):
        messages.error(request, "You do not have permission to resolve issues.")
        return redirect("bifrost:project-detail", pk=project.pk)

    if request.method == "POST":
        form = ResolutionForm(request.POST)
        if form.is_valid():
            services.create_resolution(
                issue=issue,
                description=form.cleaned_data["description"],
                created_by=request.user,
            )
            messages.success(request, f'Issue "{issue.title}" resolved.')
            return redirect("bifrost:project-detail", pk=project.pk)
    else:
        form = ResolutionForm()

    return render(
        request,
        "bifrost/issue_resolve_form.html",
        {"form": form, "project": project, "issue": issue},
    )


@login_required
def note_create(request: HttpRequest, pk) -> HttpResponse | HttpResponseRedirect:
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


@login_required
def event_create(request: HttpRequest, pk) -> HttpResponse | HttpResponseRedirect:
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


@login_required
def reference_create(request: HttpRequest, pk) -> HttpResponse | HttpResponseRedirect:
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


@login_required
def task_delete(request: HttpRequest, pk, task_pk) -> HttpResponseRedirect:
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


@login_required
def task_detail(request: HttpRequest, pk, task_pk) -> HttpResponse | HttpResponseRedirect:
    project = get_object_or_404(permissions.visible_projects_for(request.user), pk=pk)
    task = get_object_or_404(Task, pk=task_pk, project=project)
    steps = task.steps.order_by("order")

    if request.method == "POST":
        form = TaskStepForm(request.POST)
        if form.is_valid():
            step = form.save(commit=False)
            step.task = task
            step.save()
            messages.success(request, "Step added.")
            return redirect("bifrost:task-detail", pk=project.pk, task_pk=task.pk)
    else:
        form = TaskStepForm()

    return render(
        request,
        "bifrost/task_detail.html",
        {
            "project": project,
            "task": task,
            "steps": steps,
            "form": form,
            "can_edit": permissions.can_edit_task(request.user, task),
        },
    )


@login_required
def task_step_edit(
    request: HttpRequest, pk, task_pk, step_pk
) -> HttpResponse | HttpResponseRedirect:
    project = get_object_or_404(permissions.visible_projects_for(request.user), pk=pk)
    task = get_object_or_404(Task, pk=task_pk, project=project)
    step = get_object_or_404(TaskStep, pk=step_pk, task=task)

    if not permissions.can_edit_task(request.user, task):
        messages.error(request, "You do not have permission to edit this task.")
        return redirect("bifrost:task-detail", pk=project.pk, task_pk=task.pk)

    if request.method == "POST":
        form = TaskStepForm(request.POST, instance=step)
        if form.is_valid():
            form.save()
            messages.success(request, "Step updated.")
            return redirect("bifrost:task-detail", pk=project.pk, task_pk=task.pk)
    else:
        form = TaskStepForm(instance=step)

    return render(
        request,
        "bifrost/task_step_form.html",
        {"form": form, "project": project, "task": task, "step": step},
    )


@login_required
def task_step_delete(
    request: HttpRequest, pk, task_pk, step_pk
) -> HttpResponseRedirect:
    if request.method != "POST":
        return redirect("bifrost:task-detail", pk=pk, task_pk=task_pk)

    project = get_object_or_404(permissions.visible_projects_for(request.user), pk=pk)
    task = get_object_or_404(Task, pk=task_pk, project=project)
    step = get_object_or_404(TaskStep, pk=step_pk, task=task)

    if not permissions.can_edit_task(request.user, task):
        messages.error(request, "You do not have permission to edit this task.")
        return redirect("bifrost:task-detail", pk=project.pk, task_pk=task.pk)

    step.delete()
    messages.success(request, "Step deleted.")
    return redirect("bifrost:task-detail", pk=project.pk, task_pk=task.pk)


@login_required
def issue_link_task(
    request: HttpRequest, pk, issue_pk
) -> HttpResponse | HttpResponseRedirect:
    project = get_object_or_404(Project, pk=pk)
    issue = get_object_or_404(Issue, pk=issue_pk, project=project)

    if not permissions.can_manage_project(request.user, project):
        messages.error(request, "You do not have permission to link tasks.")
        return redirect("bifrost:project-detail", pk=project.pk)

    if request.method == "POST":
        form = IssueLinkTaskForm(request.POST, project=project)
        if form.is_valid():
            task = form.cleaned_data["task"]
            issue.tasks.add(task)
            messages.success(request, f'Task "{task.title}" linked to issue.')
    return redirect("bifrost:project-detail", pk=project.pk)


@login_required
def issue_unlink_task(
    request: HttpRequest, pk, issue_pk, task_pk
) -> HttpResponseRedirect:
    if request.method != "POST":
        return redirect("bifrost:project-detail", pk=pk)

    project = get_object_or_404(Project, pk=pk)
    issue = get_object_or_404(Issue, pk=issue_pk, project=project)
    task = get_object_or_404(Task, pk=task_pk, project=project)

    if not permissions.can_manage_project(request.user, project):
        messages.error(request, "You do not have permission to unlink tasks.")
        return redirect("bifrost:project-detail", pk=project.pk)

    issue.tasks.remove(task)
    messages.success(request, f'Task "{task.title}" unlinked from issue.')
    return redirect("bifrost:project-detail", pk=project.pk)
