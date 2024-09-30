from django.contrib import admin
from django.urls import path, include
from django.urls import path

from oa.api.views import api
from oa.main import views as main_views


urlpatterns = [
    path('accounts/', include('accounts.urls', namespace='accounts')),

    path('admin/', admin.site.urls),

    path("api/", api.urls),

    path('', main_views.HomeView.as_view(), name='home'),

    path('manage/', main_views.manage_assistants, name='manage_assistants'),

    path('chat/', main_views.thread_detail, name='thread_detail'),
    path('chat/<str:assistant_id>/stream/<str:thread_id>/', main_views.create_stream_url, name='create_stream_url'),
    path('chat/<str:assistant_id>/stream/<str:thread_id>/responses/', main_views.stream_responses, name='stream_responses'),

    path('projects/set/', main_views.set_project, name='set_project'),
    path('projects/create/', main_views.create_project, name='create_project'),
    path('projects/<int:project_id>/edit/', main_views.edit_project, name='edit_project'),
    path('projects/<int:project_id>/delete/', main_views.delete_project, name='delete_project'),
]
