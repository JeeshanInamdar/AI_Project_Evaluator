from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.mail import send_mail
from django.conf import settings
from django.db import transaction
from .models import ProjectTeam, TeamMember, Project
from accounts.models import Student
import json


# ============= FACULTY - TEAM MANAGEMENT =============

@login_required
def create_team(request):
    """Create a new project team"""
    if request.user.user_type != 'faculty':
        messages.error(request, 'Access denied. Faculty only.')
        return redirect('dashboard')

    if request.method == 'POST':
        team_name = request.POST.get('team_name')
        faculty = request.user.faculty_profile

        try:
            team = ProjectTeam.objects.create(
                team_name=team_name,
                faculty=faculty
            )
            messages.success(request, f'Team "{team_name}" created successfully!')
            return redirect('team_detail', team_id=team.id)
        except Exception as e:
            messages.error(request, f'Error creating team: {str(e)}')

    return render(request, 'projects/create_team.html')


@login_required
def team_detail(request, team_id):
    """View and manage team details"""
    if request.user.user_type != 'faculty':
        messages.error(request, 'Access denied. Faculty only.')
        return redirect('dashboard')

    try:
        team = get_object_or_404(ProjectTeam, id=team_id, faculty=request.user.faculty_profile)
        members = TeamMember.objects.filter(team=team).select_related('student')

        # Get students not in this team for adding
        existing_student_ids = [member.student.id for member in members]
        available_students = Student.objects.exclude(id__in=existing_student_ids)

        # Check if project exists
        try:
            project = team.project
        except Project.DoesNotExist:
            project = None

        context = {
            'team': team,
            'members': members,
            'available_students': available_students,
            'project': project,
        }

        return render(request, 'projects/team_detail.html', context)

    except Exception as e:
        messages.error(request, f'Error loading team details: {str(e)}')
        return redirect('faculty_dashboard')


@login_required
def add_team_member(request, team_id):
    """Add a student to team using USN"""
    if request.user.user_type != 'faculty':
        messages.error(request, 'Access denied.')
        return redirect('dashboard')

    team = get_object_or_404(ProjectTeam, id=team_id, faculty=request.user.faculty_profile)

    if request.method == 'POST':
        usn = request.POST.get('usn').strip().upper()

        # Check if team already has 4 members
        current_members = TeamMember.objects.filter(team=team).count()
        if current_members >= 4:
            messages.error(request, 'Team already has 4 members.')
            return redirect('team_detail', team_id=team_id)

        try:
            student = Student.objects.get(usn=usn)

            # Check if student is already in this team
            if TeamMember.objects.filter(team=team, student=student).exists():
                messages.error(request, f'Student {usn} is already in this team.')
                return redirect('team_detail', team_id=team_id)

            # Add member
            TeamMember.objects.create(
                team=team,
                student=student,
                is_leader=False
            )

            messages.success(request, f'Student {student.full_name} ({usn}) added to team.')

        except Student.DoesNotExist:
            messages.error(request, f'Student with USN {usn} not found.')
        except Exception as e:
            messages.error(request, f'Error adding member: {str(e)}')

    return redirect('team_detail', team_id=team_id)


@login_required
def set_team_leader(request, team_id, student_id):
    """Set a team member as leader and generate credentials"""
    if request.user.user_type != 'faculty':
        messages.error(request, 'Access denied.')
        return redirect('dashboard')

    try:
        print(f"DEBUG: Setting leader - team_id: {team_id}, student_id: {student_id}")

        team = get_object_or_404(ProjectTeam, id=team_id, faculty=request.user.faculty_profile)
        student = get_object_or_404(Student, id=student_id)
        member = get_object_or_404(TeamMember, team=team, student=student)

        print(f"DEBUG: Found team member {student.full_name}")

        with transaction.atomic():
            print('DEBUG: Inside leader update block')

            # Set the selected member as the new leader
            member.is_leader = True
            member.save()
            print(f"DEBUG: {member.student.full_name} marked as new leader")

            # Update the team’s leader field
            team.leader = member.student
            team.save()
            print(f"DEBUG: Team leader updated to {team.leader.full_name}")

            # Send leader credentials email
            try:
                send_leader_credentials_email(team, member.student)
                messages.success(
                    request,
                    f'{member.student.full_name} is now the team leader. Credentials sent to {member.student.user.email}'
                )
                print("DEBUG: Email sent successfully")
            except Exception as email_error:
                print(f"DEBUG: Email error: {email_error}")
                messages.warning(
                    request,
                    f'{member.student.full_name} is now the team leader, but email sending failed: {email_error}'
                )

    except Exception as e:
        import traceback
        print(f"DEBUG: Exception occurred: {type(e).__name__}")
        print(f"DEBUG: Message: {e}")
        print(f"DEBUG: Traceback:\n{traceback.format_exc()}")
        messages.error(request, f'Error setting leader: {e}')

    return redirect('team_detail', team_id=team_id)


@login_required
def remove_team_member(request, team_id, member_id):
    """Remove a member from team"""
    if request.user.user_type != 'faculty':
        messages.error(request, 'Access denied.')
        return redirect('dashboard')

    team = get_object_or_404(ProjectTeam, id=team_id, faculty=request.user.faculty_profile)

    try:
        member = get_object_or_404(TeamMember, id=member_id, team=team)
        student_name = member.student.full_name

        # If removing leader, clear team leader
        if member.is_leader:
            team.leader = None
            team.leader_username = None
            team.leader_password = None
            team.save()

        member.delete()
        messages.success(request, f'{student_name} removed from team.')

    except Exception as e:
        messages.error(request, f'Error removing member: {str(e)}')

    return redirect('team_detail', team_id=team_id)


