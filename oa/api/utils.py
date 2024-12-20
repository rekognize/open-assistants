from typing import Any
from django.contrib.auth import aget_user
from openai import AsyncOpenAI
from oa.main.models import Project, SharedLink


class APIError(Exception):
    def __init__(self, message, status=500):
        self.message = message
        self.status = status
        super().__init__(self.message)


def serialize_to_dict(obj: Any) -> Any:
    """Recursively convert an object to a serializable dictionary."""
    if isinstance(obj, (str, int, float, bool, type(None))):
        return obj
    elif isinstance(obj, dict):
        return {k: serialize_to_dict(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [serialize_to_dict(v) for v in obj]
    elif hasattr(obj, "__dict__"):
        return {k: serialize_to_dict(v) for k, v in obj.__dict__.items() if not k.startswith('_')}
    elif hasattr(obj, "_asdict"):  # For named tuples and similar objects
        return serialize_to_dict(obj._asdict())
    else:
        raise TypeError(f"Type {type(obj)} not serializable")


async def aget_object_or_404(model, *args, **kwargs):
    try:
        return await model.objects.aget(*args, **kwargs)
    except model.DoesNotExist:
        raise APIError(f"{model._meta.object_name} not found")


async def aget_authenticated_user(request):
    user = await aget_user(request)
    if user.is_authenticated:
        return user
    else:
        return None


async def aget_user_project(user, project_id):
    if project_id:
        try:
            project = await aget_object_or_404(Project, id=int(project_id), user=user)
        except ValueError:
            raise APIError("Invalid project id.", status=400)
    else:
        project = await Project.objects.filter(user=user).afirst()
        if not project:
            raise APIError("No OpenAI key found.", status=404)
    return project


async def aget_openai_client(request):
    user = await aget_authenticated_user(request)
    if user:
        # User is authenticated
        project_id = request.session.get('selected_project_id')

        # Fetch the project using the project_id
        project = await aget_user_project(user, project_id)

        return AsyncOpenAI(api_key=project.key)
    else:
        # User is anonymous, check for token
        token = request.headers.get('X-Token') or request.GET.get('token')
        if token:
            try:
                shared_link = await SharedLink.objects.select_related('project').aget(token=token)
                project = shared_link.project
                return AsyncOpenAI(api_key=project.key)
            except SharedLink.DoesNotExist:
                raise APIError("Invalid token.", status=403)
        else:
            raise APIError("Authentication required.", status=401)
