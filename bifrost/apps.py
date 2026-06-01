from django.apps import AppConfig
from django.utils.safestring import mark_safe


class BifrostConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'bifrost'
    verbose_name = "Bifröst"
    is_modular = True
    root_url = "/BIFROST"
    icon = "🌉"

    def get_dashboard_stats(self):
        stats = {
            "prop1": 100,
            "prop2": "String",
            "prop4": True,
        }

        return stats
    
