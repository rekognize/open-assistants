import os
import random
import string
import requests
from django.db import models
from django.contrib.auth.models import User
from oa.main.models import Project


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    subscription = models.CharField(max_length=1, choices=(
        ('f', 'Free'),
        ('p', 'Pro'),
        ('e', 'Enterprise'),
    ), default='f')
    cloud_service_keys = models.JSONField(default=dict, blank=True)  # {'s3': 'ABC123'}

    def __str__(self):
        return self.user.username

    def assign_project(self):
        project = Project.objects.filter(is_oa_project=True).filter(user__isnull=True).first()
        if project:
            project.user = self.user
            project.save()
        else:
            openai_admin_key = os.getenv('OPENAI_ADMIN_KEY')

            url = "https://api.openai.com/v1/organization/projects"
            headers = {
                "Authorization": f"Bearer {openai_admin_key}",
                "Content-Type": "application/json"
            }
            payload = {
                "name": f"OA-{''.join(random.choices(string.ascii_uppercase, k=4))}"
            }
            response = requests.post(url, headers=headers, json=payload)
            if response.status_code == 201:  # Created successfully
                data = response.json()
                project = Project.objects.create(
                    user=project.user,
                    name=data.name,
                    key=data.id,
                    is_oa_project=True,
                )

        return project
