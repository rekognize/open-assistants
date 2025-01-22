from django.contrib import admin
from .models import Function, Parameter


class ParameterInline(admin.TabularInline):
    model = Parameter
    extra = 1  # Number of empty forms displayed


@admin.register(Function)
class FunctionAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')
    search_fields = ('name', 'description')
    inlines = [ParameterInline]


@admin.register(Parameter)
class ParameterAdmin(admin.ModelAdmin):
    list_display = ('function', 'name', 'type', 'description', 'required')
    list_filter = ('function', 'type', 'required')
    search_fields = ('name', 'description')
