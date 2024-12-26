from django.contrib import admin
from django.contrib.auth.views import LogoutView
from django.urls import path

from oa.api.views import api
from oa.main import views as main_views


urlpatterns = [
    path('oaAdmin/', admin.site.urls),

    path('login/', main_views.login_view, name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),

    path("api/", api.urls),

    path('', main_views.HomeView.as_view(), name='home'),

    # path('manage/', main_views.manage_assistants, name='manage_assistants'),
    path('<uuid:project_uuid>/manage/', main_views.manage_assistants, name='manage_assistants'),

    # path('chat/', main_views.thread_detail, name='thread_detail'),
    path('<uuid:project_uuid>/chat/', main_views.thread_detail, name='thread_detail'),

    path('<uuid:project_uuid>/analytics/', main_views.analytics, name='analytics'),
    path('analytics/thread_data/', main_views.get_assistant_threads, name='get_assistant_threads'),

    path('db_threads/', main_views.create_db_thread, name='create_db_thread'),
    path('db_threads/list/', main_views.list_threads, name='list_threads'),

    path('files/image/<str:file_id>/', main_views.serve_image_file, name='serve_image_file'),

    path('projects/set/', main_views.set_project, name='set_project'),
    path('projects/create/', main_views.create_project, name='create_project'),
    path('projects/<int:project_id>/edit/', main_views.edit_project, name='edit_project'),
    path('projects/<int:project_id>/delete/', main_views.delete_project, name='delete_project'),

    path('a/share/<str:assistant_id>/', main_views.share_assistant, name='share_assistant'),
    path('a/share/delete/<uuid:link_token>/', main_views.delete_shared_link, name='delete_shared_link'),
    path('a/share/update/<uuid:link_token>/', main_views.update_shared_link, name='update_shared_link'),
    path('shared/<uuid:shared_token>/', main_views.shared_thread_detail, name='shared_thread_detail'),

    path('wizard/generate-instructions/', main_views.generate_instructions_view, name='generate_instructions'),
]

admin.site.index_title = 'Open Assistants'
admin.site.site_header = 'Open Assistants'
admin.site.site_title = 'Open Assistants'
