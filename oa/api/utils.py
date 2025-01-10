from typing import Any
from django.contrib.auth import aget_user
from django.urls import reverse
from openai import AsyncOpenAI, AsyncAssistantEventHandler
from openai.types.beta.threads import Text, TextDelta, ImageFile
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


class EventHandler(AsyncAssistantEventHandler):
    def __init__(self, shared_data):
        super().__init__()
        self.current_message = ""
        self.shared_data = shared_data  # Use shared_data instead of response_data
        self.stream_done = False
        self.current_annotations = []

    async def on_message_created(self, message):
        self.current_message = ""
        self.current_annotations = []
        self.shared_data.append({"type": "message_created"})

    async def on_text_delta(self, delta: TextDelta, snapshot: Text):
        if delta.value:
            self.current_message += delta.value

        # Collect annotations from the snapshot
        self.current_annotations = []
        if snapshot.annotations:
            for annotation in snapshot.annotations:
                annotation_dict = annotation.to_dict()

                if hasattr(annotation, 'file_citation') and annotation.file_citation:
                    # Manually construct the file_citation dictionary
                    annotation_dict['file_citation'] = {
                        'file_id': annotation.file_citation.file_id,
                        'filename': 'Unknown File'  # Placeholder
                    }

                self.current_annotations.append(annotation_dict)

        # Send the updated message and annotations to the client
        self.shared_data.append({
            "type": "text_delta",
            "text": self.current_message,
            "annotations": self.current_annotations
        })

    async def on_message_done(self, message):
        # Send the final message content and annotations to the client
        self.shared_data.append({
            "type": "message_done",
            "text": self.current_message,
            "annotations": self.current_annotations
        })

    async def on_image_file_done(self, image_file: ImageFile) -> None:
        image_url = reverse('api-1.0.0:serve_image_file', kwargs={
            'file_id': image_file.file_id
        })

        self.current_message += f'<p><img src="{image_url}" style="max-width: 100%;"></p>'

        # No annotations for images
        self.shared_data.append({
            "type": "image_file",
            "text": self.current_message,
            "annotations": []
        })

    async def on_end(self):
        self.stream_done = True
        self.shared_data.append({"type": "end_of_stream"})
