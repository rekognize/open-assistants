import requests
import httpx
from django.db import models
from django.utils.text import slugify


class Function(models.Model):
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
    function = models.ForeignKey(Function, on_delete=models.CASCADE, related_name="parameters")
    name = models.CharField(max_length=100)
    type = models.CharField(max_length=1, choices=(
        ('o', 'object'),
        ('s', 'string'),
        ('n', 'number'),
        ('b', 'boolean'),
        ('-', 'null'),
    ))
    description = models.TextField()
    required = models.BooleanField(default=False)

    def __str__(self):
        return f'{self.function.name}::{self.name}'
