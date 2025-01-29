import json
from ninja import NinjaAPI
from ninja import Schema
from typing import List, Dict, Optional, Any
from openai import OpenAI
from oa.function_calls.models import LocalFunction


api = NinjaAPI(urls_namespace="function_calls")


@api.post("/create_function")
def create_function(request, description):
    """
    Creates a function according to the given description
    """
    tools = [{
        "type": "function",
        "function": {
            "name": "execute_python_function",
            "description": "Executes a python function.",
            "strict": True,
            "parameters": {
                "type": "object",
                "required": [
                    "import_statements",
                    "function_name",
                    "arguments",
                    "code",
                    "return",
                ],
                "properties": {
                    # "requirements": {
                    #     "type": "string",
                    #     "description": "Contents of the requirements.txt file listing the required modules."
                    # },
                    "import_statements": {
                        "type": "array",
                        "description": "List of import statements required to make the function run",
                        "items": {
                            "type": "string",
                            "description": "An import statement"
                        }
                    },
                    "function_name": {
                        "type": "string",
                        "description": "The name of the function"
                    },
                    "function_description": {
                        "type": "string",
                        "description": "The description of the function"
                    },
                    "arguments": {
                        "type": "array",
                        "description": "The list of arguments of the function to be executed",
                        "items": {
                            "type": "string",
                            "description": "Name of the argument"
                        }
                    },
                    "code": {
                        "type": "string",
                        "description": "The code to be executed inside the function"
                    },
                    "return": {
                        "type": "string",
                        "description": "The return value of the function"
                    }
                },
                "additionalProperties": False
            }
        }
    }]

    messages = [{
        "role": "user",
        "content": f"Create a Python function that would accomplish the given task.\n"
                   f"Available modules are: pandas, numpy, scipy, matplotlib, openai, requests\n"
                   f"DESCRIPTION: {description}\n"
    }]

    client = OpenAI()

    completion = client.chat.completions.create(
        model="gpt-4o",
        messages=messages,
        tools=tools,
        tool_choice="required"
    )

    response = json.loads(completion.choices[0].message.tool_calls[0].function.arguments)

    LocalFunction.objects.create(
        name=response['function_name'],
        description=payload.task,

    )

    return payload


@api.post("/save_function")
def save_function(request, payload):
    LocalFunction.objects.create(
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
