from datetime import datetime

from django.contrib.auth import get_user
from openai import OpenAI
from oa.api.utils import APIError
from oa.main.models import Project


def format_time(timestamp):
    return datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')


def get_object_or_404_sync(model, *args, **kwargs):
    try:
        return model.objects.get(*args, **kwargs)
    except model.DoesNotExist:
        raise APIError(f"{model._meta.object_name} not found")


def get_authenticated_user_sync(request):
    user = get_user(request)
    if not user.is_authenticated:
        raise APIError("The user is not authenticated.", status=401)
    return user


def get_user_project_sync(user, project_id):
    if project_id:
        try:
            project = get_object_or_404_sync(Project, id=int(project_id), user=user)
        except ValueError:
            raise APIError("Invalid project id.", status=400)
    else:
        project = Project.objects.filter(user=user).first()
        if not project:
            raise APIError("No OpenAI key found.", status=404)
    return project


def get_openai_client_sync(request):
    user = get_authenticated_user_sync(request)

    project_id = request.session.get('selected_project_id')

    project = get_user_project_sync(user, project_id)

    return OpenAI(api_key=project.key)
