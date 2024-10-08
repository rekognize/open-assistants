import asyncio
import base64
import json
import logging
import os

from django.db import IntegrityError
from django.http import JsonResponse, StreamingHttpResponse, HttpResponse, Http404, HttpResponseNotFound
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404
from django.urls import reverse
from django.views import View
from django.views.generic import TemplateView
from openai import AssistantEventHandler, OpenAIError
from openai.types.beta.threads import Text, TextDelta, ImageFile

from .models import Project
from .utils import get_openai_client_sync, format_time
from ..api.utils import APIError, get_openai_client


logger = logging.getLogger(__name__)


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
        self.current_annotations = []

    def on_message_created(self, message):
        print("on_message_created called")
        self.current_message = ""
        self.current_annotations = []
        self.response_data.append({"type": "message_created"})

    def on_text_delta(self, delta: TextDelta, snapshot: Text):
        print(f"on_text_delta called with delta: {delta.value}")

        if delta.value:
            self.current_message += delta.value

        # Collect annotations from the snapshot
        self.current_annotations = []
        if snapshot.annotations:
            print(f"Annotations found: {snapshot.annotations}")
            for annotation in snapshot.annotations:
                annotation_dict = annotation.to_dict()

                if hasattr(annotation, 'file_citation') and annotation.file_citation:
                    # Don't have access to the client, use a placeholder
                    annotation_dict['file_citation']['filename'] = 'Unknown File'  # Placeholder

                self.current_annotations.append(annotation_dict)

        # Send the updated message and annotations to the client
        self.response_data.append({
            "type": "text_delta",
            "text": self.current_message,
            "annotations": self.current_annotations
        })

    def on_message_done(self, message):
        print("on_message_done called")
        # Send the final message content and annotations to the client
        self.response_data.append({
            "type": "message_done",
            "text": self.current_message,
            "annotations": self.current_annotations
        })

    def on_image_file_done(self, image_file: ImageFile) -> None:
        print(f"on_image_file_done called with file_id: {image_file.file_id}")
        image_url = reverse('serve_image_file', args=[image_file.file_id])
        self.current_message += f'<p><img src="{image_url}" style="max-width: 100%;"></p>'

        # No annotations for images
        self.response_data.append({
            "type": "image_file",
            "text": self.current_message,
            "annotations": []
        })

    def on_end(self):
        print("on_end called")
        self.stream_done = True
        self.response_data.append({"type": "end_of_stream"})


def serve_image_file(request, file_id):
    try:
        client = get_openai_client_sync(request)
    except APIError as e:
        return JsonResponse({"error": e.message}, status=e.status)

    try:
        content_response = client.files.content(file_id)
        image_binary = content_response.read()
        return HttpResponse(image_binary, content_type='image/png')
    except OpenAIError as e:
        logger.error(f"Error fetching image file: {e}")
        return HttpResponseNotFound('Image not found')


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
        client = get_openai_client_sync(request)
    except APIError as e:
        return JsonResponse({"error": e.message}, status=e.status)

    def event_stream():
        event_handler = EventHandler()
        try:
            with client.beta.threads.runs.stream(
                thread_id=thread_id,
                assistant_id=assistant_id,
                event_handler=event_handler,
            ) as stream:
                # Process events as they arrive
                for event in stream:
                    # The event handler methods are called automatically
                    # Retrieve and yield data as it becomes available
                    while event_handler.response_data:
                        data = event_handler.response_data.pop(0)
                        print(f"Streaming data: {data}")
                        yield f"data: {json.dumps(data)}\n\n"
                        # Check for end of stream
                        if data.get("type") == "end_of_stream":
                            return  # Exit the generator to end streaming

                # After the stream ends, process any remaining response_data
                while event_handler.response_data:
                    data = event_handler.response_data.pop(0)
                    print(f"Streaming data after stream ends: {data}")
                    yield f"data: {json.dumps(data)}\n\n"
                    if data.get("type") == "end_of_stream":
                        return  # Exit the generator to end streaming

        except Exception as e:
            # Yield an error message to the client
            error_data = {"type": "error", "message": str(e)}
            yield f"data: {json.dumps(error_data)}\n\n"

    response = StreamingHttpResponse(event_stream(), content_type='text/event-stream')
    response['Cache-Control'] = 'no-cache'
    response['X-Accel-Buffering'] = 'no'  # For Nginx
    return response


async def get_messages(request, thread_id):
    try:
        client = await get_openai_client(request)
    except APIError as e:
        return JsonResponse({"error": e.message}, status=e.status)

    messages = await fetch_messages(client, thread_id)
    return JsonResponse({'success': True, 'messages': messages})


