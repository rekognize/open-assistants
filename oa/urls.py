from django.contrib import admin
from django.urls import path
from oa.main import views as main_views

urlpatterns = [
    path('admin/', admin.site.urls),

    path('', main_views.HomeView.as_view(), name='home'),

    path('manage/', main_views.manage_assistants, name='manage_assistants'),

    path('projects/set/', main_views.set_project, name='set_project'),
    path('projects/create/', main_views.create_project, name='create_project'),
    path('projects/<int:project_id>/edit/', main_views.edit_project, name='edit_project'),
    path('projects/<int:project_id>/delete/', main_views.delete_project, name='delete_project'),
]
