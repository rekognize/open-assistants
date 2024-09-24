from django.contrib import admin
from .models import Project, Thread


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ['name', 'user', 'key']
    readonly_fields = ('list_threads',)

    def list_threads(self, obj):
        threads = obj.threads.all()
        return ", ".join([thread.openai_id or str(thread.uuid) for thread in threads])
    list_threads.short_description = 'Threads'


@admin.register(Thread)
class ThreadAdmin(admin.ModelAdmin):
    list_display = ('uuid', 'openai_id', 'created_at', 'project')
    search_fields = ('uuid', 'openai_id', 'created_at', 'project__name', 'project__key')
    readonly_fields = ('openai_id', 'uuid')
    list_filter = ['project']
