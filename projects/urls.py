from django.urls import path
from . import views

urlpatterns = [
    # Faculty - Team Management
    path('team/create/', views.create_team, name='create_team'),
    path('team/<uuid:team_id>/', views.team_detail, name='team_detail'),
    path('team/<uuid:team_id>/add-member/', views.add_team_member, name='add_team_member'),
    path('team/<uuid:team_id>/set-leader/<int:student_id>/', views.set_team_leader, name='set_team_leader'),
    path('team/<uuid:team_id>/remove-member/<int:member_id>/', views.remove_team_member, name='remove_team_member'),

    # Leader - Project Submission
    path('leader/login/', views.leader_login, name='leader_login'),
    path('leader/logout/', views.leader_logout, name='leader_logout'),
    path('leader/dashboard/', views.leader_dashboard, name='leader_dashboard'),
    path('leader/submit/', views.submit_project, name='submit_project'),
    path('leader/edit/<uuid:project_id>/', views.edit_project, name='edit_project'),

    # Faculty - View Projects
    path('view/<uuid:project_id>/', views.view_project, name='view_project'),
]