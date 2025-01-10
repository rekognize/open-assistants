import asyncio
import base64
import json
import logging
import os
import httpx
from asgiref.sync import sync_to_async
from django.urls import reverse
from ninja import NinjaAPI, File, Form, Schema
from ninja.errors import AuthenticationError
from ninja.security import HttpBearer
from ninja.files import UploadedFile
from typing import List
from openai import AsyncOpenAI, OpenAIError
from django.http import JsonResponse, StreamingHttpResponse, HttpResponse, Http404
from .schemas import AssistantSchema, VectorStoreSchema, VectorStoreIdsSchema, FileUploadSchema, ThreadSchema, \
    AssistantSharedLink
from .utils import serialize_to_dict, APIError, EventHandler
from ..main.models import Project, SharedLink, Thread
from ..main.utils import format_time
from ..tools import FUNCTION_IMPLEMENTATIONS


api = NinjaAPI()

logger = logging.getLogger(__name__)


class BearerAuth(HttpBearer):
    async def authenticate(self, request, token: str):
        if token:
            try:
                project = await Project.objects.aget(uuid=token)
            except Project.DoesNotExist:
                return AuthenticationError("Invalid or missing Bearer token.")

            try:
                client = AsyncOpenAI(api_key=project.key)
            except APIError as e:
                return JsonResponse({"error": e.message}, status=e.status)
        else:
            # User is anonymous, check for shared token
            shared_token = request.headers.get('X-Token') or request.GET.get('token')

            if shared_token:
                try:
                    shared_link = await SharedLink.objects.select_related('project').aget(token=shared_token)
                    project = shared_link.project
                    client = AsyncOpenAI(api_key=project.key)

                except SharedLink.DoesNotExist:
                    raise APIError("Invalid or missing shared token.", status=403)
            else:
                raise APIError("Authentication required.", status=401)

        return {
            'project': project,
            'client': client,
        }


# Shared link administration

@api.post("/sharedlink", auth=BearerAuth())
def retrieve_or_create_shared_link(request, data: AssistantSharedLink):
    if data.token:
        link = SharedLink.objects.filter(
            project=request.auth['project'],
            assistant_id=data.assistant_id,
            token=data.token,
        ).first()
        if link:
            is_created = False
        else:
            return JsonResponse({'status': 'error', 'message': 'Invalid request.'}, status=400)
    else:
        try:
            link = SharedLink.objects.create(
                project=request.auth['project'],
                assistant_id=data.assistant_id,
                user=request.user
            )
            is_created = True
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

    uri = reverse('shared_thread_detail', kwargs={'shared_token': link.token})

    return JsonResponse({
        'status': 'success',
        'message': f"Shared link token created successfully: {link.token}",
        'shared_link': {
            'token': link.token,
            'url': f"https://{request.get_host()}{uri}",
            'assistant_id': link.assistant_id,
            'created': link.created,
            'user': link.user.username,
            'is_created': is_created,
        }
    })


@api.get("/sharedlinks/{assistant_id}", auth=BearerAuth())
def list_shared_links(request, assistant_id):
    try:
        links = SharedLink.objects.filter(
            project=request.auth['project'],
            assistant_id=assistant_id,
        ).order_by('-created')
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

    shared_links = [
        {
            "token": link.token,
            "url": f"https://{request.get_host()}{reverse('shared_thread_detail', kwargs={'shared_token': link.token})}",
            "assistant_id": link.assistant_id,
            "name": link.name,
            "created": link.created,
            "user": link.user.username,
        }
        for link in links
    ]

    return JsonResponse({"shared_links": shared_links})


@api.delete("/sharedlink/{link_token}", auth=BearerAuth())
def delete_shared_link(request, link_token):
    link = SharedLink.objects.filter(
        project=request.auth['project'],
        token=link_token,
    ).first()

    if not link:
        return JsonResponse({
            "status": "error",
            "message": "The shared link does not exist."
        }, status=404)

    link.delete()

    return JsonResponse({
        "status": "success",
        "message": f"Shared link token deleted successfully: {link.token}",
        "token": link.token,
    })


