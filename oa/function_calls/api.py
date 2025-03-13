from asgiref.sync import sync_to_async
from ninja import NinjaAPI
from ninja.security import HttpBearer
from ninja.errors import AuthenticationError
from ninja import Schema
from openai import AsyncOpenAI, OpenAI
from django.http import JsonResponse
from ..main.models import Project
from .models import BaseAPIFunction, LocalAPIFunction, FunctionExecution, CodeInterpreterScript

api = NinjaAPI(urls_namespace="functions-api")


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
async def list_functions(request):
    functions = []
    async for function in LocalAPIFunction.objects.all():
        functions.append({
            "uuid": function.uuid,
            "type": "local",  # TODO: Add external type
            "name": function.name,
            "slug": function.slug,
            "result_type": function.result_type,
        })
    return {"functions": functions}


@api.get("/list_local_functions", auth=BearerAuth())
async def list_local_functions(request):
    try:
        functions = LocalAPIFunction.objects.filter(
            projects=request.auth['project'],
        ).order_by('-created_at')
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

    functions_data = []
    async for func in functions:
        functions_data.append({
            'uuid': func.uuid,
            'name': func.name,
            'slug': func.slug,
            'description': func.description,
            'argument_schema': func.argument_schema,
            'created_at': func.created_at.isoformat() if func.created_at else None,
            'modified_at': func.modified_at.isoformat() if func.modified_at else None,
            'code': func.code,
            'extra_context': func.extra_context,
            'result_type': func.result_type,
            'result_template': func.result_template,
            'version': func.version,
            'assistant_ids': func.assistant_ids,
            "type": "local",
        })

    return JsonResponse({"functions": functions_data})


@api.get("/get_function_executions/{slug}", auth=BearerAuth())
def get_function_executions(request, slug: str):
    try:
        function_instance = BaseAPIFunction.objects.get(slug=slug)
    except BaseAPIFunction.DoesNotExist:
        return JsonResponse({"executions": []})

    if hasattr(function_instance, 'localapifunction'):
        if not function_instance.localapifunction.projects.filter(uuid=request.auth['project'].uuid).exists():
            return JsonResponse({"executions": []})

    executions = FunctionExecution.objects.filter(function=function_instance).order_by('-time')

    executions_data = []
    for execution in executions:
        executions_data.append({
            'id': execution.id,
            'time': execution.time.isoformat() if execution.time else None,
            'arguments': execution.arguments,
            'status_code': execution.status_code,
            'executed_version': execution.executed_version,
            'error_message': execution.error_message,
            'thread_id': execution.thread.openai_id if execution.thread else None,
            'thread_metadata': execution.thread.metadata if execution.thread else None,
        })

    return JsonResponse({"executions": executions_data})


@api.get("/list_scripts", auth=BearerAuth())
def list_scripts(request):
    try:
        scripts = CodeInterpreterScript.objects.filter(
            project=request.auth['project']
        ).order_by('-created_at', 'snippet_index')
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

    scripts_data = []
    for script in scripts:
        scripts_data.append({
            'id': script.id,
            'assistant_id': script.assistant_id,
            'thread_id': script.thread_id,
            'run_id': script.run_id,
            'run_step_id': script.run_step_id,
            'tool_call_id': script.tool_call_id,
            'created_at': script.created_at.isoformat() if script.created_at else None,
            'snippet_index': script.snippet_index,
            'code': script.code,
        })

    return JsonResponse({"scripts": scripts_data})


class FunctionCreateSchema(Schema):
    name: str
    description: str = ""
    argument_schema: dict = {}
    code: str = ""
    extra_context: dict = {}
    result_type: str = "application/json"
    version: int = 1


@api.post("/create_function", auth=BearerAuth())
async def create_function(request, payload: FunctionCreateSchema):
    try:
        project = request.auth['project']

        function = await LocalAPIFunction.objects.acreate(
            name=payload.name,
            description=payload.description,
            argument_schema=payload.argument_schema,
            code=payload.code,
            extra_context=payload.extra_context,
            result_type=payload.result_type,
            version=payload.version,
        )

        await sync_to_async(function.projects.add)(project)

        response_data = {
            "uuid": str(function.uuid),
            "name": function.name,
            "description": function.description,
            "argument_schema": function.argument_schema,
            "code": function.code,
            "extra_context": function.extra_context,
            "result_type": function.result_type,
            "version": function.version,
        }
        return JsonResponse(response_data)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


class FunctionUpdateSchema(Schema):
    name: str = None
    description: str = None
    argument_schema: dict = None
    code: str = None
    extra_context: dict = None
    result_type: str = None


@api.post("/update_function/{function_uuid}", auth=BearerAuth())
async def update_function(request, function_uuid, payload: FunctionUpdateSchema):
    try:
        function = await LocalAPIFunction.objects.aget(uuid=function_uuid, projects=request.auth['project'])
    except LocalAPIFunction.DoesNotExist:
        return JsonResponse({"error": "Function not found."}, status=404)
    try:
        if payload.name is not None:
            function.name = payload.name
        if payload.description is not None:
            function.description = payload.description
        if payload.argument_schema is not None:
            function.argument_schema = payload.argument_schema
        if payload.code is not None:
            function.code = payload.code
        if payload.extra_context is not None:
            function.extra_context = payload.extra_context
        if payload.result_type is not None:
            function.result_type = payload.result_type

        await function.asave()

        response_data = {
            "uuid": str(function.uuid),
            "name": function.name,
            "description": function.description,
            "argument_schema": function.argument_schema,
            "code": function.code,
            "extra_context": function.extra_context,
            "result_type": function.result_type,
            "version": function.version,
        }
        return JsonResponse(response_data)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


@api.post("/save_function")
def save_function(request, payload):
    LocalAPIFunction.objects.create(
        name=payload.name,
        description=payload.description,
    )


@api.post("/execute_function")
def execute_function(request, payload):
    # exec
    return {}


@api.post("/update_vector_store")
def update_vector_store(request, data):
    return {}


def invoke_assistant():
    pass
