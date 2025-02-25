import uuid
from django.db import models
from django.conf import settings


class FolderAssistant(models.Model):
    # M2M model to hold the Folder - Assistant relations
    folder = models.ForeignKey('Folder', on_delete=models.CASCADE)
    assistant_id = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.folder.name} - {self.assistant_id}"

    class Meta:
        unique_together = ('folder', 'assistant_id')


class Folder(models.Model):
    # Folders are M2M related to Assistants through Vector Stores
    uuid = models.UUIDField(default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, blank=True, null=True)

    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    projects = models.ManyToManyField('main.Project', blank=True)
    file_ids = models.JSONField(default=list, blank=True)

    modified_at = models.DateTimeField(auto_now=True)
    public = models.BooleanField(default=False)

    def __str__(self):
        return self.name or str(self.uuid)


class CloudStorage(models.Model):
    """
    Currently only S3 is supported
    """
    url = models.URLField()

    def sync_files(self):
        # Syncs the files of the folder with the remote folder
        if self.url:
            if self.url.startswith("s3://"):
                pass
