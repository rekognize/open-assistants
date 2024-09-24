from oa.main.models import Project


def user_projects(request):
    if not request.user.is_authenticated:
        return {}

    projects = Project.objects.filter(user=request.user)

    # Retrieve the selected project ID from the session
    selected_project_id = request.session.get('selected_project_id')
    selected_project = None

    if selected_project_id:
        try:
            selected_project = projects.get(id=int(selected_project_id))
        except (ValueError, Project.DoesNotExist):
            selected_project = None
    else:
        # If no project selected, use the first project
        selected_project = projects.first()

    return {
        'user_projects': projects,
        'selected_project': selected_project,
    }
