from django.contrib import admin
from django.db.models import JSONField
from django_json_widget.widgets import JSONEditorWidget
from .models import LocalAPIFunction, ExternalAPIFunction


@admin.register(LocalAPIFunction)
class LocalAPIFunctionAdmin(admin.ModelAdmin):
    list_display = ("name", "project", "assistant_id", "created_at")
    list_filter = ("project", "assistant_id", "created_at")
    search_fields = ("name", "assistant_id", "description")
    ordering = ("-created_at",)
    readonly_fields = ("created_at",)

    formfield_overrides = {
        JSONField: {'widget': JSONEditorWidget},
    }


@admin.register(ExternalAPIFunction)
class ExternalAPIFunctionAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')
    search_fields = ('name', 'description')

    formfield_overrides = {
        JSONField: {'widget': JSONEditorWidget},
    }

