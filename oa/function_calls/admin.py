from django.contrib import admin
from .models import (
    CodeInterpreterScript,
    LocalFunction,
    ExternalAPIFunction,
    Parameter,
)


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


@admin.register(LocalFunction)
class LocalFunctionAdmin(admin.ModelAdmin):
    list_display = ("name", "project", "assistant_id", "created_at")
    list_filter = ("project", "assistant_id", "created_at")
    search_fields = ("name", "assistant_id", "description")
    ordering = ("-created_at",)
    readonly_fields = ("created_at",)


class ParameterInline(admin.TabularInline):
    model = Parameter
    extra = 1  # Number of empty forms displayed


@admin.register(ExternalAPIFunction)
class ExternalAPIFunctionAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')
    search_fields = ('name', 'description')
    inlines = [ParameterInline]


@admin.register(Parameter)
class ParameterAdmin(admin.ModelAdmin):
    list_display = ('function', 'name', 'type', 'description', 'required')
    list_filter = ('function', 'type', 'required')
    search_fields = ('name', 'description')
