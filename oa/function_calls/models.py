import requests
from django.db import models


class Function(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField()

    # API endpoint definition
    endpoint = models.URLField(blank=True, null=True)
    method = models.CharField(
        max_length=10, default='GET',
        choices=[(m, m) for m in ['GET', 'POST', 'PUT', 'DELETE']],
    )
    bearer_token = models.CharField(max_length=200, blank=True, null=True)

    def get_description(self):
        json_description = {
            "name": self.name,
            "description": self.description,
            "strict": True,
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
        for parameter in self.parameters.all():
            json_description["parameters"]["properties"][parameter.name] = {
                "type": parameter.get_type_display(),
                "description": parameter.description
            }
            if parameter.required:
                json_description["parameters"]["required"].append(parameter.name)
        return json_description

    def execute(self, **kwargs):
        headers = {}
        if self.bearer_token:
            headers["Authorization"] = f"Bearer {self.bearer_token}"

        # Determine the endpoint (allowing URL override as a parameter)
        url = kwargs.pop('url', self.endpoint)
        if not url:
            raise ValueError("No endpoint URL provided.")

        try:
            if self.method == 'GET':
                response = requests.get(self.endpoint, headers=headers, params=kwargs)
            else:  # POST, PUT, DELETE
                response = requests.request(
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

        except requests.exceptions.RequestException as e:
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
