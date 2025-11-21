from django.db import models
from projects.models import Project
from accounts.models import Faculty
from django.utils import timezone
import uuid
import json


class EvaluationCriteria(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    faculty = models.ForeignKey(Faculty, on_delete=models.CASCADE, related_name='evaluation_criteria')
    criteria_name = models.CharField(max_length=200)
    criteria_description = models.TextField()
    max_marks = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = 'Evaluation Criteria'

    def __str__(self):
        return f"{self.criteria_name} - {self.faculty.full_name}"


class ProjectEvaluation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.OneToOneField(Project, on_delete=models.CASCADE, related_name='evaluation')
    faculty = models.ForeignKey(Faculty, on_delete=models.CASCADE)

    # AI Evaluation - Changed to FloatField to avoid Decimal issues
    ai_marks = models.FloatField(null=True, blank=True)
    ai_feedback = models.TextField(blank=True, null=True)
    ai_evaluated_at = models.DateTimeField(null=True, blank=True)

    # Faculty Evaluation - Changed to FloatField to avoid Decimal issues
    faculty_marks = models.FloatField(null=True, blank=True)
    faculty_feedback = models.TextField(blank=True, null=True)
    faculty_evaluated_at = models.DateTimeField(null=True, blank=True)

    # Criteria used for evaluation
    evaluation_criteria = models.TextField(help_text='JSON string of criteria used')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Evaluation - {self.project.project_name}"

    @property
    def is_fully_evaluated(self):
        return self.ai_marks is not None and self.faculty_marks is not None