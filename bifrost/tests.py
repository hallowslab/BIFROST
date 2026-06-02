from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .models import EventType, TaskStatus
from . import services


class CollaborationVisibilityTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username="owner", password="pass")
        self.collaborator = User.objects.create_user(username="collab", password="pass")
        self.other = User.objects.create_user(username="other", password="pass")

        self.visible_project = services.create_project(
            name="Visible Project",
            owner=self.owner,
        )
        self.visible_task = services.create_task(
            project=self.visible_project,
            title="Collaborator task",
            actor=self.owner,
            assigned_to=self.collaborator,
        )

        self.hidden_project = services.create_project(
            name="Hidden Project",
            owner=self.other,
        )

    def test_project_list_shows_projects_with_assigned_tasks(self):
        self.client.force_login(self.collaborator)

        response = self.client.get(reverse("bifrost:project-list"))

        self.assertContains(response, "Visible Project")
        self.assertNotContains(response, "Hidden Project")

    def test_assigned_user_can_open_project_detail(self):
        self.client.force_login(self.collaborator)

        response = self.client.get(reverse("bifrost:project-detail", args=[self.visible_project.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Visible Project")

    def test_assigned_user_can_complete_their_task(self):
        self.client.force_login(self.collaborator)

        response = self.client.post(
            reverse(
                "bifrost:task-complete",
                args=[self.visible_project.pk, self.visible_task.pk],
            )
        )

        self.assertEqual(response.status_code, 302)
        self.visible_task.refresh_from_db()
        self.assertEqual(self.visible_task.status, TaskStatus.COMPLETED)
        self.assertIsNotNone(self.visible_task.completed_at)


class ProjectTransferTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username="owner", password="pass")
        self.new_owner = User.objects.create_user(username="newowner", password="pass")
        self.project = services.create_project(
            name="Transferable Project",
            owner=self.owner,
        )

    def test_owner_can_transfer_project(self):
        self.client.force_login(self.owner)

        response = self.client.post(
            reverse("bifrost:project-transfer", args=[self.project.pk]),
            {"owner": self.new_owner.pk},
        )

        self.assertEqual(response.status_code, 302)
        self.project.refresh_from_db()
        self.assertEqual(self.project.owner, self.new_owner)
        self.assertTrue(
            self.project.events.filter(event_type=EventType.PROJECT_TRANSFERRED).exists()
        )