@api.post("/update/sharedlink", auth=BearerAuth())
def update_shared_link(request, data: AssistantSharedLink):
    try:
        link = SharedLink.objects.get(
            project=request.auth['project'],
            assistant_id=data.assistant_id,
            token=data.token,
        )

    except SharedLink.DoesNotExist:
        return JsonResponse({"status": "error", "message": "Shared link not found."}, status=404)

    # Update the name if provided
    name = data.name.strip() if data.name is not None else None
    link.name = name
    link.save()

    uri = reverse('shared_thread_detail', kwargs={'shared_token': link.token})

    return JsonResponse({
        "status": "success",
        "message": f"Shared link name updated successfully: {link.name}",
        "link": {
            "token": link.token,
            "url": f"https://{request.get_host()}{uri}",
            "name": link.name,
        }
    })


# Assistants

@api.post("/assistants", auth=BearerAuth())
async def create_assistant(request, payload: AssistantSchema):
    # Use the tools and tool_resources from the payload
    tools = payload.tools or []
    tool_resources = payload.tool_resources or {}

    try:
        assistant = await request.auth['client'].beta.assistants.create(
            name=payload.name,
            description=payload.description,
            instructions=payload.instructions,
            model=payload.model,
            tools=tools,
            tool_resources=tool_resources,
            metadata=payload.metadata
        )
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse(serialize_to_dict(assistant), status=201)


@api.get("/assistants", auth=BearerAuth())
async def list_assistants(request):
    try:
        assistants = await request.auth['client'].beta.assistants.list(order="desc", limit=100)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse({
        'assistants': serialize_to_dict(assistants.data)
    })


@api.get("/assistants/{assistant_id}", auth=BearerAuth())
async def retrieve_assistant(request, assistant_id):
    try:
        assistant = await request.auth['client'].beta.assistants.retrieve(assistant_id)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse(serialize_to_dict(assistant))


@api.post("/assistants/{assistant_id}", auth=BearerAuth())
async def modify_assistant(request, assistant_id, payload: AssistantSchema):
    # Use tools and tool_resources from the payload
    tools = payload.tools or []
    tool_resources = payload.tool_resources or {}

    try:
        assistant = await request.auth['client'].beta.assistants.update(
            assistant_id,
            name=payload.name,
            description=payload.description,
            instructions=payload.instructions,
            model=payload.model,
            tools=tools,
            tool_resources=tool_resources,
            metadata=payload.metadata
        )
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse(serialize_to_dict(assistant), status=200)


@api.delete("/assistants/{assistant_id}", auth=BearerAuth())
async def delete_assistant(request, assistant_id):
    try:
        assistant = await request.auth['client'].beta.assistants.delete(assistant_id)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse(serialize_to_dict(assistant))


@api.get("/assistants/{assistant_id}/threads", auth=BearerAuth())
async def list_threads(request, assistant_id):
    """
    Returns the thread information for the given assistant
    """
    threads = Thread.objects.filter(metadata___asst=assistant_id)

    async def get_thread_data(t):
        shared_link = await sync_to_async(lambda: t.shared_link)()
        user = await sync_to_async(lambda: t.user)()

        shared_link_user = None
        if shared_link:
            shared_link_user = await sync_to_async(lambda: shared_link.user)()

        user_data = None
        if user:
            user_data = {
                'username': user.username,
            }

        return {
            'id': t.openai_id,
            'created_at': t.created_at,
            'share': str(shared_link) if shared_link else None,
            'share_user': str(shared_link_user.username) if shared_link_user else None,
            'user': user_data,
        }

    threads_data = [await get_thread_data(t) async for t in threads]
    return JsonResponse({'threads': threads_data})


# Vector Stores

@api.post("/vector_stores", auth=BearerAuth())
async def create_vector_store(request, payload: VectorStoreSchema):
    expiration_days = payload.expiration_days if payload.expiration_days is not None else None

    expires_after = None
    if expiration_days:
        expires_after = {
            "anchor": "last_active_at",
            "days": payload.expiration_days,
        }

    try:
        vector_store = await request.auth['client'].beta.vector_stores.create(
            name=payload.name,
            expires_after=expires_after,
            metadata=payload.metadata
        )
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse(serialize_to_dict(vector_store), status=201)


