from django.apps import AppConfig


class ScraperConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'scraper'
    def ready(self):
        try:
            from . import utils  # noqa: F401
        except Exception:
            pass