from django.urls import path
from . import views

urlpatterns = [
    # Authentication
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),

    # Faculty Registration and Dashboard
    path('faculty/register/', views.faculty_register, name='faculty_register'),
    path('faculty/dashboard/', views.faculty_dashboard, name='faculty_dashboard'),
    path('faculty/profile/', views.faculty_profile, name='faculty_profile'),

    # Student Registration and Dashboard
    path('student/register/', views.student_register, name='student_register'),
    path('student/dashboard/', views.student_dashboard, name='student_dashboard'),
    path('student/profile/', views.student_profile, name='student_profile'),
    path('student/results/', views.student_results, name='student_results'),

    # General Dashboard
    path('dashboard/', views.dashboard_redirect, name='dashboard'),
]