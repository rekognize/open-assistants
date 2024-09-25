import json

from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404
from django.views.generic import TemplateView

from .models import Project


class HomeView(TemplateView):
    template_name = 'home.html'


@login_required
def manage_assistants(request):
    return render(request, "manage.html")


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
