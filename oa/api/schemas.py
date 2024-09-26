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
