from django.contrib import admin
from .models import Project, Thread, SharedLink


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ['name', 'user', 'key', 'is_oa_project']
    readonly_fields = ('list_shared_links',)

    def list_shared_links(self, obj):
        shared_links = obj.shared_links.all()
        return ", ".join([f"{link.name} ({link.token})" for link in shared_links])
    list_shared_links.short_description = 'Shared Links'


@admin.register(Thread)
class ThreadAdmin(admin.ModelAdmin):
    list_display = ('uuid', 'openai_id', 'created_at', 'shared_link_display')
    search_fields = ('uuid', 'openai_id', 'created_at', 'shared_link__name', 'shared_link__token')

    def shared_link_display(self, obj):
        if obj.shared_link:
            return f"{obj.shared_link.name} ({obj.shared_link.token})"
        return "-"
    shared_link_display.short_description = 'Shared Link'

@admin.register(SharedLink)
class SharedLinkAdmin(admin.ModelAdmin):
    list_display = ('assistant_id', 'name', 'token', 'created', 'project')
    search_fields = ('assistant_id', 'name', 'token', 'created', 'project__name', 'project__key')
    readonly_fields = ('token', 'created')
    list_filter = ['project']
