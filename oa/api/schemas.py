from typing import List, Dict, Optional
from ninja import Schema
from pydantic import field_validator


class AssistantSchema(Schema):
    name: str
    instructions: str
    description: Optional[str] = None
    model: str
    vector_store_id: Optional[str] = None
    tools: List[Dict[str, str]] = [{"type": "code_interpreter"}]


class VectorStoreSchema(Schema):
    name: str
    expiration_days: Optional[int] = None

    @field_validator('expiration_days', mode='before')
    @classmethod
    def convert_empty_string_to_none(cls, v):
        if v == "":  # If the value is an empty string, return None
            return None
        return v


class VectorStoreIdsSchema(Schema):
    vector_store_ids: List[str]


class FileUploadSchema(Schema):
    vector_store_ids: Optional[List[str]] = []  # To hold selected vector store IDs


class ThreadSchema(Schema):
    title: Optional[str] = None
    metadata: Optional[Dict[str, str]] = None

    @field_validator('metadata')
    @classmethod
    def validate_metadata(cls, v):
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