async def fetch_messages(client, thread_id):
    try:
        response = await client.beta.threads.messages.list(
            thread_id=thread_id,
            order='asc',
        )
        messages = response.data

        async def format_message(message):
            role = message.role
            content = ""
            if message.content:
                for content_item in message.content:
                    if content_item.type == "text":
                        text_content = content_item.text.value
                        annotations = content_item.text.annotations

                        for index, annotation in enumerate(annotations):
                            # Fetch file citation
                            if file_citation := getattr(annotation, 'file_citation', None):
                                citation_file_id = getattr(file_citation, 'file_id', None)
                                try:
                                    cited_file = await client.files.retrieve(citation_file_id)
                                    file_info = f'({cited_file.filename})'
                                except OpenAIError as e:
                                    logger.warning(f"File with id {citation_file_id} not found: {e}")
                                    file_info = '(Reference file is not available)'

                                # Replace the annotation text with the file info
                                text_content = text_content.replace(annotation.text, f' [{index + 1}] {file_info}')

                            # Fetch file path
                            if file_path := getattr(annotation, 'file_path', None):
                                file_path_file_id = getattr(file_path, 'file_id', None)
                                download_link = reverse('download_file', args=[thread_id, file_path_file_id])

                                # Replace the annotation text with the download link
                                text_content = text_content.replace(annotation.text, download_link)

                        content += f"<p>{text_content}</p>"

                    elif content_item.type == "image_file":
                        image_file_id = content_item.image_file.file_id
                        try:
                            image_data = await fetch_image_file(client, image_file_id)
                            content += f'<p><img src="{image_data}" style="max-width: 100%;"></p>'
                        except OpenAIError as e:
                            logger.warning(f"Error fetching image file with id {image_file_id}: {e}")
                            content += f"<p>(Error fetching image file)</p>"
                    else:
                        content += f"<p>Unsupported content type: {content_item.type}</p>"

            # Fetch assistant name if role is 'assistant'
            if role == 'assistant':
                try:
                    assistant_response = await client.beta.assistants.retrieve(assistant_id=message.assistant_id)
                    name = assistant_response.name
                except OpenAIError as e:
                    logger.warning(f"Assistant with id {message.assistant_id} not found: {e}")
                    name = "assistant"
            else:
                name = role

            return {
                "role": role,
                "name": name,
                "message": content
            }

        # Run the formatting tasks concurrently
        formatted_messages_tasks = [format_message(message) for message in messages]
        formatted_messages = await asyncio.gather(*formatted_messages_tasks)

        return formatted_messages
    except Exception as e:
        logger.error(f"Error fetching messages: {e}")
        return []


async def fetch_image_file(client, file_id):
    content_response = await client.files.content(file_id)

    # Read the binary content from the response
    image_binary = content_response.read()

    # Convert the binary content to a base64 encoded string
    image_base64 = base64.b64encode(image_binary).decode('utf-8')

    # Create a data URL
    image_data_url = f"data:image/png;base64,{image_base64}"

    return image_data_url


async def get_thread_files(request, thread_id):
    try:
        client = await get_openai_client(request)
    except APIError as e:
        return JsonResponse({"error": e.message}, status=e.status)

    try:
        # Retrieve the thread details from OpenAI
        response = await client.beta.threads.retrieve(thread_id=thread_id)
        file_ids = response.tool_resources.code_interpreter.file_ids
    except Exception as e:
        logger.error(f"Error retrieving file IDs from OpenAI: {e}")
        return JsonResponse({'success': False, 'error': 'Error retrieving file IDs from OpenAI'}, status=500)

    async def fetch_file(file_id):
        try:
            file_response = await client.files.retrieve(file_id=file_id)
            return {
                "file_id": file_id,
                "file_name": file_response.filename,
                "created_at": format_time(file_response.created_at),
                "bytes": file_response.bytes,
            }
        except Exception as e:
            logger.error(f"Error retrieving file from OpenAI: {e}")
            return None

    # Run the file retrieval tasks concurrently
    file_tasks = [fetch_file(file_id) for file_id in file_ids]
    files_responses = await asyncio.gather(*file_tasks)

    # Filter out any failed file retrievals
    files = [file for file in files_responses if file is not None]

    return JsonResponse({'success': True, 'files': files})


class DownloadFileView(View):
    async def get(self, request, thread_id, file_id):
        try:
            client = await get_openai_client(request)
        except APIError as e:
            return JsonResponse({"error": e.message}, status=e.status)

        try:
            # Retrieve file metadata
            file_info = await client.files.retrieve(file_id)
            # Retrieve file content
            file_content_response = await client.files.content(file_id)
            file_content = file_content_response.read()  # Read the content as bytes

            # Extract the filename from the full path
            filename = os.path.basename(file_info.filename)

            response = HttpResponse(file_content, content_type='application/octet-stream')
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            return response
        except OpenAIError as e:
            raise Http404(f"File not found: {e}")


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
