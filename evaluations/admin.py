from django.contrib import admin
from .models import EvaluationCriteria, ProjectEvaluation

@admin.register(EvaluationCriteria)
class EvaluationCriteriaAdmin(admin.ModelAdmin):
    list_display = ('criteria_name', 'faculty', 'max_marks', 'created_at')
    list_filter = ('faculty', 'created_at')
    search_fields = ('criteria_name', 'faculty__full_name')
    ordering = ('-created_at',)

@admin.register(ProjectEvaluation)
class ProjectEvaluationAdmin(admin.ModelAdmin):
    list_display = ('project', 'faculty', 'ai_marks', 'faculty_marks', 'created_at')
    list_filter = ('faculty', 'created_at')
    search_fields = ('project__project_name', 'faculty__full_name')
    ordering = ('-created_at',)
    readonly_fields = ('created_at', 'updated_at')