import json
import uuid
from collections import defaultdict

from asgiref.sync import sync_to_async
from django.shortcuts import get_object_or_404
from ninja import NinjaAPI, Schema, Field
from ninja.security import HttpBearer
from ninja.errors import AuthenticationError
from openai import AsyncOpenAI
from django.http import JsonResponse
from ..main.models import Project
from .models import Folder, FolderAssistant

api = NinjaAPI(urls_namespace="folders-api")


class APIError(Exception):
    def __init__(self, message, status=500):
        self.message = message
        self.status = status
        super().__init__(self.message)


class BearerAuth(HttpBearer):
    async def authenticate(self, request, token: str):
        try:
            project = await Project.objects.aget(uuid=token)
        except Project.DoesNotExist:
            return AuthenticationError("Invalid or missing Bearer token.")

        try:
            client = AsyncOpenAI(api_key=project.key)
        except APIError as e:
            return JsonResponse({"error": e.message}, status=e.status)

        return {
            'project': project,
            'client': client,
        }


@api.get("/", auth=BearerAuth())
async def list_folders(request):
    project = request.auth['project']
    qs = Folder.objects.filter(projects=project)

    # Filter by assistant_id
    assistant_id = request.GET.get('assistant_id')
    if assistant_id is not None:
        qs = qs.filter(folderassistant_set__assistant_id=assistant_id)

    qs = qs.select_related("created_by")

    folders = []
    async for folder in qs:
        folders.append({
            "uuid": folder.uuid,
            "name": folder.name,
            "created_at": folder.created_at,
            "created_by": folder.created_by.username,
            "modified_at": folder.modified_at,
            "public": folder.public,
            "file_ids": folder.file_ids,
        })
    return {"folders": folders}


class FolderUpdateSchema(Schema):
    file_ids: list[str] | None = Field(default=None)
    name: str | None = None


@api.post("/{folder_uuid}/files/", auth=BearerAuth())
def update_folder(request, folder_uuid: uuid.UUID, payload: FolderUpdateSchema):
    folder = get_object_or_404(Folder, uuid=folder_uuid)
    if payload.file_ids is not None:
        folder.file_ids = payload.file_ids
    if payload.name is not None:
        folder.name = payload.name
    folder.save()
    return {"file_ids": folder.file_ids, "name": folder.name}


@api.post("/create/", auth=BearerAuth())
def create_folder(request):
    folder = Folder.objects.create(
        created_by=request.user,
    )
    folder.projects.add(request.auth['project'])
    return {"folder_uuid": folder.uuid}


@api.delete("/{folder_uuid}/", auth=BearerAuth())
def delete_folder(request, folder_uuid: uuid.UUID):
    folder = get_object_or_404(Folder, uuid=folder_uuid)
    folder.delete()
    return {"folder_uuid": folder_uuid}


# Assistant - Folder relations

@api.get("/assistant-folders", auth=BearerAuth())
async def list_assistant_folders(request):
    project = request.auth['project']
    qs = FolderAssistant.objects.filter(folder__projects=project).select_related("folder")
    mapping = {}
    async for fa in qs:
        # Use the assistant_id as key and collect folder UUIDs
        mapping.setdefault(fa.assistant_id, []).append(str(fa.folder.uuid))
    return {"assistant_folders": mapping}


@api.get("/folder-assistants", auth=BearerAuth())
async def list_folder_assistants(request):
    project = request.auth['project']
    qs = FolderAssistant.objects.filter(folder__projects=project).select_related("folder")
    folder_assistants = defaultdict(list)
    async for fa in qs:
        folder_assistants[str(fa.folder.uuid)].append(fa.assistant_id)
    return {"folder_assistants": folder_assistants}


@api.post("/assistants/{assistant_id}", auth=BearerAuth())
async def modify_assistant_folders(request, assistant_id):
    project = request.auth['project']
    data = json.loads(request.body)
    folder_ids = data.get("folder_ids")

    if not isinstance(folder_ids, list):
        return JsonResponse({'success': False, 'error': 'Invalid folder_ids'}, status=400)

    # TODO: change sync_to_async
    # Get current FolderAssistant relations for this assistant in the current project
    current_folder_ids = set(map(str, await sync_to_async(list)(
        FolderAssistant.objects.filter(assistant_id=assistant_id, folder__projects=project)
        .values_list('folder__uuid', flat=True)
    )))

    new_folder_ids = set(folder_ids)

    # Determine which relations to remove and which to add.
    to_remove = current_folder_ids - new_folder_ids
    to_add = new_folder_ids - current_folder_ids

    await sync_to_async(FolderAssistant.objects.filter(assistant_id=assistant_id, folder__uuid__in=to_remove).delete)()

    # For each folder that needs to be added, verify that the folder exists in the current project
    for folder_id in to_add:
        try:
            folder = await Folder.objects.aget(uuid=folder_id, projects=project)
            await sync_to_async(FolderAssistant.objects.create)(folder=folder, assistant_id=assistant_id)
        except Folder.DoesNotExist:
            # If the folder doesn't exist or isn't part of the project, skip it
            continue

    # TODO: remove skipped items from response

    return JsonResponse({'success': True, 'returned_folder_ids': list(new_folder_ids)})

