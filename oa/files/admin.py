from django.contrib import admin
from .models import Folder, FolderProject, S3Folder, File


@admin.register(Folder)
class FolderAdmin(admin.ModelAdmin):
    list_display = ("uuid", "name", "owner", "created_at")
    search_fields = ("uuid", "name")
    list_filter = ("created_at",)


@admin.register(FolderProject)
class FolderProjectAdmin(admin.ModelAdmin):
    list_display = ("folder", "project")
    search_fields = ("folder__name", "project__name")


@admin.register(S3Folder)
class S3FolderAdmin(admin.ModelAdmin):
    list_display = ("uuid", "name", "owner", "s3_bucket", "s3_key_prefix", "created_at")
    search_fields = ("uuid", "name", "s3_bucket")
    list_filter = ("created_at",)


@admin.register(File)
class FileAdmin(admin.ModelAdmin):
    list_display = ("uuid", "name", "status", "created_at")
    search_fields = ("uuid", "name")
    list_filter = ("status", "created_at")
