import uuid
from django.db import models
from django.conf import settings


class FolderVectorStore(models.Model):
    # M2M model to hold the Folder - Vector Store relations
    folder = models.ForeignKey('Folder', on_delete=models.CASCADE)
    vector_store_id = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.folder.name} - {self.vector_store_id}"


class Folder(models.Model):
    # Folders are M2M related to Assistants through Vector Stores
    uuid = models.UUIDField(default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    project = models.ForeignKey('main.Project', blank=True, null=True, on_delete=models.CASCADE)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
    public = models.BooleanField(default=False)
    sync_source = models.URLField(blank=True, null=True)

    def __str__(self):
        return self.name

    def sync(self):
        if self.sync_source:
            if self.source.startswith("s3://"):
                pass


class FolderFile(models.Model):
    # M2M model to hold the Folder - File relations
    folder = models.ForeignKey('Folder', on_delete=models.CASCADE)
    file_id = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.folder.name} - {self.file_id}"
