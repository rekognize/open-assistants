from ninja import NinjaAPI
from ninja.security import HttpBearer
from ninja.errors import AuthenticationError
from openai import AsyncOpenAI
from django.http import JsonResponse
from ..main.models import Project
from .models import Folder, FolderFile


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

    qs = qs.select_related("created_by").prefetch_related("folderfile_set")

    folders = []
    async for folder in qs:
        folders.append({
            "uuid": folder.uuid,
            "name": folder.name,
            "created_at": folder.created_at,
            "created_by": folder.created_by.username,
            "modified_at": folder.modified_at,
            "public": folder.public,
            "sync_source": folder.sync_source,
            "file_ids": [ff.file_id for ff in folder.folderfile_set.all()],
        })
    return {"folders": folders}


@api.get("/{folder_uuid}/list/")
async def list_files(request, folder_uuid):
    file_ids = [
        file_id
        async for file_id in FolderFile.objects.filter(folder__uuid=folder_uuid).values_list('file_id', flat=True)
    ]
    return {"file_ids": file_ids}


@api.get("/{folder_uuid}/sync/")
async def sync_folder(request, folder_uuid):
    folder = Folder.objects.get(uuid=folder_uuid)
    folder.sync_files()
