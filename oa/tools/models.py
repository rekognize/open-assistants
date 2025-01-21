import requests
from django.db import models


class Tool(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField()

    # API endpoint definition
    endpoint = models.URLField()
    method = models.CharField(max_length=10, choices=(((m, m) for m in ['GET', 'POST', 'PUT', 'DELETE'])))
    bearer_token = models.CharField(max_length=100, blank=True, null=True)

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
        for parameter in self.parameter_set.all():
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

        try:
            if self.method == 'GET':
                response = requests.get(self.endpoint, headers=headers, params=kwargs)
            else:  # POST, PUT, DELETE
                response = requests.request(
                    method=self.method,
                    url=self.endpoint,
                    headers=headers,
                    json=kwargs
                )

            response.raise_for_status()  # Raise an error for HTTP error responses
            return response.json()
        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"API request failed: {e}")


class Parameter(models.Model):
    tool = models.ForeignKey(Tool, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    type = models.CharField(max_length=1, choices=(
        ('s', 'string'),
        ('i', 'integer'),
        ('o', 'object'),
    ))
    description = models.TextField()
    required = models.BooleanField(default=False)

    def __str__(self):
        return f'{self.tool.name}::{self.name}'
