import asyncio
import base64
import json
import logging
import os

from asgiref.sync import async_to_sync, sync_to_async
from django.contrib.auth import authenticate, login
from django.contrib import messages
from django import forms
from django.db.models import Count, Min, Max, Q
from django.http import JsonResponse, HttpResponse, Http404, HttpResponseNotFound, HttpResponseBadRequest
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from django.utils.translation import gettext as _
from django.views import View
from django.views.generic import TemplateView
from openai import OpenAIError

from .models import Project, SharedLink, Thread
from .utils import format_time, verify_openai_key
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

async def create_db_thread(request):
    try:
        data = await sync_to_async(request.body.decode)('utf-8')
        data = json.loads(data)
    except Exception as e:
        return JsonResponse({"error": f"Invalid JSON: {str(e)}"}, status=400)

    openai_id = data.get("openai_id")
    created_at = data.get("created_at")
    metadata = data.get("metadata", {})

    shared_link_token = request.headers.get('X-Token')

    if not openai_id:
        return JsonResponse({"error": "openai_id is required"}, status=400)

    shared_link = None
    if shared_link_token:
        shared_link = await sync_to_async(SharedLink.objects.filter(token=shared_link_token).first)()
        if not shared_link:
            return JsonResponse({"error": "Invalid token"}, status=400)

    # Create the thread in DB
    thread = Thread(
        openai_id=openai_id,
        created_at=format_time(created_at),
        metadata=metadata,
        shared_link=shared_link
    )
    await sync_to_async(thread.save)()

    return JsonResponse({
        "uuid": str(thread.uuid),
        "openai_id": thread.openai_id,
        "created_at": thread.created_at,
        "metadata": thread.metadata,
        "shared_link_token": str(thread.shared_link.token) if thread.shared_link else None
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


def thread_detail(request, project_uuid):
    if request.user.is_staff:
        selected_project = get_object_or_404(Project, uuid=project_uuid)
    else:
        selected_project = get_object_or_404(Project, uuid=project_uuid, users=request.user)

    return render(request, "chat/chat.html", {
        'assistant_id': request.GET.get('a'),
        'selected_project': selected_project,
    })


# Projects

@login_required
def set_project(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            project_id = data.get('project_id')

            if project_id:
                # Set the selected project ID in the session
                request.session['selected_project_id'] = project_id
                return JsonResponse({'status': 'success'}, status=200)
            else:
                return JsonResponse({'error': 'Invalid project ID'}, status=400)
        except ValueError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)
    return JsonResponse({'error': 'Bad Request'}, status=400)


@login_required
def create_project(request):
    if request.method == "POST":
        name = request.POST.get('name')
        key = request.POST.get('key')

        if not name:
            return JsonResponse({'success': False, 'error': 'Name is required.'})
        if not key:
            return JsonResponse({'success': False, 'error': 'Key is required.'})

        # Verify the key with OpenAI
        is_valid, error_message = verify_openai_key(key)
        if not is_valid:
            return JsonResponse({'success': False, 'error': error_message})

        # Check if the user already has a project with this key
        if Project.objects.filter(user=request.user, key=key).exists():
            return JsonResponse({'success': False, 'error': 'You already have a project with this key.'})

        try:
            project = Project.objects.create(user=request.user, name=name, key=key)
            return JsonResponse({
                'success': True,
                'project': {
                    'id': project.id,
                    'name': project.name,
                    'partial_key': project.get_partial_key()
                }
            })
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})

    return JsonResponse({'success': False, 'error': 'Invalid request method.'})


