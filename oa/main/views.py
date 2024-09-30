import asyncio
import base64
import json
import time

from django.db import IntegrityError
from django.http import JsonResponse, StreamingHttpResponse
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404
from django.urls import reverse
from django.views.generic import TemplateView
from openai import AssistantEventHandler, AsyncOpenAI
from openai.types.beta.threads import Text, TextDelta, ImageFile

from .models import Project
from .utils import get_openai_client_sync
from ..api.utils import APIError


class HomeView(TemplateView):
    template_name = 'home.html'


@login_required
def manage_assistants(request):
    return render(request, "manage.html")


# Chat

class EventHandler(AssistantEventHandler):
    def __init__(self):
        super().__init__()
        self.current_message = ""
        self.response_data = []
        self.stream_done = False

    def on_text_created(self, text: Text) -> None:
        self.response_data.append({"type": "text_created", "text": self.current_message})

    def on_text_delta(self, delta: TextDelta, snapshot: Text):
        if delta.value:
            self.current_message += delta.value
        self.response_data.append({"type": "text_delta", "text": self.current_message})

    def on_image_file_done(self, image_file: ImageFile) -> None:
        image_data = asyncio.run(fetch_image_file(image_file.file_id))
        if image_data:
            self.current_message += f'<p><img src="{image_data}" style="max-width: 100%;"></p>'
        self.response_data.append({
            "type": "image_file",
            "image_data": image_data
        })

    def on_end(self):
        self.stream_done = True
        self.response_data.append({"type": "end_of_stream"})

    def stream_response(self):
        while True:
            if self.response_data:
                data = self.response_data.pop(0)
                yield f"data: {json.dumps(data)}\n\n"
                if data.get("type") == "end_of_stream":
                    break
            time.sleep(0.1)


def thread_detail(request):
    # Get assistant
    return render(request, "chat/chat.html", {
        'assistant_id': request.GET.get('a')
    })


def create_stream_url(request, thread_id, assistant_id):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid request method'}, status=400)

    # Generate the URL for 'stream_responses'
    stream_path = reverse('stream_responses', kwargs={
        'assistant_id': assistant_id,
        'thread_id': thread_id
    })
    stream_url = request.build_absolute_uri(stream_path)

    return JsonResponse({'success': True, 'stream_url': stream_url})


def stream_responses(request, thread_id, assistant_id):
    try:
        event_handler = EventHandler()
        create_run(request, thread_id, assistant_id, event_handler)
        response = StreamingHttpResponse(event_handler.stream_response(), content_type='text/event-stream')
        response['Cache-Control'] = 'no-cache'
        response['X-Accel-Buffering'] = 'no'  # For Nginx
        return response

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


def create_run(request, thread_id, assistant_id, event_handler):
    try:
        client = get_openai_client_sync(request)
    except APIError as e:
        return JsonResponse({"error": e.message}, status=e.status)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

    try:
        with client.beta.threads.runs.stream(
            thread_id=thread_id,
            assistant_id=assistant_id,
            event_handler=event_handler,
        ) as stream:
            stream.until_done()

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse({"status": "success", "message": "Run created successfully"}, status=200)


async def fetch_image_file(file_id):
    async with AsyncOpenAI() as client:
        content_response = await client.files.content(file_id)

        # Read the binary content from the response
        image_binary = content_response.read()

        # Convert the binary content to a base64 encoded string
        image_base64 = base64.b64encode(image_binary).decode('utf-8')

        # Create a data URL
        image_data_url = f"data:image/png;base64,{image_base64}"

        return image_data_url


# Projects

@login_required
def set_project(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            project_id = data.get('project_id')

            if project_id:
                # Set the selected project ID in the session
                request.session['selected_project_id'] = project_id
                return JsonResponse({'status': 'success'}, status=200)
            else:
                return JsonResponse({'error': 'Invalid project ID'}, status=400)
        except ValueError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)
    return JsonResponse({'error': 'Bad Request'}, status=400)


@login_required
def create_project(request):
    if request.method == "POST":
        name = request.POST.get('name')
        key = request.POST.get('key')

        if not name:
            return JsonResponse({'success': False, 'error': 'Name is required.'})
        if not key:
            return JsonResponse({'success': False, 'error': 'Key is required.'})

        try:
            project = Project.objects.create(user=request.user, name=name, key=key)
            return JsonResponse({
                'success': True,
                'project': {
                    'id': project.id,
                    'name': project.name,
                    'partial_key': project.get_partial_key()
                }
            })
        except IntegrityError:
            return JsonResponse({'success': False, 'error': 'The key provided is already in use. Please enter a different key.'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})

    return JsonResponse({'success': False, 'error': 'Invalid request method.'})


@login_required
def edit_project(request, project_id):
    if request.method == "POST":
        name = request.POST.get('name')
        key = request.POST.get('key')

        if not name:
            return JsonResponse({'success': False, 'error': 'Name is required.'})

        try:
            project = get_object_or_404(Project, id=project_id, user=request.user)

            # Update the name
            project.name = name

            # Update the key only if it is provided
            if key:
                project.key = key

            project.save()

            return JsonResponse({
                'success': True,
                'project': {
                    'id': project.id,
                    'name': project.name,
                    'partial_key': project.get_partial_key()
                }
            })
        except IntegrityError:
            return JsonResponse({'success': False, 'error': 'The key provided is already in use. Please enter a different key.'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})

    return JsonResponse({'success': False, 'error': 'Invalid request method.'})


@login_required
def delete_project(request, project_id):
    if request.method == "POST":
        try:
            project = get_object_or_404(Project, id=project_id, user=request.user)
            project.delete()
            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})

    return JsonResponse({'success': False, 'error': 'Invalid request method.'})
