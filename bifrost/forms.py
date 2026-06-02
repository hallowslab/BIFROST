from django import forms
from django.contrib.auth.models import User

from .models import (
    Event,
    EventType,
    Note,
    Project,
    ProjectStatus,
    Reference,
    Task,
    TaskStatus,
)


class ProjectForm(forms.ModelForm):
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
    """Lighter form used on the edit page — excludes owner."""

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


class TaskForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = ["title", "description", "status", "assigned_to"]
        widgets = {
            "title": forms.TextInput(attrs={"placeholder": "Task title"}),
            "description": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Hide COMPLETED and CANCELLED from creation form
        if not self.instance.pk:
            self.fields["status"].choices = [
                (TaskStatus.PENDING, "Pending"),
                (TaskStatus.IN_PROGRESS, "In Progress"),
            ]


class NoteForm(forms.ModelForm):
    class Meta:
        model = Note
        fields = ["title", "content"]
        widgets = {
            "title": forms.TextInput(attrs={"placeholder": "Note title"}),
            "content": forms.Textarea(attrs={"rows": 6}),
        }


class EventForm(forms.ModelForm):
    """Manually-created events (auto-events come from services)."""

    class Meta:
        model = Event
        fields = ["event_type", "title", "description", "assigned_to"]
        widgets = {
            "title": forms.TextInput(attrs={"placeholder": "Event title"}),
            "description": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Auto-events should not be manually created via the UI
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


class ReferenceForm(forms.ModelForm):
    class Meta:
        model = Reference
        fields = ["reference_type", "value"]
        widgets = {
            "value": forms.TextInput(attrs={"placeholder": "Reference value or URL"}),
        }


class ProjectFilterForm(forms.Form):
    """Search/filter form for the project list."""

    q = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={"placeholder": "Search projects…"}),
        label="Search",
    )
    status = forms.ChoiceField(
        required=False,
        choices=[("", "All statuses")] + ProjectStatus.choices,
        label="Status",
    )
