from .settings import *  # noqa: F403


ALLOWED_HOSTS = ["testserver", "localhost", "127.0.0.1"]  # noqa: F405
DATABASES = {  # noqa: F405
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}
