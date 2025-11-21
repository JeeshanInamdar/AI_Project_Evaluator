from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from .models import User, Faculty, Student
from projects.models import ProjectTeam, TeamMember, Project
from evaluations.models import ProjectEvaluation


def home(request):
    """Home page"""
    return render(request, 'home.html')


def user_login(request):
    """Universal login for all users"""
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')

        user = authenticate(request, username=email, password=password)

        if user is not None:
            login(request, user)
            messages.success(request, f'Welcome back, {email}!')
            return redirect('dashboard')
        else:
            messages.error(request, 'Invalid email or password.')

    return render(request, 'accounts/login.html')


def user_logout(request):
    """Logout user"""
    logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('home')


@login_required
def dashboard_redirect(request):
    """Redirect to appropriate dashboard based on user type"""
    if request.user.user_type == 'faculty':
        return redirect('faculty_dashboard')
    elif request.user.user_type == 'student':
        return redirect('student_dashboard')
    else:
        messages.error(request, 'Invalid user type.')
        return redirect('home')


# ============= FACULTY VIEWS =============

def faculty_register(request):
    """Faculty registration"""
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        # Get form data
        email = request.POST.get('email')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')
        faculty_id = request.POST.get('faculty_id')
        full_name = request.POST.get('full_name')
        department = request.POST.get('department')
        designation = request.POST.get('designation')
        phone = request.POST.get('phone')

        # Validation
        if password != confirm_password:
            messages.error(request, 'Passwords do not match.')
            return render(request, 'accounts/faculty_register.html')

        if User.objects.filter(email=email).exists():
            messages.error(request, 'Email already registered.')
            return render(request, 'accounts/faculty_register.html')

        if Faculty.objects.filter(faculty_id=faculty_id).exists():
            messages.error(request, 'Faculty ID already exists.')
            return render(request, 'accounts/faculty_register.html')

        try:
            with transaction.atomic():
                # Create user
                user = User.objects.create_user(
                    email=email,
                    password=password,
                    user_type='faculty'
                )

                # Create faculty profile
                Faculty.objects.create(
                    user=user,
                    faculty_id=faculty_id,
                    full_name=full_name,
                    department=department,
                    designation=designation,
                    phone=phone
                )

                messages.success(request, 'Registration successful! Please login.')
                return redirect('login')

        except Exception as e:
            messages.error(request, f'Registration failed: {str(e)}')

    return render(request, 'accounts/faculty_register.html')


@login_required
def faculty_dashboard(request):
    """Faculty dashboard"""
    if request.user.user_type != 'faculty':
        messages.error(request, 'Access denied. Faculty only.')
        return redirect('dashboard')

    faculty = request.user.faculty_profile
    teams = ProjectTeam.objects.filter(faculty=faculty).order_by('-created_at')

    # Get projects statistics
    total_teams = teams.count()
    submitted_projects = Project.objects.filter(team__faculty=faculty).count()
    evaluated_projects = ProjectEvaluation.objects.filter(faculty=faculty,
                                                          ai_marks__isnull=False,
                                                          faculty_marks__isnull=False).count()

    context = {
        'faculty': faculty,
        'teams': teams,
        'total_teams': total_teams,
        'submitted_projects': submitted_projects,
        'evaluated_projects': evaluated_projects,
    }

    return render(request, 'accounts/faculty_dashboard.html', context)


@login_required
def faculty_profile(request):
    """Faculty profile"""
    if request.user.user_type != 'faculty':
        messages.error(request, 'Access denied.')
        return redirect('dashboard')

    faculty = request.user.faculty_profile

    if request.method == 'POST':
        faculty.full_name = request.POST.get('full_name')
        faculty.department = request.POST.get('department')
        faculty.designation = request.POST.get('designation')
        faculty.phone = request.POST.get('phone')
        faculty.save()

        messages.success(request, 'Profile updated successfully.')
        return redirect('faculty_profile')

    return render(request, 'accounts/faculty_profile.html', {'faculty': faculty})


# ============= STUDENT VIEWS =============

def student_register(request):
    """Student registration"""
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        # Get form data
        email = request.POST.get('email')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')
        usn = request.POST.get('usn')
        full_name = request.POST.get('full_name')
        department = request.POST.get('department')
        semester = request.POST.get('semester')
        phone = request.POST.get('phone')

        # Validation
        if password != confirm_password:
            messages.error(request, 'Passwords do not match.')
            return render(request, 'accounts/student_register.html')

        if User.objects.filter(email=email).exists():
            messages.error(request, 'Email already registered.')
            return render(request, 'accounts/student_register.html')

        if Student.objects.filter(usn=usn).exists():
            messages.error(request, 'USN already exists.')
            return render(request, 'accounts/student_register.html')

        try:
            with transaction.atomic():
                # Create user
                user = User.objects.create_user(
                    email=email,
                    password=password,
                    user_type='student'
                )

                # Create student profile
                Student.objects.create(
                    user=user,
                    usn=usn,
                    full_name=full_name,
                    department=department,
                    semester=int(semester),
                    phone=phone
                )

                messages.success(request, 'Registration successful! Please login.')
                return redirect('login')

        except Exception as e:
            messages.error(request, f'Registration failed: {str(e)}')

    return render(request, 'accounts/student_register.html')


@login_required
def student_dashboard(request):
    """Student dashboard"""
    if request.user.user_type != 'student':
        messages.error(request, 'Access denied. Students only.')
        return redirect('dashboard')

    student = request.user.student_profile

    # Get student's teams
    team_memberships = TeamMember.objects.filter(student=student).select_related('team')
    teams = [membership.team for membership in team_memberships]

    # Get projects where student is a member
    projects = Project.objects.filter(team__in=teams)

    context = {
        'student': student,
        'teams': teams,
        'projects': projects,
        'team_memberships': team_memberships,
    }

    return render(request, 'accounts/student_dashboard.html', context)


@login_required
def student_profile(request):
    """Student profile"""
    if request.user.user_type != 'student':
        messages.error(request, 'Access denied.')
        return redirect('dashboard')

    student = request.user.student_profile

    if request.method == 'POST':
        student.full_name = request.POST.get('full_name')
        student.department = request.POST.get('department')
        student.semester = int(request.POST.get('semester'))
        student.phone = request.POST.get('phone')
        student.save()

        messages.success(request, 'Profile updated successfully.')
        return redirect('student_profile')

    return render(request, 'accounts/student_profile.html', {'student': student})


@login_required
def student_results(request):
    """View project evaluation results"""
    if request.user.user_type != 'student':
        messages.error(request, 'Access denied.')
        return redirect('dashboard')

    student = request.user.student_profile

    # Get all teams student is part of
    team_memberships = TeamMember.objects.filter(student=student).select_related('team')
    teams = [membership.team for membership in team_memberships]

    # Get evaluated projects
    results = []
    for team in teams:
        try:
            project = team.project
            if hasattr(project, 'evaluation'):
                evaluation = project.evaluation
                if evaluation.is_fully_evaluated:
                    results.append({
                        'team': team,
                        'project': project,
                        'evaluation': evaluation,
                        'student': student,
                    })
        except Project.DoesNotExist:
            continue

    context = {
        'student': student,
        'results': results,
    }

    return render(request, 'accounts/student_results.html', context)