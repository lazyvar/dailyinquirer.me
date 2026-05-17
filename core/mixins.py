from django.db import models


class TimestampedModel(models.Model):
    """Abstract base that gives a model self-maintaining timestamps.

    ``created_at`` is set once when the row is first inserted and
    ``updated_at`` is refreshed on every save. Both are required.
    """

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
