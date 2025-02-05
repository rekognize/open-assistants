from django.contrib import admin
from django.db.models import JSONField
from django_json_widget.widgets import JSONEditorWidget
from .models import LocalAPIFunction, ExternalAPIFunction, CodeInterpreterScript, FunctionExecution


@admin.register(CodeInterpreterScript)
class CodeInterpreterScriptAdmin(admin.ModelAdmin):
    list_display = (
        "project",
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

@admin.register(FunctionExecution)
class FunctionExecutionAdmin(admin.ModelAdmin):
    list_display = ('function', 'time', 'status_code')
    list_filter = ('status_code', 'time')
    search_fields = ('function__name', 'error_message')
    ordering = ('-time',)