@api.get("/vector_stores", auth=BearerAuth())
async def list_vector_stores(request):
    try:
        vector_stores = await request.auth['client'].beta.vector_stores.list(
            order="desc",
            limit=100,
        )
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse({"vector_stores": serialize_to_dict(vector_stores.data)})


@api.get("/vector_stores/{vector_store_id}", auth=BearerAuth())
async def retrieve_vector_store(request, vector_store_id):
    try:
        vector_store = await request.auth['client'].beta.vector_stores.retrieve(vector_store_id)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse(serialize_to_dict(vector_store))


@api.post("/vector_stores/{vector_store_id}", auth=BearerAuth())
async def modify_vector_store(request, vector_store_id, payload: VectorStoreSchema):
    expires_after = None
    if payload.expiration_days:
        expires_after = {
            "anchor": "last_active_at",
            "days": payload.expiration_days,
        }

    try:
        vector_store = await request.auth['client'].beta.vector_stores.update(
            vector_store_id,
            name=payload.name,
            expires_after=expires_after,
            metadata=payload.metadata
        )
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse(serialize_to_dict(vector_store), status=201)


@api.delete("/vector_stores/{vector_store_id}", auth=BearerAuth())
async def delete_vector_store(request, vector_store_id):
    try:
        vector_store = await request.auth['client'].beta.vector_stores.delete(vector_store_id)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse(serialize_to_dict(vector_store))


# Vector Store Files

@api.get("/vector_stores/{vector_store_id}/files", auth=BearerAuth())
async def list_vector_store_files(request, vector_store_id):
    try:
        vector_store_files = await request.auth['client'].beta.vector_stores.files.list(
            vector_store_id=vector_store_id,
            order="desc",
            limit=100,
        )
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse({"files": serialize_to_dict(vector_store_files.data)})


@api.get("/vector_stores/{vector_store_id}/files/{file_id}", auth=BearerAuth())
async def retrieve_vector_store_file(request, vector_store_id, file_id):
    try:
        vector_store_file = await request.auth['client'].beta.vector_stores.files.retrieve(
            vector_store_id=vector_store_id,
            file_id=file_id
        )
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse(serialize_to_dict(vector_store_file))


# Files

@api.post("/files/upload", auth=BearerAuth())
async def upload_files(
        request,
        files: List[UploadedFile] = File(...),
        payload: FileUploadSchema = Form(...)
):

    uploaded_files, failed_files, supported_files = [], [], []

    # Define the supported file types for file search (same as the client-side)
    supported_file_types = {
        ".c": "text/x-c",
        ".cpp": "text/x-c++",
        ".css": "text/css",
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".go": "text/x-golang",
        ".html": "text/html",
        ".java": "text/x-java",
        ".js": "text/javascript",
        ".json": "application/json",
        ".md": "text/markdown",
        ".pdf": "application/pdf",
        ".php": "text/x-php",
        ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        ".py": ["text/x-python", "text/x-script.python"],
        ".rb": "text/x-ruby",
        ".tex": "text/x-tex",
        ".ts": "application/typescript",
        ".txt": "text/plain"
    }

    def is_supported_file(file_name):
        extension = file_name[file_name.rfind("."):].lower()
        return extension in supported_file_types

    # Handle file uploads
    for uploaded_file in files:
        try:
            # Upload the file
            response = await request.auth['client'].files.create(
                file=(uploaded_file.name, uploaded_file.file),
                purpose="assistants"
            )
            uploaded_file_info = json.loads(response.json())
            uploaded_files.append(uploaded_file_info)

            # If the file is supported, add it to the supported_files list
            if is_supported_file(uploaded_file.name):
                supported_files.append(uploaded_file_info)

        except Exception as e:
            failed_files.append({
                "filename": uploaded_file.name,
                "error": str(e)
            })

    # Only attach supported files to vector stores if any vector stores are selected
    vector_store_ids = payload.vector_store_ids or []
    for vector_store_id in vector_store_ids:
        if len(supported_files) > 1:
            # Batch assignment for multiple files
            await request.auth['client'].beta.vector_stores.file_batches.create(
                vector_store_id=vector_store_id,
                file_ids=[f['id'] for f in supported_files]
            )
        elif len(supported_files) == 1:
            # Assign a single file
            await request.auth['client'].beta.vector_stores.files.create(
                vector_store_id=vector_store_id,
                file_id=supported_files[0]['id']
            )

    return JsonResponse({
        "uploaded_files": uploaded_files,
        "failed_files": failed_files,
        "supported_files": supported_files,
        "vector_store_ids": vector_store_ids,
    })


