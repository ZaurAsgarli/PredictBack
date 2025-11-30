# Make celery import optional to allow Django to run without celery installed
try:
    from .celery import app as celery_app
    __all__ = ('celery_app',)
except ImportError:
    # Celery not installed or not needed for basic operation
    pass

