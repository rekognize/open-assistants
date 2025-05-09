import base64
import logging
from typing import Any

from openai import AsyncAssistantEventHandler
from openai.types.beta.threads import Text, TextDelta, ImageFile


logger = logging.getLogger(__name__)


class APIError(Exception):
    def __init__(self, message, status=500):
        self.message = message
        self.status = status
        super().__init__(self.message)


def serialize_to_dict(obj: Any) -> Any:
    """Recursively convert an object to a serializable dictionary."""
    if isinstance(obj, (str, int, float, bool, type(None))):
        return obj
    elif isinstance(obj, dict):
        return {k: serialize_to_dict(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [serialize_to_dict(v) for v in obj]
    elif hasattr(obj, "__dict__"):
        return {k: serialize_to_dict(v) for k, v in obj.__dict__.items() if not k.startswith('_')}
    elif hasattr(obj, "_asdict"):  # For named tuples and similar objects
        return serialize_to_dict(obj._asdict())
    else:
        raise TypeError(f"Type {type(obj)} not serializable")


class EventHandler(AsyncAssistantEventHandler):
    def __init__(self, request, shared_data):
        super().__init__()
        self.request = request
        self.current_message = ""
        self.shared_data = shared_data
        self.stream_done = False
        self.current_annotations = []

    async def on_message_created(self, message):
        self.current_message = ""
        self.current_annotations = []
        self.shared_data.append({"type": "message_created"})

    async def on_text_delta(self, delta: TextDelta, snapshot: Text):
        if delta.value:
            self.current_message += delta.value

        # Collect annotations from the snapshot
        self.current_annotations = []
        if snapshot.annotations:
            for annotation in snapshot.annotations:
                annotation_dict = annotation.to_dict()

                if hasattr(annotation, 'file_citation') and annotation.file_citation:
                    # Manually construct the file_citation dictionary
                    annotation_dict['file_citation'] = {
                        'file_id': annotation.file_citation.file_id,
                        'filename': 'Unknown File'  # Placeholder
                    }

                self.current_annotations.append(annotation_dict)

        # Send the updated message and annotations to the client
        self.shared_data.append({
            "type": "text_delta",
            "text": self.current_message,
            "annotations": self.current_annotations
        })

    async def on_message_done(self, message):
        # Send the final message content and annotations to the client
        self.shared_data.append({
            "type": "message_done",
            "text": self.current_message,
            "annotations": self.current_annotations
        })

    async def on_image_file_done(self, image_file: ImageFile) -> None:
        try:
            content_response = await self.request.auth['client'].files.content(image_file.file_id)
            image_binary = content_response.read()
            image_base64 = base64.b64encode(image_binary).decode('utf-8')
            image_data = f"data:image/png;base64,{image_base64}"

            self.current_message += f'<p><img src="{image_data}" style="max-width: 100%;"></p>'
        except APIError as e:
            logger.warning(f"Error fetching image file with id {image_file.file_id}: {e}")
            self.current_message += f"<p>(Error fetching image file)</p>"

        # Send an SSE event that includes the updated current_message
        self.shared_data.append({
            "type": "image_file",
            "text": self.current_message,
            "annotations": []
        })

    async def on_end(self):
        self.stream_done = True
        self.shared_data.append({"type": "end_of_stream"})
