from django.contrib import admin
from .models import Project, Thread, SharedLink


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ['name', 'user', 'key', 'is_oa_project']
    readonly_fields = ('list_threads',)

    def list_threads(self, obj):
        threads = obj.threads.all()
        return ", ".join([thread.openai_id or str(thread.uuid) for thread in threads])
    list_threads.short_description = 'Threads'


@admin.register(Thread)
class ThreadAdmin(admin.ModelAdmin):
    list_display = ('uuid', 'openai_id', 'created_at')
    search_fields = ('uuid', 'openai_id', 'created_at')


@admin.register(SharedLink)
class SharedLinkAdmin(admin.ModelAdmin):
    list_display = ('assistant_id', 'name', 'token', 'created', 'project')
    search_fields = ('assistant_id', 'name', 'token', 'created', 'project__name', 'project__key')
    readonly_fields = ('token', 'created')
    list_filter = ['project']
