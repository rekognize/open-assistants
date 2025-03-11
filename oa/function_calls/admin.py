from django.contrib import admin
from django.db.models import JSONField
from django_json_widget.widgets import JSONEditorWidget
from .models import LocalAPIFunction, ExternalAPIFunction, CodeInterpreterScript, FunctionExecution


@admin.register(CodeInterpreterScript)
class CodeInterpreterScriptAdmin(admin.ModelAdmin):
    list_display = (
        "assistant_id",
        "thread_id",
        "run_id",
        "run_step_id",
        "tool_call_id",
        "snippet_index",
        "created_at",
    )
    list_filter = ("created_at",)
    search_fields = (
        "assistant_id",
        "thread_id",
        "run_id",
        "run_step_id",
        "tool_call_id",
        "code",
    )
    ordering = ("-created_at",)


@admin.register(LocalAPIFunction)
class LocalAPIFunctionAdmin(admin.ModelAdmin):
    list_display = ("name", "display_assistant_ids", "created_at")
    list_filter = ("created_at",)
    search_fields = ("name", "description")
    ordering = ("-created_at",)
    readonly_fields = ("created_at",)

    formfield_overrides = {
        JSONField: {'widget': JSONEditorWidget},
    }

    def display_assistant_ids(self, obj):
        if obj.assistant_ids:
            return ", ".join(obj.assistant_ids)
        return "-"
    display_assistant_ids.short_description = "Assistant IDs"


@admin.register(ExternalAPIFunction)
class ExternalAPIFunctionAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')
    search_fields = ('name', 'description')

    formfield_overrides = {
        JSONField: {'widget': JSONEditorWidget},
    }

@admin.register(FunctionExecution)
class FunctionExecutionAdmin(admin.ModelAdmin):
    list_display = ('function', 'thread', 'time', 'status_code', 'executed_version')
    list_filter = ('status_code', 'time')
    search_fields = ('function__name', 'thread__openai_id', 'error_message')
    ordering = ('-time',)
