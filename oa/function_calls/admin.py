from django.contrib import admin
from .models import LocalAPIFunction, ExternalAPIFunction, Parameter


@admin.register(LocalAPIFunction)
class LocalAPIFunctionAdmin(admin.ModelAdmin):
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
