import json
import logging

from django.contrib.auth import authenticate, login
from django.contrib import messages
from django import forms
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import TemplateView
from ..function_calls.models import ExternalAPIFunction, LocalAPIFunction
from .models import Project, SharedLink, Thread
from .utils import format_time

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
def manage_overview(request, project_uuid):
    if request.user.is_staff:
        selected_project = get_object_or_404(Project, uuid=project_uuid)
    else:
        selected_project = get_object_or_404(Project, uuid=project_uuid, users=request.user)

    function_definitions = ([f.get_definition() for f in LocalAPIFunction.objects.all()] +
                            [f.get_definition() for f in ExternalAPIFunction.objects.all()])

    return render(request, "manage/overview.html", {
        'function_definitions_json': json.dumps(function_definitions),
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


# Threads

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
