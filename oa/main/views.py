import asyncio
import base64
import json
import logging
import os

from asgiref.sync import async_to_sync
from django.http import JsonResponse, StreamingHttpResponse, HttpResponse, Http404, HttpResponseNotFound, \
    HttpResponseBadRequest
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from django.utils.translation import gettext as _
from django.views import View
from django.views.generic import TemplateView
from openai import AsyncAssistantEventHandler, OpenAIError
from openai.types.beta.threads import Text, TextDelta, ImageFile

from .models import Project, SharedLink
from .utils import format_time, verify_openai_key
from ..api.utils import APIError, aget_openai_client
from ..tools import FUNCTION_DEFINITIONS, FUNCTION_IMPLEMENTATIONS

logger = logging.getLogger(__name__)


class HomeView(TemplateView):
    template_name = 'home.html'


@login_required
def manage_assistants(request):
    if not Project.objects.filter(user=request.user).exists():
        return redirect('home')

    function_definitions_json = json.dumps(FUNCTION_DEFINITIONS)
    return render(request, "manage.html", {
        'function_definitions_json': function_definitions_json,
        'active_nav': 'manage'
    })


@login_required
def analytics(request):
    if not Project.objects.filter(user=request.user).exists():
        return redirect('home')

    return render(request, "analytics.html", {
        'active_nav': 'analytics'
    })


# Chat

class EventHandler(AsyncAssistantEventHandler):
    def __init__(self, shared_data, token=None):
        super().__init__()
        self.current_message = ""
        self.shared_data = shared_data  # Use shared_data instead of response_data
        self.stream_done = False
        self.current_annotations = []
        self.token = token

    async def on_message_created(self, message):
        print("on_message_created called")
        self.current_message = ""
        self.current_annotations = []
        self.shared_data.append({"type": "message_created"})

    async def on_text_delta(self, delta: TextDelta, snapshot: Text):
        # print(f"on_text_delta called with delta: {delta.value}")

        if delta.value:
            self.current_message += delta.value

        # Collect annotations from the snapshot
        self.current_annotations = []
        if snapshot.annotations:
            print(f"Annotations found: {snapshot.annotations}")
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
        print("on_message_done called")
        # Send the final message content and annotations to the client
        self.shared_data.append({
            "type": "message_done",
            "text": self.current_message,
            "annotations": self.current_annotations
        })

    async def on_image_file_done(self, image_file: ImageFile) -> None:
        print(f"on_image_file_done called with file_id: {image_file.file_id}")
        image_url = reverse('serve_image_file', args=[image_file.file_id])
        if self.token:
            image_url += f'?token={self.token}'
        self.current_message += f'<p><img src="{image_url}" style="max-width: 100%;"></p>'

        # No annotations for images
        self.shared_data.append({
            "type": "image_file",
            "text": self.current_message,
            "annotations": []
        })

    async def on_end(self):
        print("on_end called")
        self.stream_done = True
        self.shared_data.append({"type": "end_of_stream"})


def serve_image_file(request, file_id):
    try:
        image_binary = async_to_sync(fetch_image_binary)(request, file_id)
        return HttpResponse(image_binary, content_type='image/png')
    except APIError as e:
        return JsonResponse({"error": e.message}, status=e.status)
    except OpenAIError as e:
        logger.error(f"Error fetching image file: {e}")
        return HttpResponseNotFound('Image not found')

async def fetch_image_binary(request, file_id):
    client = await aget_openai_client(request)
    content_response = await client.files.content(file_id)
    image_binary = content_response.read()
    return image_binary


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


async def stream_responses(request, thread_id, assistant_id):
    token = request.GET.get('token')
    if token:
        request.GET = request.GET.copy()
        request.GET['token'] = token
    try:
        client = await aget_openai_client(request)
    except APIError as e:
        return JsonResponse({"error": e.message}, status=e.status)

    async def event_stream():
        shared_data = []
        event_handler = EventHandler(shared_data=shared_data, token=token)
        try:
            async with client.beta.threads.runs.stream(
                thread_id=thread_id,
                assistant_id=assistant_id,
                event_handler=event_handler,
            ) as stream:
                # Process events as they arrive
                async for event in stream:
                    print(f"Received event: {event.event}")

                    # Handle 'requires_action' events here
                    if event.event == "thread.run.requires_action":
                        run_id = event.data.id
                        required_action = event.data.required_action
                        if required_action.type == "submit_tool_outputs":
                            tool_calls = required_action.submit_tool_outputs.tool_calls
                            tool_outputs = []

                            for tool_call in tool_calls:
                                tool_call_id = tool_call.id
                                function_name = tool_call.function.name
                                function_args_json = tool_call.function.arguments
                                function_args = json.loads(function_args_json)

                                print("tool_call_id:", tool_call_id)
                                print(f"Function call received: {function_name} with arguments {function_args}")

                                # Execute the function and get the output
                                if function_name in FUNCTION_IMPLEMENTATIONS:
                                    function_class = FUNCTION_IMPLEMENTATIONS[function_name]
                                    try:
                                        # Instantiate the class with the arguments
                                        function_instance = function_class(**function_args)
                                        # If 'main' is synchronous, run it in a thread
                                        output = await asyncio.to_thread(function_instance.main)
                                        print(f"Output successful for: {function_name}")
                                        # Ensure the output is JSON-serializable
                                        output_json = json.dumps(output)
                                    except Exception as e:
                                        output = f"Error executing function {function_name}: {str(e)}"
                                        output_json = json.dumps({"error": output})
                                else:
                                    output = f"Function {function_name} not found"
                                    output_json = json.dumps({"error": output})

                                tool_outputs.append({"tool_call_id": tool_call_id, "output": output_json})

                            # Create a new EventHandler instance for the submit_tool_outputs_stream
                            tool_output_event_handler = EventHandler(shared_data=shared_data)

                            # Submit tool outputs
                            async with client.beta.threads.runs.submit_tool_outputs_stream(
                                thread_id=thread_id,
                                run_id=run_id,
                                tool_outputs=tool_outputs,
                                event_handler=tool_output_event_handler,
                            ) as tool_output_stream:
                                # Process events from the tool output stream
                                async for tool_event in tool_output_stream:
                                    print(f"tool_event: {tool_event.event}")

                                    while shared_data:
                                        data = shared_data.pop(0)
                                        yield f"data: {json.dumps(data)}\n\n"

                                        await asyncio.sleep(0)

                    # Yield data to the client immediately
                    while shared_data:
                        data = shared_data.pop(0)
                        yield f"data: {json.dumps(data)}\n\n"

                        # Flush the response to the client
                        await asyncio.sleep(0)  # Yield control to the event loop

                # After the stream ends, process any remaining shared_data
                while shared_data:
                    data = shared_data.pop(0)
                    print(f"Streaming data after stream ends: {data}")
                    yield f"data: {json.dumps(data)}\n\n"
                    await asyncio.sleep(0)  # Yield control to the event loop
                    if data.get("type") == "end_of_stream":
                        return

        except Exception as e:
            # Yield an error message to the client
            error_data = {"type": "error", "message": str(e)}
            yield f"data: {json.dumps(error_data)}\n\n"

    response = StreamingHttpResponse(event_stream(), content_type='text/event-stream')
    response['Cache-Control'] = 'no-cache'
    response['X-Accel-Buffering'] = 'no'  # For Nginx
    return response


