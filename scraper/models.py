from django.db import models
from django.utils import timezone

class QueryCache(models.Model):
    query = models.CharField(max_length=255, unique=True)
    results_json = models.JSONField()
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.query} @ {self.created_at}"
