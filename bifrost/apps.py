from django.apps import AppConfig


class BifrostConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "bifrost"
    verbose_name = "Bifröst"
    is_modular = True
    root_url = "/BIFROST"
    icon = "🌉"

    def get_dashboard_stats(self):
        from .models import Project, ProjectStatus, Task, TaskStatus

        total_projects = Project.objects.count()
        active_projects = Project.objects.filter(
            status=ProjectStatus.IN_PROGRESS
        ).count()
        pending_tasks = Task.objects.filter(status=TaskStatus.PENDING).count()
        incomplete_tasks = Task.objects.exclude(
            status__in=[TaskStatus.COMPLETED, TaskStatus.CANCELLED]
        ).count()

        return {
            "Total Projects": total_projects,
            "Active Projects": active_projects,
            "Pending Tasks": pending_tasks,
            "Incomplete Tasks": incomplete_tasks,
        }
