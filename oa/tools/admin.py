from django.contrib import admin
from .models import Tool, Parameter


class ParameterInline(admin.TabularInline):
    model = Parameter
    extra = 1  # Number of empty forms displayed


@admin.register(Tool)
class ToolAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')
    search_fields = ('name', 'description')
    inlines = [ParameterInline]


@admin.register(Parameter)
class ParameterAdmin(admin.ModelAdmin):
    list_display = ('tool', 'name', 'type', 'description', 'required')
    list_filter = ('tool', 'type', 'required')
    search_fields = ('name', 'description')
