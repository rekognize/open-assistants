from typing import List, Dict, Optional, Any
from ninja import Schema
from pydantic import field_validator


def validate_metadata(v):
    if v is None:
        return v
    if not isinstance(v, dict):
        raise ValueError("metadata must be a dictionary")
    if len(v) > 16:
        raise ValueError("metadata can contain at most 16 key-value pairs")
    for key, value in v.items():
        if not isinstance(key, str):
            raise ValueError(f"metadata key '{key}' must be a string")
        if len(key) > 64:
            raise ValueError(f"metadata key '{key}' exceeds maximum length of 64 characters")
        if not isinstance(value, str):
            raise ValueError(f"metadata value for key '{key}' must be a string")
        if len(value) > 512:
            raise ValueError(f"metadata value for key '{key}' exceeds maximum length of 512 characters")
    return v


class AssistantSchema(Schema):
    name: str
    description: Optional[str] = None
    instructions: str
    model: str
    tools: Optional[List[Dict[str, str]]] = None
    tool_resources: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, str]] = None

    _validate_metadata = field_validator('metadata')(validate_metadata)


class VectorStoreSchema(Schema):
    name: str
    expiration_days: Optional[int] = None
    metadata: Optional[Dict[str, str]] = None

    @field_validator('expiration_days', mode='before')
    @classmethod
    def convert_empty_string_to_none(cls, v):
        if v == "":  # If the value is an empty string, return None
            return None
        return v

    _validate_metadata = field_validator('metadata')(validate_metadata)


class VectorStoreIdsSchema(Schema):
    vector_store_ids: List[str]


class FileUploadSchema(Schema):
    vector_store_ids: Optional[List[str]] = []  # To hold selected vector store IDs


class ThreadSchema(Schema):
    title: Optional[str] = None
    metadata: Optional[Dict[str, str]] = None

    _validate_metadata = field_validator('metadata')(validate_metadata)