def send_leader_credentials_email(team, student):
    """Send login credentials to team leader"""
    subject = f'Project Leader Credentials - {team.team_name}'

    # Build the login URL
    from django.contrib.sites.shortcuts import get_current_site
    from django.conf import settings

    # Use localhost for development
    domain = 'localhost:8000' if settings.DEBUG else 'your-domain.com'
    login_url = f"http://{domain}/projects/leader/login/"

    message = f"""Dear {student.full_name},

You have been assigned as the leader for the project team: {team.team_name}

Your login credentials for project submission are:

Username: {team.leader_username}
Password: {team.leader_password}

Please use these credentials to login and submit your project.

Login URL: {login_url}

Faculty: {team.faculty.full_name}
Department: {team.faculty.department}

Best regards,
AI Project Evaluator System
"""

    try:
        from django.core.mail import send_mail

        print(f"DEBUG: Attempting to send email to {student.user.email}")
        print(f"DEBUG: EMAIL_HOST_USER: {settings.EMAIL_HOST_USER}")
        print(f"DEBUG: DEFAULT_FROM_EMAIL: {settings.DEFAULT_FROM_EMAIL}")

        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [student.user.email],
            fail_silently=False,
        )
        print(f"DEBUG: Email sent successfully")
        return True
    except Exception as e:
        print(f"DEBUG: Email sending failed: {type(e).__name__}: {str(e)}")
        # Don't raise the exception, just log it
        return False


# ============= LEADER - PROJECT SUBMISSION =============

def leader_login(request):
    """Leader login for project submission"""
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        try:
            team = ProjectTeam.objects.get(leader_username=username)

            if team.leader_password == password:  # In production, use hashing
                request.session['leader_team_id'] = str(team.id)
                messages.success(request, f'Welcome, {team.leader.full_name}!')
                return redirect('leader_dashboard')
            else:
                messages.error(request, 'Invalid credentials.')
        except ProjectTeam.DoesNotExist:
            messages.error(request, 'Invalid credentials.')

    return render(request, 'projects/leader_login.html')


def leader_logout(request):
    """Leader logout"""
    if 'leader_team_id' in request.session:
        del request.session['leader_team_id']
    messages.success(request, 'Logged out successfully.')
    return redirect('leader_login')


def leader_dashboard(request):
    """Leader dashboard"""
    team_id = request.session.get('leader_team_id')
    if not team_id:
        messages.error(request, 'Please login first.')
        return redirect('leader_login')

    team = get_object_or_404(ProjectTeam, id=team_id)

    # Get project if exists
    project = None
    try:
        project = team.project
    except Project.DoesNotExist:
        pass

    context = {
        'team': team,
        'project': project,
        'members': TeamMember.objects.filter(team=team).select_related('student'),
    }

    return render(request, 'projects/leader_dashboard.html', context)


def submit_project(request):
    """Submit or update project"""
    team_id = request.session.get('leader_team_id')
    if not team_id:
        messages.error(request, 'Please login first.')
        return redirect('leader_login')

    team = get_object_or_404(ProjectTeam, id=team_id)

    if request.method == 'POST':
        project_name = request.POST.get('project_name')
        github_link = request.POST.get('github_link')
        project_report = request.FILES.get('project_report')

        try:
            # Check if project already exists
            project, created = Project.objects.get_or_create(
                team=team,
                defaults={
                    'project_name': project_name,
                    'github_link': github_link,
                    'status': 'submitted'
                }
            )

            if not created:
                # Update existing project
                project.project_name = project_name
                project.github_link = github_link
                project.status = 'submitted'

            # Update report if provided
            if project_report:
                project.project_report = project_report

            project.save()

            if created:
                messages.success(request, 'Project submitted successfully!')
            else:
                messages.success(request, 'Project updated successfully!')

            return redirect('leader_dashboard')

        except Exception as e:
            messages.error(request, f'Error submitting project: {str(e)}')

    return render(request, 'projects/submit_project.html', {'team': team})


def edit_project(request, project_id):
    """Edit existing project"""
    team_id = request.session.get('leader_team_id')
    if not team_id:
        messages.error(request, 'Please login first.')
        return redirect('leader_login')

    team = get_object_or_404(ProjectTeam, id=team_id)
    project = get_object_or_404(Project, id=project_id, team=team)

    if request.method == 'POST':
        project.project_name = request.POST.get('project_name')
        project.github_link = request.POST.get('github_link')

        if request.FILES.get('project_report'):
            project.project_report = request.FILES.get('project_report')

        project.save()
        messages.success(request, 'Project updated successfully!')
        return redirect('leader_dashboard')

    context = {
        'team': team,
        'project': project,
    }

    return render(request, 'projects/edit_project.html', context)


# ============= FACULTY - VIEW PROJECTS =============

@login_required
def view_project(request, project_id):
    """View project details"""
    if request.user.user_type != 'faculty':
        messages.error(request, 'Access denied.')
        return redirect('dashboard')

    project = get_object_or_404(Project, id=project_id, team__faculty=request.user.faculty_profile)
    members = TeamMember.objects.filter(team=project.team).select_related('student')

    # Get evaluation if exists
    evaluation = None
    try:
        evaluation = project.evaluation
    except:
        pass

    context = {
        'project': project,
        'team': project.team,
        'members': members,
        'evaluation': evaluation,
    }

    return render(request, 'projects/view_project.html', context)