from django.apps import AppConfig


class AuthServiceConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "auth_service"

    def ready(self) -> None:  # pragma: no cover - import side effect
        from . import db  # noqa: WPS433

        db.init_mongo()
