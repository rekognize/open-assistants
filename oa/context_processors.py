from django.conf import settings
from .main.models import Project


def user_projects(request):
    if request.user.is_anonymous:
        return {}

    if request.user.is_staff:
        projects = Project.objects.all()
    else:
        projects = Project.objects.filter(users=request.user)

    return {
        'user_projects': projects,
    }


def site_info(request):
    return {
        'SITE_NAME': settings.SITE_NAME,
    }
