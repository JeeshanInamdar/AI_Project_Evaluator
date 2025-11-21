from django.urls import path
from . import views

urlpatterns = [
    # Evaluation Criteria Management
    path('criteria/', views.manage_criteria, name='manage_criteria'),
    path('criteria/create/', views.create_criteria, name='create_criteria'),
    path('criteria/<uuid:criteria_id>/edit/', views.edit_criteria, name='edit_criteria'),
    path('criteria/<uuid:criteria_id>/delete/', views.delete_criteria, name='delete_criteria'),

    # Project Evaluation
    path('evaluate/<uuid:project_id>/', views.evaluate_project, name='evaluate_project'),
    path('ai-evaluate/<uuid:project_id>/', views.ai_evaluate_project, name='ai_evaluate_project'),
    path('faculty-evaluate/<uuid:project_id>/', views.faculty_evaluate_project, name='faculty_evaluate_project'),

    # View Evaluation Results
    path('results/<uuid:project_id>/', views.evaluation_results, name='evaluation_results'),
]