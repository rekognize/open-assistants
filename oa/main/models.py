import uuid
from django.db import models
from django.contrib.auth.models import User


class Project(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='projects')
    key = models.CharField(max_length=255)
    name = models.CharField(max_length=100, blank=True, null=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['user', 'key'], name='unique_key_per_user')
        ]

    def __str__(self):
        return self.name or self.get_partial_key()

    def get_partial_key(self):
        if self.key:
            return f"{self.key[:8]}...{self.key[-5:]}"
        return None


class Thread(models.Model):
    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, db_index=True)
    openai_id = models.CharField(max_length=100, blank=True, null=True, db_index=True)
    created_at = models.DateTimeField(blank=True, null=True, db_index=True)
    metadata = models.JSONField(blank=True, null=True)

    def __str__(self):
        return self.openai_id or str(self.uuid)


class SharedLink(models.Model):
    assistant_id = models.CharField(max_length=100)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='shared_links')
    token = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    created = models.DateTimeField(auto_now_add=True)
    name = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        return f"Shared link for {self.assistant_id}"
