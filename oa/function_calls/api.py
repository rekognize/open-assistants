import json
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
            'code': func.code,
            'extra_context': func.extra_context,
            'result_type': func.result_type,
            'result_template': func.result_template,
            'version': func.version,
            'assistant_id': func.assistant_id,
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
    description: str


@api.post("/create_function")
def create_function(request, data: FunctionCreateSchema):
    """
    Creates a function according to the given description
    """
    tools = [{
        "type": "function",
        "function": {
            "name": "execute_python_function",
            "description": "Executes a python function.",
            "strict": False,
            "parameters": {
                "type": "object",
                "required": [
                    "name",
                    "description",
                    "arguments",
                    "code",
                    "return_schema"
                ],
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "The name of the function"
                    },
                    "description": {
                        "type": "string",
                        "description": "The description of the function"
                    },
                    "arguments": {
                        "type": "array",
                        "description": "A list of function parameters, each describing a required or optional argument.",
                        "items": {
                            "type": "object",
                            "description": "Definition of the function parameter.",
                            "properties": {
                                "name": {
                                    "type": "string",
                                    "description": "The name of the parameter"
                                },
                                "type": {
                                    "type": "string",
                                    "description": "The data type of the parameter.",
                                    "enum": ["string", "number", "boolean", "object", "array"]
                                },
                                "description": {
                                    "type": "string",
                                    "description": "A short description of the parameter's purpose."
                                },
                                "required": {
                                    "type": ["boolean", "null"],
                                    "description": "Whether this parameter is required."
                                },
                                "enum": {
                                    "type": ["array", "null"],
                                    "description": "List of allowed values for this parameter, if applicable.",
                                    "items": {
                                        "type": ["string", "number", "boolean"]
                                    }
                                }
                            },
                            "required": ["name", "type", "description", "required", "enum"],
                            "additionalProperties": False
                        }
                    },
                    "code": {
                        "type": "string",
                        "description": "The full Python script to be executed"
                    },
                    "return_schema": {
                        "type": "object",
                        "description": "Defines the structure of the function's return value.\n"
                                       "It can be a single value, an object or a list of objects.\n"
                                       "E.g. values and their representations in the schema: \n"
                                       "{'x': 5} => {'x': {'type': 'number'}}\n"
                                       "{'name': 'Alice', 'score': 4.5} => "
                                       "{'name': {'type': 'string'}, 'score': {'type': 'number'}}\n"
                                       "df.to_records() => "
                                       "{'records': {'type': 'array', 'items': {'id': {'type': 'number'}, 'name': {'type': 'string'}, 'score': {'type': 'number'}}}\n"
                                       "Be specific as possible. ",
                        "minProperties": 1,
                        "additionalProperties": True
                    }
                },
                "additionalProperties": False
            }
        }
    }]

    messages = [{
        "role": "user",
        "content": f"Create a Python script that would accomplish the given task.\n"
                   f"The code should be a flat script, not a function.\n"
                   f"Available modules are: pandas, numpy, scipy, matplotlib, openai, requests\n"
                   f"DESCRIPTION: {data.description}\n"
    }]

    client = OpenAI()

    # JSON
    completion = client.chat.completions.create(
        model="gpt-4o",
        messages=messages,
        tools=tools,
        tool_choice="required"
    )
    response = json.loads(completion.choices[0].message.tool_calls[0].function.arguments)
    """
    # Pydantic:
    completion = client.beta.chat.completions.parse(
        model="gpt-4o",
        messages=messages,
        response_format=ExecutePythonFunctionSchema,
    )
    response = json.loads(completion.choices[0].message.content)
    """


    LocalAPIFunction.objects.create(
        name=response['name'],
        description=response['description'],
        arguments=response['arguments'],
        code=response['code'],
        return_schema=response.get('return_schema', {}),
    )

    return


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
