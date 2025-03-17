import uuid
import httpx
from django.db import models
from django.http import JsonResponse
from django.utils.text import slugify
from ..main.models import Project, Thread


class CodeInterpreterScript(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    assistant_id = models.CharField(max_length=50, db_index=True)
    thread_id = models.CharField(max_length=50, db_index=True)
    run_id = models.CharField(max_length=50, db_index=True)
    run_step_id = models.CharField(max_length=50, db_index=True)
    tool_call_id = models.CharField(max_length=50, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    snippet_index = models.PositiveIntegerField(default=1)
    code = models.TextField()

    def __str__(self):
        return f"CodeInterpreterScript(pk={self.pk}, run={self.run_id}, snippet={self.snippet_index})"


class BaseAPIFunction(models.Model):
    """
    Functions called by assistants and executed via the local or external APIs
    """
    uuid = models.UUIDField(default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
    projects = models.ManyToManyField('main.Project', blank=True)

    # JSON schema describing the parameters as in the OpenAI function definition
    argument_schema = models.JSONField(default=dict, blank=True)

    assistant_ids = models.JSONField(default=list, blank=True)

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        # Always update the slug to match the current name
        self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def get_definition(self):
        parameters = self.argument_schema.get("parameters", self.argument_schema)
        strict = self.argument_schema.get("strict", False)
        return {
            "name": self.slug,
            "description": self.description,
            "parameters": parameters,
            "strict": strict,
        }


class LocalAPIFunction(BaseAPIFunction):
    """
    Functions called via the local API and executed in a sandbox locally or in Lambda containers
    """

    # The actual Python code to process the input; blank => no processing, i.e. the input parameters are returned
    code = models.TextField(blank=True, default='')

    # Extra context required by the script; e.g. API keys
    extra_context = models.JSONField(default=dict, blank=True)

    # Response
    result_type = models.CharField(max_length=100, default='application/json')
    result_template = models.TextField(default=dict, blank=True)

    # Metadata
    version = models.PositiveIntegerField(default=1)

    async def execute(self, **kwargs):
        """
        Executes the stored Python code with the provided **kwargs and returns the final result variable.
        """
        # Use a single environment for both globals and locals.
        env = {}
        env.update(self.extra_context)
        env['kwargs'] = kwargs

        # Execute the stored code.
        try:
            exec(self.code, env)
        except Exception as e:
            # Return an error dictionary instead of a JsonResponse.
            return {"error": str(e)}

        # TODO: Apply result_template and return rendered result

        # Check that the code has set a "result" variable.
        if "result" not in env:
            return {"error": "No result returned from function code."}

        # Return the plain result dictionary.
        return env["result"]


class ExternalAPIFunction(BaseAPIFunction):
    """
    Functions called via an external API endpoint.
    """
    # API endpoint definition
    endpoint = models.URLField(blank=True, null=True)
    method = models.CharField(
        max_length=10, default='GET',
        choices=[(m, m) for m in ['GET', 'POST', 'PUT', 'DELETE']],
    )
    bearer_token = models.CharField(max_length=200, blank=True, null=True)

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


class FunctionExecution(models.Model):
    """
    Represents a single run of an APIFunction, capturing the inputs, outputs and any metadata around execution.
    """
    function = models.ForeignKey(BaseAPIFunction, related_name='executions', on_delete=models.CASCADE)
    thread = models.ForeignKey(Thread, related_name='function_executions', blank=True, null=True, on_delete=models.SET_NULL)

    arguments = models.JSONField(default=dict, blank=True)
    result = models.JSONField(default=dict, blank=True)

    status_code = models.CharField(max_length=5, blank=True, null=True)
    error_message = models.TextField(blank=True, null=True)

    executed_version = models.PositiveIntegerField(null=True, blank=True)

    time = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Execution of {self.function.name} at {self.time}"
