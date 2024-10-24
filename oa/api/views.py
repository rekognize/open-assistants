import json
from ninja import NinjaAPI, File, Form
from ninja.files import UploadedFile
from typing import List
from django.http import JsonResponse
from .schemas import AssistantSchema, VectorStoreSchema, VectorStoreIdsSchema, FileUploadSchema, ThreadSchema
from .utils import serialize_to_dict, APIError, get_openai_client

api = NinjaAPI()


# Assistants

@api.post("/assistants")
async def create_assistant(request, payload: AssistantSchema):
    try:
        client = await get_openai_client(request)
    except APIError as e:
        return JsonResponse({"error": e.message}, status=e.status)

    # Always include code_interpreter in tools
    tools = [{"type": "code_interpreter"}]
    tool_resources = {}

    if payload.vector_store_id:
        # Add file_search to tools
        tools.append({"type": "file_search"})
        # Add tool_resources for file_search
        tool_resources["file_search"] = {
            "vector_store_ids": [payload.vector_store_id]
        }

    try:
        assistant = await client.beta.assistants.create(
            name=payload.name,
            instructions=payload.instructions,
            description=payload.description,
            model=payload.model,
            tools=tools,
            tool_resources=tool_resources,
            metadata=payload.metadata
        )
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse(serialize_to_dict(assistant), status=201)


@api.get("/assistants")
async def list_assistants(request):
    try:
        client = await get_openai_client(request)
    except APIError as e:
        return JsonResponse({"error": e.message}, status=e.status)

    try:
        assistants = await client.beta.assistants.list(order="desc", limit=100)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse({
        'assistants': serialize_to_dict(assistants.data)
    })


@api.get("/assistants/{assistant_id}")
async def retrieve_assistant(request, assistant_id):
    try:
        client = await get_openai_client(request)
    except APIError as e:
        return JsonResponse({"error": e.message}, status=e.status)

    try:
        assistant = await client.beta.assistants.retrieve(assistant_id)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse(serialize_to_dict(assistant))


@api.post("/assistants/{assistant_id}")
async def modify_assistant(request, assistant_id, payload: AssistantSchema):
    try:
        client = await get_openai_client(request)
    except APIError as e:
        return JsonResponse({"error": e.message}, status=e.status)

    if payload.vector_store_id:
        tools = [{
            "type": "file_search"
        }]
        tool_resources = {
            "file_search": {
                "vector_store_ids": [payload.vector_store_id]
            }
        }
    else:
        tools, tool_resources = [], {}

    try:
        assistant = await client.beta.assistants.update(
            assistant_id,
            name=payload.name,
            instructions=payload.instructions,
            description=payload.description,
            model=payload.model,
            tools=tools,
            tool_resources=tool_resources,
            metadata=payload.metadata
        )
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse(serialize_to_dict(assistant), status=201)


@api.delete("/assistants/{assistant_id}")
async def delete_assistant(request, assistant_id):
    try:
        client = await get_openai_client(request)
    except APIError as e:
        return JsonResponse({"error": e.message}, status=e.status)

    try:
        assistant = await client.beta.assistants.delete(assistant_id)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse(serialize_to_dict(assistant))


# Vector Stores

@api.post("/vector_stores")
async def create_vector_store(request, payload: VectorStoreSchema):
    try:
        client = await get_openai_client(request)
    except APIError as e:
        return JsonResponse({"error": e.message}, status=e.status)

    expiration_days = payload.expiration_days if payload.expiration_days is not None else None

    expires_after = None
    if expiration_days:
        expires_after = {
            "anchor": "last_active_at",
            "days": payload.expiration_days,
        }

    try:
        vector_store = await client.beta.vector_stores.create(
            name=payload.name,
            expires_after=expires_after,
            metadata=payload.metadata
        )
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse(serialize_to_dict(vector_store), status=201)


@api.get("/vector_stores")
async def list_vector_stores(request):
    try:
        client = await get_openai_client(request)
    except APIError as e:
        return JsonResponse({"error": e.message}, status=e.status)

    try:
        vector_stores = await client.beta.vector_stores.list(
            order="desc",
            limit=100,
        )
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse({"vector_stores": serialize_to_dict(vector_stores.data)})


@api.get("/vector_stores/{vector_store_id}")
async def retrieve_vector_store(request, vector_store_id):
    try:
        client = await get_openai_client(request)
    except APIError as e:
        return JsonResponse({"error": e.message}, status=e.status)

    try:
        vector_store = await client.beta.vector_stores.retrieve(vector_store_id)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse(serialize_to_dict(vector_store))


@api.post("/vector_stores/{vector_store_id}")
async def modify_vector_store(request, vector_store_id, payload: VectorStoreSchema):
    try:
        client = await get_openai_client(request)
    except APIError as e:
        return JsonResponse({"error": e.message}, status=e.status)

    expires_after = None
    if payload.expiration_days:
        expires_after = {
            "anchor": "last_active_at",
            "days": payload.expiration_days,
        }

    try:
        vector_store = await client.beta.vector_stores.update(
            vector_store_id,
            name=payload.name,
            expires_after=expires_after,
            metadata=payload.metadata
        )
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse(serialize_to_dict(vector_store), status=201)


@api.delete("/vector_stores/{vector_store_id}")
async def delete_vector_store(request, vector_store_id):
    try:
        client = await get_openai_client(request)
    except APIError as e:
        return JsonResponse({"error": e.message}, status=e.status)

    try:
        vector_store = await client.beta.vector_stores.delete(vector_store_id)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse(serialize_to_dict(vector_store))


# Vector Store Files

