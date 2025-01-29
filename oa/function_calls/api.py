import json
from ninja import NinjaAPI
from ninja import Schema
from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Union
from openai import OpenAI
from oa.function_calls.models import LocalAPIFunction


api = NinjaAPI(urls_namespace="function_calls")


class FunctionCreateSchema(Schema):
    description: str


class FunctionParameter(BaseModel):
    name: str = Field(..., description="The name of the parameter")
    type: str = Field(..., description="The data type of the parameter", enum=["string", "number", "boolean", "object", "array"])
    description: str = Field(..., description="A short description of the parameter's purpose.")
    required: bool = Field(description="Whether this parameter is required.")
    enum: Optional[List[str]] = Field(description="List of allowed values for this parameter, if applicable.")
    default: Optional[Union[str, int, float, bool, dict, list, None]] = Field(description="The default value of the parameter, if applicable.")

class ReturnSchemaProperties(BaseModel):
    type: str = Field(..., enum=["string", "number", "boolean", "object", "array"], description="The data type of the property.")
    description: Optional[str] = Field(description="Description of this field.")

class ReturnSchemaItems(BaseModel):
    type: str = Field(..., enum=["string", "number", "boolean", "object", "array"], description="The data type of the array items.")
    description: Optional[str] = Field(description="Description of array items.")

class ReturnSchema(BaseModel):
    type: str = Field(..., description="The type of the output.", enum=["single_value", "object", "array"])
    description: str = Field(..., description="A short description of what the function returns.")
    schema: Optional[Dict[str, Union[str, Dict[str, ReturnSchemaProperties], ReturnSchemaItems]]] = Field(description="A JSON schema describing the return structure if type is 'object' or 'array'.")

class ExecutePythonFunctionSchema(BaseModel):
    name: str = Field(..., description="The name of the function")
    description: str = Field(..., description="The description of the function")
    arguments: List[FunctionParameter] = Field(..., description="A list of function parameters, each describing a required or optional argument.")
    code: str = Field(..., description="The full Python script to be executed")
    return_schema: ReturnSchema = Field(..., description="Defines the structure of the function's return value.")


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
            "strict": True,
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
                        "description": "Defines the structure of the function's return value.",
                        "properties": {
                            "type": {
                                "type": "string",
                                "description": "The type of the output.",
                                "enum": ["single_value", "object", "array"]
                            },
                            "description": {
                                "type": "string",
                                "description": "A short description of what the function returns."
                            },
                            "schema": {
                                "type": ["object", "null"],
                                "description": "A JSON schema describing the return structure if type is 'object' or 'array'.",
                                "properties": {
                                    "type": {
                                        "type": "string",
                                        "enum": ["object", "array"]
                                    },
                                    "properties": {
                                        "type": "object",
                                        "description": "Defines properties of an object return type.",
                                        "additionalProperties": False
                                    },
                                    "items": {
                                        "type": "object",
                                        "description": "Schema for each item if type is 'array'.",
                                        "properties": {
                                            "type": {
                                                "type": "string",
                                                "enum": ["string", "number", "boolean", "object", "array"]
                                            },
                                            "description": {
                                                "type": "string",
                                                "description": "Description of array items."
                                            }
                                        },
                                        "required": ["type", "description"],
                                        "additionalProperties": False
                                    }
                                },
                                "additionalProperties": False
                            }
                        },
                        "required": ["type", "description", "schema"],
                        "additionalProperties": False
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
                   f"DESCRIPTION: {data.description}\n"
    }]

    client = OpenAI()

    """
    completion = client.chat.completions.create(
        model="gpt-4o",
        messages=messages,
        tools=tools,
        tool_choice="required"
    )
    """

    completion = client.beta.chat.completions.parse(
        model="gpt-4o",
        messages=messages,
        response_format=ExecutePythonFunctionSchema,
    )

    response = json.loads(completion.choices[0].message.tool_calls[0].function.arguments)

    LocalAPIFunction.objects.create(
        name=response['name'],
        description=response['description'],
        arguments=response['arguments'],
        code=response['code'],
        return_schema=response['return_schema'],
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
