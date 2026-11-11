from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from ..models import EventType, IssueStatus, TaskStatus
from .. import services


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
        response = self.client.get(
            reverse("bifrost:project-detail", args=[self.visible_project.pk])
        )
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
            self.project.events.filter(
                event_type=EventType.PROJECT_TRANSFERRED
            ).exists()
        )


class IssueServiceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="pass")
        self.project = services.create_project(
            name="Project with Issues",
            owner=self.user,
        )

    def test_create_issue(self):
        issue = services.create_issue(
            project=self.project,
            title="Test Issue",
            identified_by=self.user,
            description="Something broke",
        )
        self.assertEqual(issue.title, "Test Issue")
        self.assertEqual(issue.status, IssueStatus.IDENTIFIED)
        self.assertTrue(
            self.project.events.filter(
                event_type=EventType.ISSUE_IDENTIFIED
            ).exists()
        )

    def test_create_resolution_updates_status_and_creates_events(self):
        issue = services.create_issue(
            project=self.project,
            title="Fixable Issue",
            identified_by=self.user,
        )
        resolution = services.create_resolution(
            issue=issue,
            description="Fixed it",
            created_by=self.user,
        )
        issue.refresh_from_db()
        self.assertEqual(issue.status, IssueStatus.RESOLVED)
        self.assertEqual(resolution.issue_id, issue.id)
        self.assertTrue(
            self.project.events.filter(
                event_type=EventType.ISSUE_RESOLVED
            ).exists()
        )
        self.assertTrue(
            self.project.events.filter(
                event_type=EventType.RESOLUTION_APPLIED
            ).exists()
        )

    def test_multiple_resolutions_per_issue(self):
        issue = services.create_issue(
            project=self.project,
            title="Multi-resolve Issue",
            identified_by=self.user,
        )
        r1 = services.create_resolution(issue=issue, description="First try", created_by=self.user)
        r2 = services.create_resolution(issue=issue, description="Second try", created_by=self.user)
        self.assertEqual(issue.resolutions.count(), 2)
        self.assertEqual(r1.issue_id, issue.id)
        self.assertEqual(r2.issue_id, issue.id)


class BridgePromotionTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username="admin", password="pass", is_staff=True, is_superuser=True
        )
        self.project = services.create_project(
            name="Promotable Project",
            owner=self.admin,
        )
        self.task = services.create_task(
            project=self.project,
            title="Promotable Task",
            actor=self.admin,
        )

    def test_promote_task_to_template(self):
        template = services.promote_task_to_template(task=self.task, admin=self.admin)
        self.assertEqual(template.title, "Promotable Task")
        self.assertTrue(
            self.project.project_template.task_templates.filter(
                pk=template.pk
            ).exists()
        )

    def test_promote_project_to_template(self):
        template = services.promote_project_to_template(
            project=self.project, admin=self.admin
        )
        self.assertEqual(template.name, "Promotable Project")
        self.assertEqual(template.task_templates.count(), 1)

    def test_promote_issue_to_template(self):
        issue = services.create_issue(
            project=self.project,
            title="Promotable Issue",
            identified_by=self.admin,
        )
        template = services.promote_issue_to_template(issue=issue, admin=self.admin)
        self.assertEqual(template.title, "Promotable Issue")