@api.get("/vector_stores/{vector_store_id}/files")
async def list_vector_store_files(request, vector_store_id):
    try:
        client = await get_openai_client(request)
    except APIError as e:
        return JsonResponse({"error": e.message}, status=e.status)

    try:
        vector_store_files = await client.beta.vector_stores.files.list(
            vector_store_id=vector_store_id,
            order="desc",
            limit=100,
        )
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse({"files": serialize_to_dict(vector_store_files.data)})


@api.get("/vector_stores/{vector_store_id}/files/{file_id}")
async def retrieve_vector_store_file(request, vector_store_id, file_id):
    try:
        client = await get_openai_client(request)
    except APIError as e:
        return JsonResponse({"error": e.message}, status=e.status)

    try:
        vector_store_file = await client.beta.vector_stores.files.retrieve(
            vector_store_id=vector_store_id,
            file_id=file_id
        )
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse(serialize_to_dict(vector_store_file))


# Files

@api.post("/files/upload")
async def upload_files(
        request,
        files: List[UploadedFile] = File(...),
        payload: FileUploadSchema = Form(...)
):
    try:
        client = await get_openai_client(request)
    except APIError as e:
        return JsonResponse({"error": e.message}, status=e.status)

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
            response = await client.files.create(
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
            await client.beta.vector_stores.file_batches.create(
                vector_store_id=vector_store_id,
                file_ids=[f['id'] for f in supported_files]
            )
        elif len(supported_files) == 1:
            # Assign a single file
            await client.beta.vector_stores.files.create(
                vector_store_id=vector_store_id,
                file_id=supported_files[0]['id']
            )

    return JsonResponse({
        "uploaded_files": uploaded_files,
        "failed_files": failed_files,
        "supported_files": supported_files,
        "vector_store_ids": vector_store_ids,
    })


@api.get("/files")
async def list_files(request):
    try:
        client = await get_openai_client(request)
    except APIError as e:
        return JsonResponse({"error": e.message}, status=e.status)

    try:
        files = await client.files.list(
            purpose='assistants'
        )
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse({"files": serialize_to_dict(files.data)})


@api.get("/files/{file_id}")
async def retrieve_file(request, file_id):
    try:
        client = await get_openai_client(request)
    except APIError as e:
        return JsonResponse({"error": e.message}, status=e.status)

    try:
        file = await client.files.retrieve(file_id)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse(serialize_to_dict(file))


@api.post("/files/{file_id}/vector_stores/add")
async def add_file_to_vector_stores(request, file_id, payload: VectorStoreIdsSchema):
    """Adds the file to the given vector stores."""
    try:
        client = await get_openai_client(request)
    except APIError as e:
        return JsonResponse({"error": e.message}, status=e.status)

    status = {'success': [], 'error': []}

    for vector_store_id in payload.vector_store_ids:
        try:
            vector_store_file = await client.beta.vector_stores.files.create(
                vector_store_id=vector_store_id,
                file_id=file_id
            )
            status['success'].append(vector_store_id)
        except Exception as e:
            status['error'].append(vector_store_id)

    return JsonResponse(serialize_to_dict(status))


@api.post("/files/{file_id}/vector_stores/remove")
async def remove_file_from_vector_stores(request, file_id, payload: VectorStoreIdsSchema):
    """Removes the file from the given vector stores."""
    try:
        client = await get_openai_client(request)
    except APIError as e:
        return JsonResponse({"error": e.message}, status=e.status)

    status = {'success': [], 'error': []}

    for vector_store_id in payload.vector_store_ids:
        try:
            vector_store_file = await client.beta.vector_stores.files.delete(
                vector_store_id=vector_store_id,
                file_id=file_id
            )
            status['success'].append(vector_store_id)
        except Exception as e:
            status['error'].append(vector_store_id)

    return JsonResponse(serialize_to_dict(status))


@api.delete("/files/{file_id}")
async def delete_file(request, file_id):
    try:
        client = await get_openai_client(request)
    except APIError as e:
        return JsonResponse({"error": e.message}, status=e.status)

    try:
        response = await client.files.delete(file_id)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse(serialize_to_dict(response))


# Threads

@api.post("/threads")
async def create_thread(request):
    try:
        client = await get_openai_client(request)
    except APIError as e:
        return JsonResponse({"error": e.message}, status=e.status)

    assistant_id = request.GET.get('asst')

    try:
        response = await client.beta.threads.create(metadata={
            "_asst": assistant_id,
        })
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse(serialize_to_dict(response))


@api.get("/threads/{thread_id}")
async def retrieve_thread(request, thread_id):
    try:
        client = await get_openai_client(request)
    except APIError as e:
        return JsonResponse({"error": e.message}, status=e.status)

    try:
        thread = await client.beta.threads.retrieve(thread_id)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse(serialize_to_dict(thread))


@api.post("/threads/{thread_id}")
async def modify_thread(request, thread_id, payload: ThreadSchema):
    try:
        client = await get_openai_client(request)
    except APIError as e:
        return JsonResponse({"error": e.message}, status=e.status)

    # Prepare parameters for update
    update_params = {}
    if payload.title is not None:
        update_params['title'] = payload.title
    if payload.metadata is not None:
        update_params['metadata'] = payload.metadata

    if not update_params:
        return JsonResponse({"error": "No data provided to update."}, status=400)

    try:
        thread = await client.beta.threads.update(
            thread_id=thread_id,
            **update_params
        )
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse(serialize_to_dict(thread), status=200)


@api.post("/threads/{thread_id}/messages")
async def create_message(request, thread_id):
    try:
        client = await get_openai_client(request)
    except APIError as e:
        return JsonResponse({"error": e.message}, status=e.status)

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

        response = await client.beta.threads.messages.create(**message_data)

    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON."}, status=400)
    except KeyError as e:
        return JsonResponse({"error": f"Missing key: {str(e)}"}, status=400)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse(serialize_to_dict(response), status=201)
