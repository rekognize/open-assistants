from datetime import datetime

import requests
from django.contrib.auth import get_user
from openai import OpenAI
from oa.api.utils import APIError
from oa.main.models import Project


def format_time(timestamp):
    return datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')


def verify_openai_key(key):
    url = 'https://api.openai.com/v1/models'
    headers = {
        'Authorization': f'Bearer {key}',
    }
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            return True, None
        else:
            error_data = response.json()
            error_message = error_data.get('error', {}).get('message', 'Invalid API key.')
            return False, error_message
    except requests.RequestException:
        return False, 'Failed to verify the key due to a network error.'
