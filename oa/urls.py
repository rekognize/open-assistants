from django.contrib import admin
from django.contrib.auth.views import LogoutView
from django.conf import settings
from django.urls import path

from .api.views import api
from .main import views as main_views


urlpatterns = [
    path('aiAdmin/', admin.site.urls),

    path('login/', main_views.login_view, name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),

    path("api/", api.urls),

    path('', main_views.HomeView.as_view(), name='home'),
    path('<uuid:project_uuid>/', main_views.HomeView.as_view(), name='home'),

    # path('manage/', main_views.manage_assistants, name='manage_assistants'),
    path('<uuid:project_uuid>/manage/', main_views.manage_assistants, name='manage_assistants'),

    # path('chat/', main_views.thread_detail, name='thread_detail'),
    path('<uuid:project_uuid>/chat/', main_views.thread_detail, name='thread_detail'),

    path('<uuid:project_uuid>/analytics/', main_views.analytics, name='analytics'),
    path('analytics/thread_data/', main_views.get_assistant_threads, name='get_assistant_threads'),

    path('db_threads/', main_views.create_db_thread, name='create_db_thread'),
    path('db_threads/list/', main_views.list_threads, name='list_threads'),

    path('files/image/<str:file_id>/', main_views.serve_image_file, name='serve_image_file'),

    path('shared/<uuid:shared_token>/', main_views.shared_thread_detail, name='shared_thread_detail'),
]

admin.site.index_title = settings.SITE_NAME
admin.site.site_header = settings.SITE_NAME
admin.site.site_title = settings.SITE_NAME
