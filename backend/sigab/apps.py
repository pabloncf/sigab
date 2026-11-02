from django.apps import AppConfig


class SigabConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "sigab"

    def ready(self):
        from . import authentication  # noqa: F401  (registers login signal receivers)
