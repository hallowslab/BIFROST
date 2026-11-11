from django import forms
from django.contrib.auth.models import User

from ..models.knowledge import IssueTemplate, ProjectTemplate, TaskTemplate
from ..models.runtime import (
    Event,
    EventType,
    Issue,
    IssueStatus,
    Note,
    Project,
    ProjectStatus,
    Reference,
    Resolution,
    Task,
    TaskStep,
    TaskStatus,
)


class ProjectForm(forms.ModelForm):
    project_template = forms.ModelChoiceField(
        queryset=ProjectTemplate.objects.order_by("name"),
        required=False,
        label="From Template",
        help_text="Optional: link this project to a template.",
        widget=forms.Select(attrs={"class": "select is-fullwidth"}),
    )

    class Meta:
        model = Project
        fields = [
            "name",
            "project_type",
            "project_type_custom",
            "status",
            "owner",
            "description",
        ]
        widgets = {
            "name": forms.TextInput(attrs={"placeholder": "Project name"}),
            "project_type_custom": forms.TextInput(
                attrs={"placeholder": "Custom type (optional)"}
            ),
            "description": forms.Textarea(attrs={"rows": 4}),
        }
        help_texts = {
            "project_type_custom": "Only used when no catalogue entry matches.",
        }


class ProjectEditForm(forms.ModelForm):
    class Meta:
        model = Project
        fields = [
            "name",
            "project_type",
            "project_type_custom",
            "status",
            "description",
        ]
        widgets = {
            "name": forms.TextInput(attrs={"placeholder": "Project name"}),
            "project_type_custom": forms.TextInput(
                attrs={"placeholder": "Custom type (optional)"}
            ),
            "description": forms.Textarea(attrs={"rows": 4}),
        }


class ProjectTransferForm(forms.Form):
    owner = forms.ModelChoiceField(
        queryset=User.objects.order_by("username"),
        label="New owner",
    )


class ProjectFilterForm(forms.Form):
    q = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={"placeholder": "Search projects\u2026"}),
        label="Search",
    )
    status = forms.ChoiceField(
        required=False,
        choices=[("", "All statuses")] + ProjectStatus.choices,
        label="Status",
    )


class TaskForm(forms.ModelForm):
    task_template = forms.ModelChoiceField(
        queryset=TaskTemplate.objects.select_related("project_template").order_by("title"),
        required=False,
        label="From Template",
        help_text="Optional: link this task to a template.",
        widget=forms.Select(attrs={"class": "select is-fullwidth"}),
    )

    class Meta:
        model = Task
        fields = ["title", "description", "status", "assigned_to"]
        widgets = {
            "title": forms.TextInput(attrs={"placeholder": "Task title"}),
            "description": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.instance.pk:
            self.fields["status"].choices = [
                (TaskStatus.PENDING, "Pending"),
                (TaskStatus.IN_PROGRESS, "In Progress"),
            ]


class IssueForm(forms.ModelForm):
    issue_template = forms.ModelChoiceField(
        queryset=IssueTemplate.objects.order_by("title"),
        required=False,
        label="From Template",
        help_text="Optional: link this issue to a template.",
        widget=forms.Select(attrs={"class": "select is-fullwidth"}),
    )

    class Meta:
        model = Issue
        fields = ["title", "description", "status", "identified_by"]
        widgets = {
            "title": forms.TextInput(attrs={"placeholder": "Issue title"}),
            "description": forms.Textarea(attrs={"rows": 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.instance.pk:
            self.fields["status"].choices = [
                (IssueStatus.IDENTIFIED, "Identified"),
                (IssueStatus.INVESTIGATING, "Investigating"),
            ]


class ResolutionForm(forms.ModelForm):
    class Meta:
        model = Resolution
        fields = ["description"]
        widgets = {
            "description": forms.Textarea(
                attrs={"rows": 4, "placeholder": "Describe the resolution..."}
            ),
        }


class NoteForm(forms.ModelForm):
    class Meta:
        model = Note
        fields = ["title", "content"]
        widgets = {
            "title": forms.TextInput(attrs={"placeholder": "Note title"}),
            "content": forms.Textarea(attrs={"rows": 6}),
        }


class EventForm(forms.ModelForm):
    class Meta:
        model = Event
        fields = ["event_type", "title", "description", "assigned_to"]
        widgets = {
            "title": forms.TextInput(attrs={"placeholder": "Event title"}),
            "description": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        excluded = {
            EventType.PROJECT_CREATED,
            EventType.PROJECT_COMPLETED,
            EventType.PROJECT_TRANSFERRED,
            EventType.TASK_COMPLETED,
            EventType.STATUS_CHANGED,
            EventType.NOTE_ADDED,
        }
        self.fields["event_type"].choices = [
            (v, label)
            for v, label in EventType.choices
            if v not in excluded
        ]


class TaskStepForm(forms.ModelForm):
    class Meta:
        model = TaskStep
        fields = ["order", "description", "completed"]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 2}),
        }


class IssueLinkTaskForm(forms.Form):
    task = forms.ModelChoiceField(
        queryset=Task.objects.none(),
        label="Task",
    )

    def __init__(self, *args, **kwargs):
        project = kwargs.pop("project", None)
        super().__init__(*args, **kwargs)
        if project:
            self.fields["task"].queryset = Task.objects.filter(project=project).order_by("title")


class ReferenceForm(forms.ModelForm):
    class Meta:
        model = Reference
        fields = ["reference_type", "value"]
        widgets = {
            "value": forms.TextInput(attrs={"placeholder": "Reference value or URL"}),
        }