@api.get("/files", auth=BearerAuth())
async def list_files(request):
    try:
        files = await request.auth['client'].files.list(
            purpose='assistants'
        )
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse({"files": serialize_to_dict(files.data)})


@api.get("/files/{file_id}", auth=BearerAuth())
async def retrieve_file(request, file_id):
    try:
        file = await request.auth['client'].files.retrieve(file_id)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse(serialize_to_dict(file))


@api.post("/files/{file_id}/vector_stores/add", auth=BearerAuth())
async def add_file_to_vector_stores(request, file_id, payload: VectorStoreIdsSchema):
    """Adds the file to the given vector stores."""
    status = {'success': [], 'error': []}

    for vector_store_id in payload.vector_store_ids:
        try:
            vector_store_file = await request.auth['client'].beta.vector_stores.files.create(
                vector_store_id=vector_store_id,
                file_id=file_id
            )
            status['success'].append(vector_store_id)
        except Exception as e:
            status['error'].append(vector_store_id)

    return JsonResponse(serialize_to_dict(status))


@api.post("/files/{file_id}/vector_stores/remove", auth=BearerAuth())
async def remove_file_from_vector_stores(request, file_id, payload: VectorStoreIdsSchema):
    """Removes the file from the given vector stores."""
    status = {'success': [], 'error': []}

    for vector_store_id in payload.vector_store_ids:
        try:
            vector_store_file = await request.auth['client'].beta.vector_stores.files.delete(
                vector_store_id=vector_store_id,
                file_id=file_id
            )
            status['success'].append(vector_store_id)
        except Exception as e:
            status['error'].append(vector_store_id)

    return JsonResponse(serialize_to_dict(status))


@api.delete("/files/{file_id}", auth=BearerAuth())
async def delete_file(request, file_id):
    try:
        response = await request.auth['client'].files.delete(file_id)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse(serialize_to_dict(response))


# Threads

@api.post("/threads/create/{assistant_id}", auth=BearerAuth())
async def create_thread(request, assistant_id):
    try:
        response = await request.auth['client'].beta.threads.create(metadata={
            "_asst": assistant_id,
        })
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse(serialize_to_dict(response))


@api.get("/threads/{thread_id}", auth=BearerAuth())
async def retrieve_thread(request, thread_id):
    try:
        thread = await request.auth['client'].beta.threads.retrieve(thread_id)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse(serialize_to_dict(thread))


@api.post("/threads/{thread_id}", auth=BearerAuth())
async def modify_thread(request, thread_id, payload: ThreadSchema):
    # Prepare parameters for update
    update_params = {}
    if payload.title is not None:
        update_params['title'] = payload.title
    if payload.metadata is not None:
        update_params['metadata'] = payload.metadata

    if not update_params:
        return JsonResponse({"error": "No data provided to update."}, status=400)

    try:
        thread = await request.auth['client'].beta.threads.update(
            thread_id=thread_id,
            **update_params
        )
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse(serialize_to_dict(thread), status=200)


@api.post("/threads/{thread_id}/messages", auth=BearerAuth())
async def create_message(request, thread_id):
    try:
        # Parse JSON body
        body = json.loads(request.body)
        message_text = body.get('message')
        attachments = body.get('attachments', [])

        if not message_text:
            return JsonResponse({"error": "Message content is missing."}, status=400)

        formatted_attachments = []
        if attachments:
            for attachment in attachments:
                formatted_attachment = {}

                # Accessing 'file_id' using dictionary keys
                file_id = attachment.get('file_id')
                if file_id:
                    formatted_attachment['file_id'] = file_id

                # Accessing 'tools' using dictionary keys
                tools = attachment.get('tools')
                if tools:
                    formatted_attachment['tools'] = tools

                formatted_attachments.append(formatted_attachment)

        message_data = {
            "thread_id": thread_id,
            "role": "user",
            "content": message_text,
        }

        if formatted_attachments:
            message_data["attachments"] = formatted_attachments

        response = await request.auth['client'].beta.threads.messages.create(**message_data)

    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON."}, status=400)
    except KeyError as e:
        return JsonResponse({"error": f"Missing key: {str(e)}"}, status=400)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse(serialize_to_dict(response), status=201)


