from django.contrib import admin
from django.contrib.auth.views import LogoutView
from django.conf import settings
from django.urls import path

from .api.views import api
from .function_calls.api import api as function_calls_api
from .folders.api import api as folders_api

from .main import views as main_views


urlpatterns = [
    path('aiAdmin/', admin.site.urls),

    path('login/', main_views.login_view, name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),

    path("api/", api.urls),
    path("api/functions/", function_calls_api.urls),
    path("api/folders/", folders_api.urls),

    path('', main_views.HomeView.as_view(), name='home'),

    path('<uuid:project_uuid>/', main_views.HomeView.as_view(), name='home'),

    path('<uuid:project_uuid>/manage/', main_views.manage_overview, name='manage_overview'),
    path('<uuid:project_uuid>/manage/assistants', main_views.manage_assistants, name='manage_assistants'),
    path('<uuid:project_uuid>/manage/tools', main_views.manage_tools, name='manage_tools'),

    path('<uuid:project_uuid>/analytics/', main_views.analytics, name='analytics'),
    path('<uuid:project_uuid>/tools/', main_views.tools, name='tools'),

    path('<uuid:project_uuid>/chat/', main_views.thread_detail, name='thread_detail'),

    path('shared/<uuid:shared_token>/', main_views.shared_thread_detail, name='shared_thread_detail'),

    path('db_threads/', main_views.create_db_thread, name='create_db_thread'),
]

admin.site.index_title = settings.SITE_NAME
admin.site.site_header = settings.SITE_NAME
admin.site.site_title = settings.SITE_NAME
