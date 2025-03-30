from django.contrib import admin
from .models import Folder, FolderAssistant


class FolderAssistantInline(admin.TabularInline):
    model = FolderAssistant
    extra = 1


@admin.register(Folder)
class FolderAdmin(admin.ModelAdmin):
    list_display = ('uuid', 'name', 'created_by', 'created_at', 'modified_at', 'public')
    search_fields = ('name', 'created_by__username')
    list_filter = ('public', 'created_at')
    inlines = [FolderAssistantInline]


@admin.register(FolderAssistant)
class FolderAssistantAdmin(admin.ModelAdmin):
    list_display = ('folder', 'assistant_id')
    search_fields = ('folder__name', 'assistant_id')
