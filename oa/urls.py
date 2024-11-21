from django.contrib import admin
from django.urls import path
from oa.api.views import api
from oa.main import views as main_views

urlpatterns = [
    path('admin/', admin.site.urls),

    path("api/", api.urls),

    path('', main_views.HomeView.as_view(), name='home'),

    path('manage/', main_views.manage_assistants, name='manage_assistants'),

    path('chat/', main_views.thread_detail, name='thread_detail'),
    path('chat/<str:assistant_id>/stream/<str:thread_id>/', main_views.create_stream_url, name='create_stream_url'),
    path('chat/<str:assistant_id>/stream/<str:thread_id>/responses/', main_views.stream_responses, name='stream_responses'),

    path('t/<str:thread_id>/messages/', main_views.get_messages, name='get_messages'),
    path('t/<str:thread_id>/files/', main_views.get_thread_files, name='get_thread_files'),
    path('t/<str:thread_id>/download/<str:file_id>/', main_views.DownloadFileView.as_view(), name='download_file'),
    path('files/<str:file_id>/', main_views.serve_image_file, name='serve_image_file'),

    path('projects/set/', main_views.set_project, name='set_project'),
    path('projects/create/', main_views.create_project, name='create_project'),
    path('projects/<int:project_id>/edit/', main_views.edit_project, name='edit_project'),
    path('projects/<int:project_id>/delete/', main_views.delete_project, name='delete_project'),

    path('a/share/<str:assistant_id>/', main_views.share_assistant, name='share_assistant'),
    path('a/share/delete/<uuid:link_token>/', main_views.delete_shared_link, name='delete_shared_link'),
    path('shared/<uuid:token>/', main_views.shared_thread_detail, name='shared_thread_detail'),
]

admin.site.index_title = 'Open Assistants'
admin.site.site_header = 'Open Assistants'
admin.site.site_title = 'Open Assistants'
