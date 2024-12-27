import uuid
from django.db import models
from django.contrib.auth.models import User


class Project(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False)
    openai_id = models.CharField(max_length=100, blank=True, null=True, db_index=True)
    key = models.CharField(max_length=255)
    name = models.CharField(max_length=100, blank=True, null=True)
    users = models.ManyToManyField(User, blank=True)

    def __str__(self):
        return self.name or self.get_partial_key()

    def get_partial_key(self):
        if self.key:
            return f"{self.key[:8]}...{self.key[-5:]}"
        return None


class Thread(models.Model):
    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    openai_id = models.CharField(max_length=100, blank=True, null=True, db_index=True)
    created_at = models.DateTimeField(blank=True, null=True, db_index=True)
    metadata = models.JSONField(blank=True, null=True)
    shared_link = models.ForeignKey(
        'SharedLink',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='threads'
    )

    def __str__(self):
        return self.openai_id or str(self.uuid)

    class Meta:
        indexes = [
            models.Index(fields=["openai_id"], name="openai_id_idx"),
            models.Index(fields=["created_at"], name="created_at_idx"),
        ]


class SharedLink(models.Model):
    assistant_id = models.CharField(max_length=100)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='shared_links')
    token = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    created = models.DateTimeField(auto_now_add=True)
    name = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        return f"Shared link for {self.assistant_id}"