@login_required
def edit_project(request, project_id):
    if request.method == "POST":
        name = request.POST.get('name')
        key = request.POST.get('key')

        if not name:
            return JsonResponse({'success': False, 'error': 'Name is required.'})

        try:
            project = get_object_or_404(Project, id=project_id, user=request.user)

            # Update the name
            project.name = name

            # Update the key only if it is provided
            if key:
                # Check if another project with the same key exists for the user
                if Project.objects.filter(user=request.user, key=key).exclude(id=project_id).exists():
                    return JsonResponse({'success': False, 'error': 'You already have a project with this key.'})
                project.key = key

            project.save()

            return JsonResponse({
                'success': True,
                'project': {
                    'id': project.id,
                    'name': project.name,
                    'partial_key': project.get_partial_key()
                }
            })
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})

    return JsonResponse({'success': False, 'error': 'Invalid request method.'})


@login_required
def delete_project(request, project_id):
    if request.method == "POST":
        try:
            project = get_object_or_404(Project, id=project_id, user=request.user)
            project.delete()
            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})

    return JsonResponse({'success': False, 'error': 'Invalid request method.'})


# Sharing

@login_required
def share_assistant(request, assistant_id):
    if not request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return HttpResponseBadRequest('Invalid request')

    # Retrieve the selected project
    selected_project_id = request.session.get('selected_project_id') or request.GET.get('selected_project_id')
    selected_project = None

    if selected_project_id:
        try:
            selected_project = Project.objects.get(id=int(selected_project_id), user=request.user)
        except (ValueError, Project.DoesNotExist):
            return JsonResponse({'status': 'error', 'message': _('Invalid project selected.')}, status=400)
    else:
        return JsonResponse({'status': 'error', 'message': _('No project selected.')}, status=400)

    if request.method == 'POST':
        try:
            # Create a new shareable link
            new_link = SharedLink.objects.create(assistant_id=assistant_id, project=selected_project)
            link_url = request.build_absolute_uri(reverse('shared_thread_detail', args=[new_link.token]))
            return JsonResponse({
                'status': 'success',
                'message': _('New shareable link created.'),
                'link': {
                    'token': str(new_link.token),
                    'url': link_url,
                    'created': new_link.created
                }
            })
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

    elif request.method == 'GET':
        links = SharedLink.objects.filter(
            assistant_id=assistant_id,
            project=selected_project,
            project__user=request.user
        ).order_by('-created')

        try:
            if links:
                data = {'links': [{'token': link.token,
                                   'url': request.build_absolute_uri(f'/shared/{link.token}/'),
                                   'name': link.name,
                                   'created': link.created
                                   } for link in links]}
            else:
                data = {'message': _('No links available.')}
            return JsonResponse(data)
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

    return JsonResponse({'status': 'error', 'message': 'Invalid request method.'}, status=400)


@login_required
def delete_shared_link(request, link_token):
    if not request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return HttpResponseBadRequest('Invalid request')

    if request.method == 'POST':
        try:
            link = get_object_or_404(SharedLink, token=link_token, project__user=request.user)
            link.delete()
            return JsonResponse({'status': 'success', 'message': _('Link deleted successfully.')})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

    return JsonResponse({'status': 'error', 'message': 'Invalid request method.'}, status=400)


@login_required
def update_shared_link(request, link_token):
    if request.method != 'POST' or request.headers.get('X-Requested-With') != 'XMLHttpRequest':
        return HttpResponseBadRequest('Invalid request')

    link = get_object_or_404(SharedLink, token=link_token, project__user=request.user)

    name = request.POST.get('name', '').strip()
    link.name = name
    link.save()

    # Build the link URL to return
    link_url = request.build_absolute_uri(reverse('shared_thread_detail', args=[link.token]))

    return JsonResponse({
        'status': 'success',
        'message': _('Link name updated successfully.'),
        'link': {
            'url': link_url
        }
    })


def shared_thread_detail(request, token):
    shared_link = get_object_or_404(SharedLink, token=token)
    assistant_id = shared_link.assistant_id

    # Initial context
    context = {
        'assistant_id': assistant_id,
        'token': token,
        'is_shared_thread': True,
    }

    return render(request, 'chat/chat.html', context)