# Runs

@api.get("/threads/{thread_id}/runs", auth=BearerAuth())
async def list_runs(request, thread_id):
    try:
        runs = await request.auth['client'].beta.threads.runs.list(
            thread_id=thread_id,
            limit=100,
        )
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse({
        'runs': serialize_to_dict(runs.data)
    })


@api.get("/threads/{thread_id}/runs/{run_id}", auth=BearerAuth())
async def retrieve_run(request, thread_id, run_id):
    try:
        run = await request.auth['client'].beta.threads.runs.retrieve(
            thread_id= thread_id,
            run_id= run_id
        )
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse(serialize_to_dict(run))


@api.post("/threads/{thread_id}/runs/{run_id}/cancel", auth=BearerAuth())
async def cancel_run(request, thread_id, run_id):
    try:
        run = await request.auth['client'].beta.threads.runs.cancel(
            thread_id= thread_id,
            run_id= run_id
        )
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse({
        'assistants': serialize_to_dict(run.data)
    })


# Chat

@api.get("/stream/{assistant_id}/{thread_id}", auth=BearerAuth())
async def stream_responses(request, assistant_id: str, thread_id: str):
    async def event_stream():
        shared_data = []
        event_handler = EventHandler(shared_data=shared_data)
        try:
            async with request.auth['client'].beta.threads.runs.stream(
                thread_id=thread_id,
                assistant_id=assistant_id,
                event_handler=event_handler,
            ) as stream:
                # Process events as they arrive
                async for event in stream:
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

                                # Execute the function and get the output
                                if function_name in FUNCTION_IMPLEMENTATIONS:
                                    function_class = FUNCTION_IMPLEMENTATIONS[function_name]
                                    try:
                                        # Instantiate the class with the arguments
                                        function_instance = function_class(**function_args)
                                        # If 'main' is synchronous, run it in a thread
                                        output = await asyncio.to_thread(function_instance.main)
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
                            async with request.auth['client'].beta.threads.runs.submit_tool_outputs_stream(
                                thread_id=thread_id,
                                run_id=run_id,
                                tool_outputs=tool_outputs,
                                event_handler=tool_output_event_handler,
                            ) as tool_output_stream:
                                # Process events from the tool output stream
                                async for tool_event in tool_output_stream:
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


