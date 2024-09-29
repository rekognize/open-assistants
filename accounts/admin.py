from django.contrib import admin
from .models import Profile


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'cloud_service_keys')
    search_fields = ('user__username',)
    list_filter = ('user__is_active', 'user__is_staff')
