import uuid
from django.db import models
from django.contrib.auth.models import User
from ..main.models import Project


class AbstractFolder(models.Model):
    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    owner = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="%(class)s_folders"
    )

    class Meta:
        abstract = True

    def __str__(self):
        return self.name or str(self.uuid)

    def add_to_vector_store(self):
        raise NotImplementedError(
            "Subclasses of AbstractFolder must implement add_to_vector_store()."
        )

    def sync_to_openai(self):
        raise NotImplementedError(
            "Subclasses of AbstractFolder must implement sync_to_openai()."
        )


class Folder(AbstractFolder):
    projects = models.ManyToManyField(
        Project,
        through='FolderProject',
        related_name='folders'
    )
    parent_folder = models.ForeignKey(
        'self', on_delete=models.SET_NULL, null=True, blank=True, related_name='subfolders'
    )
    files = models.ManyToManyField('File', blank=True, related_name='folders')

    def add_to_vector_store(self):
        pass

    def sync_to_openai(self):
        pass


class FolderProject(models.Model):
    folder = models.ForeignKey(Folder, on_delete=models.CASCADE)
    project = models.ForeignKey(Project, on_delete=models.CASCADE)

    class Meta:
        unique_together = ('folder', 'project')


class S3Folder(AbstractFolder):
    """
    A folder representing an S3 location.
    """
    s3_bucket = models.CharField(max_length=255)
    s3_key_prefix = models.CharField(max_length=255, blank=True, null=True)
    files = models.ManyToManyField('File', blank=True, related_name='s3_folders')

    def add_to_vector_store(self):
        pass

    def sync_to_openai(self):
        pass


class File(models.Model):
    class Status(models.TextChoices):
        NOT_SYNCED = 'not_synced', 'Not Synced'
        SYNCED = 'synced', 'Synced'
        DELETED = 'deleted', 'Deleted'

    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(blank=True, null=True, db_index=True)

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.NOT_SYNCED,
    )
    openai_id = models.CharField(max_length=100, blank=True, null=True, db_index=True)

    def __str__(self):
        return self.name or str(self.uuid)

    def is_synced(self):
        return self.status == self.Status.SYNCED