@api.get("/thread/{thread_id}/messages", auth=BearerAuth())
async def get_thread_messages(request, thread_id):
    try:
        response = await request.auth['client'].beta.threads.messages.list(
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
                                    cited_file = await request.auth['client'].files.retrieve(citation_file_id)
                                    file_info = f'({cited_file.filename})'
                                except OpenAIError as e:
                                    logger.warning(f"File with id {citation_file_id} not found: {e}")
                                    file_info = '(Reference file is not available)'

                                # Replace the annotation text with the file info
                                text_content = text_content.replace(annotation.text, f' [{index + 1}] {file_info}')

                            # Fetch file path
                            if file_path := getattr(annotation, 'file_path', None):
                                file_path_file_id = getattr(file_path, 'file_id', None)
                                download_link = reverse('api-1.0.0:download_file', kwargs={
                                    'file_id': file_path_file_id
                                })

                                # Replace the annotation text with the download link
                                text_content = text_content.replace(annotation.text, download_link)

                        content += f"<p>{text_content}</p>"

                    elif content_item.type == "image_file":

                        image_file_id = content_item.image_file.file_id

                        # Fetch the image and embed into the message
                        try:
                            content_response = await request.auth['client'].files.content(image_file_id)
                        except OpenAIError as e:
                            logger.warning(f"Error fetching image file with id {image_file_id}: {e}")
                            content += f"<p>(Error fetching image file)</p>"
                        else:
                            # Convert image content into base64 encoded data URL
                            image_binary = content_response.read()
                            image_base64 = base64.b64encode(image_binary).decode('utf-8')
                            image_data = f"data:image/png;base64,{image_base64}"
                            content += f'<p><img src="{image_data}" style="max-width: 100%;"></p>'
                    else:
                        content += f"<p>Unsupported content type: {content_item.type}</p>"

            # Fetch assistant name if role is 'assistant'
            if role == 'assistant':
                try:
                    assistant_response = await request.auth['client'].beta.assistants.retrieve(assistant_id=message.assistant_id)
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
        messages = await asyncio.gather(*formatted_messages_tasks)

    except Exception as e:
        logger.error(f"Error fetching messages: {e}")
        messages = []

    return JsonResponse({'success': True, 'messages': messages})


@api.get("/thread/{thread_id}/files", auth=BearerAuth())
async def get_thread_files(request, thread_id):
    try:
        # Retrieve the thread details from OpenAI
        response = await request.auth['client'].beta.threads.retrieve(thread_id=thread_id)
        file_ids = response.tool_resources.code_interpreter.file_ids
    except Exception as e:
        logger.error(f"Error retrieving file IDs from OpenAI: {e}")
        return JsonResponse({'success': False, 'error': 'Error retrieving file IDs from OpenAI'}, status=500)

    async def fetch_file(file_id):
        try:
            file_response = await request.auth['client'].files.retrieve(file_id=file_id)
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


@api.get("/download/{file_id}", auth=BearerAuth())
async def download_file(request, file_id: str):
    try:
        # Retrieve file metadata
        file_info = await request.auth['client'].files.retrieve(file_id)

        # Retrieve file content
        file_content_response = await request.auth['client'].files.content(file_id)
        file_content = await file_content_response.read()  # Read the content as bytes

        # Extract the filename from the full path
        filename = os.path.basename(file_info.filename)

        response = HttpResponse(file_content, content_type='application/octet-stream')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response

    except Exception as e:
        raise Http404(f"File not found: {e}")


# Get started

@api.post("/get_started/generate_instructions", auth=BearerAuth())
async def generate_instructions(request):
    data = json.loads(request.body)
    prompt = data.get("prompt")

    if not prompt:
        return JsonResponse({"error": "Missing prompt in request."}, status=400)

    try:
        response = await request.auth['client'].chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Provide system instructions for an assistant with the user prompt."},
                {"role": "user", "content": prompt}
            ]
        )
        # Extract the generated text from the API response
        generated_text = response.choices[0].message.content
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse({"generated_text": generated_text}, status=200)


# Admin APIs

@api.get("/get_costs", auth=BearerAuth())
async def get_costs(request):
    try:
        await request.auth['client'].models.list()
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

    openai_admin_key = os.getenv('OPENAI_ADMIN_KEY')
    if not openai_admin_key:
        return JsonResponse({'error': 'API key is missing'}, status=400)

    start_time = request.GET.get('start_time')
    if not start_time:
        return JsonResponse({'error': 'start_time is required'}, status=400)

    # Optional params
    project_ids_str = request.GET.get('project_ids')
    group_by = request.GET.get('group_by') or 'project_id'  # default to project_id if not set

    # Convert 'project_ids' into a list if present
    project_ids = []
    if project_ids_str:
        project_ids = project_ids_str.split(',')

    params = [
        ("start_time", start_time),
        ("limit", "180"),  # maximum
        ("group_by", group_by),
    ]

    for pid in project_ids:
        params.append(("project_ids", pid.strip()))

    headers = {
        "Authorization": f"Bearer {openai_admin_key}",
        "Content-Type": "application/json"
    }

    try:
        # DEBUG
        from urllib.parse import urlencode
        param_str = urlencode(params, doseq=True)
        debug_url = f"https://api.openai.com/v1/organization/costs?{param_str}"

        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(
                "https://api.openai.com/v1/organization/costs",
                headers=headers,
                params=params
            )
        response_data = response.json()

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

    return JsonResponse({
        'costs': serialize_to_dict(response_data)
    })
