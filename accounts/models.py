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
            pass
        return project
