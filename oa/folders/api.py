from ninja import NinjaAPI
from .models import Folder, FolderFile


api = NinjaAPI(urls_namespace="folders")


@api.get("/")
async def list_folders(request):
    qs = Folder.objects.all()

    # Filter by project_uuid
    project_uuid = request.GET.get('project_uuid')
    if project_uuid is not None:
        qs = qs.filter(project__uuid=project_uuid)

    # Filter by vector_store_id
    vector_store_id = request.GET.get('vector_store_id')
    if vector_store_id is not None:
        qs = qs.filter(foldervectorstore_set__vector_store_id=vector_store_id)

    folders = {}
    async for folder in qs.select_related("project", "created_by"):
        folders[folder.name] = {
            "uuid": folder.uuid,
            "name": folder.name,
            "project": {
                "uuid": folder.project.uuid,
                "name": folder.project.name,
            } if folder.project else None,
            "created_at": folder.created_at,
            "created_by": folder.created_by.username,
            "modified_at": folder.modified_at,
            "public": folder.public,
            "sync_source": folder.sync_source,
        }
    return folders


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
