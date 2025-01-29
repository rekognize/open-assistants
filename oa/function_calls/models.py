import httpx
from django.db import models
from django.utils.text import slugify
from ..main.models import Project


class CodeInterpreterScript(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    assistant_id = models.CharField(max_length=50, db_index=True)
    thread_id = models.CharField(max_length=50, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    code = models.TextField()


class LocalAPIFunction(models.Model):
    """
    Functions called via the local API and executed in a sandbox locally or in Lambda containers
    """
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)

    # JSON schema describing what parameters or fields are required as input
    # e.g. {"url": {"type": "string", "description": "URL or the webpage to fetch"}, ...}
    arguments = models.JSONField(default=dict)

    # The actual Python code to run
    # e.g. {"paragraphs": {"type": "array", "items": {"type": "string"}}}
    code = models.TextField()

    # JSON schema describing the expected output structure.
    return_schema = models.JSONField(default=dict)

    # Information on how to populate the initial context.
    # e.g. what data sources (CSV files, URLs) or parameters are expected.
    data_source_schema = models.JSONField(default=dict)

    # Jinja2 template to render the outputs
    template = models.TextField(blank=True, null=True)

    # Metadata
    version = models.PositiveIntegerField(default=1)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, blank=True, null=True)
    assistant_id = models.CharField(max_length=50, db_index=True, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def get_definition(self):
        # Returns the definition in OpenAI function definition format
        return {
            "name": self.name,
            "description": self.description,
            "strict": True,
            "parameters": {
                "type": "object",
                "properties": {
                    param['name']: {
                        "type": param.get('type', 'string'),
                        "description": param.get('description', ''),
                    } for param in self.initial_context_schema
                },
                "required": list(self.initial_context_schema.keys()),
                "additionalProperties": False
            },
        }


class LocalAPIFunctionExecution(models.Model):
    """
    Represents a single run of a ReusableScript, capturing the inputs, outputs,
    and any logs or metadata around execution.
    """
    script = models.ForeignKey(LocalAPIFunction, on_delete=models.CASCADE, related_name='executions')

    # The actual context/parameters used in this run
    initial_context = models.JSONField(default=dict)

    # The data sources used (e.g. references to file uploads, S3 paths, etc.)
    data_source = models.JSONField(default=dict)

    # The output produced by this run
    output = models.JSONField(default=dict, null=True, blank=True)

    # Execution metadata
    success = models.BooleanField(default=False)
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Execution of {self.script.name} at {self.created_at}"


class ExternalAPIFunction(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=100, blank=True)
    description = models.TextField()

    # API endpoint definition
    endpoint = models.URLField(blank=True, null=True)
    method = models.CharField(
        max_length=10, default='GET',
        choices=[(m, m) for m in ['GET', 'POST', 'PUT', 'DELETE']],
    )
    bearer_token = models.CharField(max_length=200, blank=True, null=True)

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def get_definition(self):
        properties, required = {}, []
        for parameter in self.parameters.all():
            properties[parameter.name] = {
                "type": parameter.get_type_display(),
                "description": parameter.description
            }
            if parameter.required:
                required.append(parameter.name)

        return {
            "name": self.slug,
            "description": self.description,
            "strict": True,
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": required,
                "additionalProperties": False
            },
        }

    async def execute(self, **kwargs):
        headers = {}
        if self.bearer_token:
            headers["Authorization"] = f"Bearer {self.bearer_token}"

        # Determine the endpoint (allowing URL override as a parameter)
        url = kwargs.pop('url', self.endpoint)
        if not url:
            raise ValueError("No endpoint URL provided.")

        async with httpx.AsyncClient() as client:
            try:
                if self.method == 'GET':
                    response = await client.get(url, headers=headers, params=kwargs)
                else:  # POST, PUT, DELETE
                    response = await client.request(
                        method=self.method,
                        url=self.endpoint,
                        headers=headers,
                        json=kwargs,
                    )

                response.raise_for_status()  # Raise an error for HTTP error responses

                # Handle non-JSON content (e.g., images, HTML)
                if 'application/json' in response.headers.get('Content-Type', ''):
                    return response.json()

                return response.content

            except httpx.RequestError as e:
                raise RuntimeError(f"Request failed: {e}")


class Parameter(models.Model):
    function = models.ForeignKey(ExternalAPIFunction, on_delete=models.CASCADE, related_name="parameters")
    name = models.CharField(max_length=100)
    type = models.CharField(max_length=1, choices=(
        ('o', 'object'),
        ('a', 'array'),
        ('s', 'string'),
        ('n', 'number'),
        ('b', 'boolean'),
        ('-', 'null'),
    ))
    description = models.TextField()
    required = models.BooleanField(default=False)

    def __str__(self):
        return f'{self.function.name}::{self.name}'


class ExternalAPIFunctionExecution(models.Model):
    function = models.ForeignKey(ExternalAPIFunction, on_delete=models.CASCADE)
    arguments = models.JSONField(default=dict, blank=True)
    result = models.JSONField(default=dict, blank=True)
    time = models.DateTimeField()

