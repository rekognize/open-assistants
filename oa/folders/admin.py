from django.contrib import admin
from .models import Folder, FolderVectorStore, FolderFile, FolderSync


class FolderVectorStoreInline(admin.TabularInline):
    model = FolderVectorStore
    extra = 1


class FolderFileInline(admin.TabularInline):
    model = FolderFile
    extra = 1


class FolderSyncInline(admin.TabularInline):
    model = FolderSync
    extra = 1


@admin.register(Folder)
class FolderAdmin(admin.ModelAdmin):
    list_display = ('uuid', 'name', 'created_by', 'created_at', 'modified_at', 'public')
    search_fields = ('name', 'created_by__username')
    list_filter = ('public', 'created_at')
    inlines = [FolderVectorStoreInline, FolderFileInline, FolderSyncInline]


@admin.register(FolderVectorStore)
class FolderVectorStoreAdmin(admin.ModelAdmin):
    list_display = ('folder', 'vector_store_id')
    search_fields = ('folder__name', 'vector_store_id')


@admin.register(FolderFile)
class FolderFileAdmin(admin.ModelAdmin):
    list_display = ('folder', 'file_id')
    search_fields = ('folder__name', 'file_id')


@admin.register(FolderSync)
class FolderSyncAdmin(admin.ModelAdmin):
    list_display = ('folder', 'source', 'cron')
    search_fields = ('folder__name', 'source', 'cron')
