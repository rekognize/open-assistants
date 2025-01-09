import json
import logging

from asgiref.sync import async_to_sync
from django.contrib.auth import authenticate, login
from django.contrib import messages
from django import forms
from django.db.models import Count, Min, Max, Q
from django.http import JsonResponse, HttpResponse, HttpResponseNotFound
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import TemplateView
from openai import OpenAIError

from .models import Project, SharedLink, Thread
from .utils import format_time
from ..api.utils import APIError, aget_openai_client
from ..tools import FUNCTION_DEFINITIONS

logger = logging.getLogger(__name__)


class LoginForm(forms.Form):
    username = forms.CharField(max_length=150, widget=forms.TextInput(attrs={'class': 'form-control'}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control'}))


def login_view(request):
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                return redirect('home')
            else:
                messages.error(request, 'Invalid username or password.')
    else:
        form = LoginForm()
    return render(request, 'login.html', {'form': form})


class HomeView(TemplateView):
    template_name = 'home.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        request = self.request
        project_uuid = self.kwargs.get('project_uuid', '')

        if project_uuid:
            if request.user.is_staff:
                selected_project = get_object_or_404(Project, uuid=project_uuid)
            else:
                selected_project = get_object_or_404(Project, uuid=project_uuid, users=request.user)

            context['selected_project'] = selected_project

        return context


@login_required
def manage_assistants(request, project_uuid):
    if request.user.is_staff:
        selected_project = get_object_or_404(Project, uuid=project_uuid)
    else:
        selected_project = get_object_or_404(Project, uuid=project_uuid, users=request.user)

    return render(request, "manage.html", {
        'function_definitions_json': json.dumps(FUNCTION_DEFINITIONS),
        'active_nav': 'manage',
        'selected_project': selected_project,
    })


@login_required
def analytics(request, project_uuid):
    if request.user.is_staff:
        selected_project = get_object_or_404(Project, uuid=project_uuid)
    else:
        selected_project = get_object_or_404(Project, uuid=project_uuid, users=request.user)

    return render(request, "analytics.html", {
        'active_nav': 'analytics',
        'selected_project': selected_project,
    })


# Analytics

@login_required
def get_assistant_threads(request):
    try:
        # Parse the JSON body to get assistant IDs
        body = json.loads(request.body)
        assistant_ids = body.get("assistant_ids", [])

        if not assistant_ids:
            return JsonResponse({}, status=200)

        # Fetch thread data for the given assistant IDs
        assistant_threads = (
            Thread.objects.filter(metadata__has_key="_asst")
            .filter(metadata___asst__in=assistant_ids)
            .values("metadata")
            .annotate(
                total_thread_count=Count("uuid"),
                shared_thread_count=Count("uuid", filter=Q(shared_link__isnull=False)),
                not_shared_thread_count=Count("uuid", filter=Q(shared_link__isnull=True)),
                first_thread=Min("created_at"),
                last_thread=Max("created_at"),
            )
        )

        thread_data = {}
        for item in assistant_threads:
            assistant_id = item["metadata"]["_asst"]
            thread_data[assistant_id] = {
                "thread_count": {
                    "shared": item["shared_thread_count"],
                    "not_shared": item["not_shared_thread_count"],
                    "total": item["total_thread_count"],
                },
                "first_thread": item["first_thread"],
                "last_thread": item["last_thread"],
            }

        return JsonResponse(thread_data, status=200)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@login_required
def list_threads(request):
    if request.method != "POST":
        return JsonResponse({"error": "POST request required."}, status=400)

    try:
        body = json.loads(request.body)
        assistant_ids = body.get("assistant_ids", [])
        if not assistant_ids:
            return JsonResponse({"threads": []}, status=200)

        threads_qs = (
            Thread.objects
            .filter(metadata___asst__in=assistant_ids)
            .select_related('shared_link')
            .order_by('-created_at')
        )

        threads_data = []
        for t in threads_qs:
            created_ts = int(t.created_at.timestamp()) if t.created_at else None

            if t.shared_link:
                name = t.shared_link.name if t.shared_link.name else "Untitled link"
                shared_name = name
            else:
                shared_name = None

            assistant_id = t.metadata.get("_asst") if t.metadata else None

            thread_info = {
                "id": str(t.openai_id),
                "created_at": created_ts,
                "assistant_id": assistant_id,
                "shared_link_name": shared_name,
            }
            threads_data.append(thread_info)

        return JsonResponse({"threads": threads_data}, status=200)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


# Threads

def create_db_thread(request):
    try:
        data_str = request.body.decode('utf-8')
        data = json.loads(data_str)
    except Exception as e:
        return JsonResponse({"error": f"Invalid JSON: {str(e)}"}, status=400)

    openai_id = data.get("openai_id")
    created_at = data.get("created_at")
    metadata = data.get("metadata", {})
    shared_link_token = request.headers.get("X-Token")

    # Validate required field
    if not openai_id:
        return JsonResponse({"error": "openai_id is required"}, status=400)

    # Fetch the SharedLink if a token is provided
    shared_link = None
    if shared_link_token:
        shared_link = SharedLink.objects.filter(token=shared_link_token).first()
        if not shared_link:
            return JsonResponse({"error": "Invalid token"}, status=400)

    # Check if user is authenticated
    user_id = None
    if request.user and request.user.is_authenticated:
        user_id = request.user.id

    # Create the thread in DB
    thread = Thread(
        openai_id=openai_id,
        created_at=format_time(created_at),
        metadata=metadata,
        shared_link=shared_link,
    )

    if user_id:
        thread.user_id = user_id

    thread.save()

    return JsonResponse({
        "uuid": str(thread.uuid),
        "openai_id": thread.openai_id,
        "created_at": thread.created_at,
        "metadata": thread.metadata,
        "shared_link_token": str(thread.shared_link.token) if thread.shared_link else None,
        "user": user_id or None
    }, status=201)


# Chat

def serve_image_file(request, file_id):
    try:
        image_binary = async_to_sync(fetch_image_binary)(request, file_id)
        return HttpResponse(image_binary, content_type='image/png')
    except APIError as e:
        return JsonResponse({"error": e.message}, status=e.status)
    except OpenAIError as e:
        logger.error(f"Error fetching image file: {e}")
        return HttpResponseNotFound('Image not found')


async def fetch_image_binary(request, file_id):
    client = await aget_openai_client(request)
    content_response = await client.files.content(file_id)
    image_binary = content_response.read()
    return image_binary


@login_required
def thread_detail(request, project_uuid):
    if request.user.is_staff:
        selected_project = get_object_or_404(Project, uuid=project_uuid)
    else:
        selected_project = get_object_or_404(Project, uuid=project_uuid, users=request.user)

    return render(request, "chat/chat.html", {
        'assistant_id': request.GET.get('a'),
        'selected_project': selected_project,
        'is_shared_thread': False,
    })


def shared_thread_detail(request, shared_token):
    shared_link = get_object_or_404(SharedLink, token=shared_token)
    assistant_id = shared_link.assistant_id

    # Initial context
    context = {
        'assistant_id': assistant_id,
        'shared_token': shared_token,
        'is_shared_thread': True,
    }

    return render(request, 'chat/chat.html', context)