async def get_messages(request, thread_id):
    token = request.headers.get('X-Token') or request.GET.get('token')
    try:
        client = await aget_openai_client(request)
    except APIError as e:
        return JsonResponse({"error": e.message}, status=e.status)

    messages = await fetch_messages(client, thread_id, token)
    return JsonResponse({'success': True, 'messages': messages})


async def fetch_messages(client, thread_id, token=None):
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

                                # Include the token in the download link
                                if token:
                                    download_link += f'?token={token}'

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
        client = await aget_openai_client(request)
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
            client = await aget_openai_client(request)
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

        # Verify the key with OpenAI
        is_valid, error_message = verify_openai_key(key)
        if not is_valid:
            return JsonResponse({'success': False, 'error': error_message})

        # Check if the user already has a project with this key
        if Project.objects.filter(user=request.user, key=key).exists():
            return JsonResponse({'success': False, 'error': 'You already have a project with this key.'})

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
                # Check if another project with the same key exists for the user
                if Project.objects.filter(user=request.user, key=key).exclude(id=project_id).exists():
                    return JsonResponse({'success': False, 'error': 'You already have a project with this key.'})
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


# Sharing

@login_required
def share_assistant(request, assistant_id):
    if not request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return HttpResponseBadRequest('Invalid request')

    # Retrieve the selected project
    selected_project_id = request.session.get('selected_project_id') or request.GET.get('selected_project_id')
    selected_project = None

    if selected_project_id:
        try:
            selected_project = Project.objects.get(id=int(selected_project_id), user=request.user)
        except (ValueError, Project.DoesNotExist):
            return JsonResponse({'status': 'error', 'message': _('Invalid project selected.')}, status=400)
    else:
        return JsonResponse({'status': 'error', 'message': _('No project selected.')}, status=400)

    if request.method == 'POST':
        # Check the number of existing shared links for the assistant
        links_count = SharedLink.objects.filter(assistant_id=assistant_id, project=selected_project).count()
        if links_count >= 5:
            return JsonResponse({
                'status': 'info',
                'message': _('You can only create up to 5 links per assistant.')
            })

        try:
            # Create a new shareable link
            new_link = SharedLink.objects.create(assistant_id=assistant_id, project=selected_project)
            link_url = request.build_absolute_uri(reverse('shared_thread_detail', args=[new_link.token]))
            return JsonResponse({
                'status': 'success',
                'message': _('New shareable link created.'),
                'link': {'token': str(new_link.token), 'url': link_url}
            })
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

    elif request.method == 'GET':
        links = SharedLink.objects.filter(assistant_id=assistant_id, project=selected_project)

        try:
            if links:
                data = {'links': [{'token': link.token,
                                   'url': request.build_absolute_uri(f'/shared/{link.token}/'),
                                   'name': link.name
                                   } for link in links]}
            else:
                data = {'message': _('No links available.')}
            return JsonResponse(data)
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

    return JsonResponse({'status': 'error', 'message': 'Invalid request method.'}, status=400)


@login_required
def delete_shared_link(request, link_token):
    if not request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return HttpResponseBadRequest('Invalid request')

    if request.method == 'POST':
        try:
            link = get_object_or_404(SharedLink, token=link_token)
            link.delete()
            return JsonResponse({'status': 'success', 'message': _('Link deleted successfully.')})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

    return JsonResponse({'status': 'error', 'message': 'Invalid request method.'}, status=400)


def shared_thread_detail(request, token):
    shared_link = get_object_or_404(SharedLink, token=token)
    assistant_id = shared_link.assistant_id

    # Initial context
    context = {
        'assistant_id': assistant_id,
        'token': token,
        'is_shared_thread': True,
    }

    return render(request, 'chat/chat.html', context)
