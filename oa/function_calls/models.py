import httpx
from django.db import models
from django.http import JsonResponse
from django.utils.text import slugify
from ..main.models import Project


class BaseAPIFunction(models.Model):
    """
    Functions called by assistants and executed via the local or external APIs
    """
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=100, blank=True, unique=True)
    description = models.TextField(blank=True)

    # JSON schema describing the parameters as in the OpenAI function definition
    argument_schema = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def get_definition(self):
        # Returns the definition in OpenAI function definition format
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.argument_schema,
            # "strict": True,
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
    project = models.ForeignKey(Project, on_delete=models.CASCADE, blank=True, null=True)
    assistant_id = models.CharField(max_length=50, db_index=True, blank=True, null=True)

    async def execute(self, **kwargs):
        """
        Executes the stored Python code with the provided **kwargs and returns the final context as a JSON object.
        """

        # Setting the local environment for exec
        local_vars = dict(kwargs=kwargs)

        # Adding extra context
        local_vars.update(self.extra_context)

        status_code, result, error_message = 200, None, None

        # Execute the code
        try:
            exec(self.code, {}, local_vars)

        except Exception as e:
            status_code = 400
            error_message = str(e)

        else:
            # Remove built-in references
            executed_vars = {
                k: v for k, v in local_vars.items()
                if not (k.startswith('__') and k.endswith('__'))
            }

            # TODO: Apply result_template and return rendered result
            result = executed_vars

        # Return the final context as JSON
        return JsonResponse({
            'function_type': 'local',
            'function_name': self.slug,
            'result_type': self.result_type,
            'result': result,
            'error_message': error_message,
            'status_code': status_code,
        }, safe=False)


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
    function = models.ForeignKey(BaseAPIFunction, related_name='executions',
                                 blank=True, null=True, on_delete=models.SET_NULL)

    # For function calls from built-in tools like code_interpreter that won't have a FK to the BaseAPIFunction
    function_name = models.CharField(max_length=50)

    arguments = models.JSONField(default=dict, blank=True)
    result = models.JSONField(default=dict, blank=True)

    status_code = models.CharField(max_length=5, blank=True, null=True)
    error_message = models.TextField(blank=True, null=True)

    time = models.DateTimeField()

    def __str__(self):
        return f"Execution of {self.function.name if self.function else self.function_name} at {self.time}"
