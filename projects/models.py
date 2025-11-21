from django.db import models
from accounts.models import Faculty, Student
import uuid
import secrets
import string

def generate_leader_credentials():
    """Generate random login credentials for project leader"""
    username = 'leader_' + ''.join(secrets.choice(string.ascii_lowercase + string.digits) for _ in range(8))
    password = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(12))
    return username, password


class ProjectTeam(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    team_name = models.CharField(max_length=200)
    faculty = models.ForeignKey(Faculty, on_delete=models.CASCADE, related_name='project_teams')
    leader = models.ForeignKey(Student, on_delete=models.SET_NULL, null=True, blank=True, related_name='led_teams')
    leader_username = models.CharField(max_length=50, unique=True, blank=True, null=True)
    leader_password = models.CharField(max_length=100, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.team_name} - {self.faculty.full_name}"

    def save(self, *args, **kwargs):
        # Generate credentials when leader is assigned and credentials don't exist
        if self.leader and not self.leader_username:
            username, password = generate_leader_credentials()
            self.leader_username = username
            self.leader_password = password
        super().save(*args, **kwargs)


class TeamMember(models.Model):
    team = models.ForeignKey(ProjectTeam, on_delete=models.CASCADE, related_name='members')
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    is_leader = models.BooleanField(default=False)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('team', 'student')

    def __str__(self):
        return f"{self.student.full_name} - {self.team.team_name}"


class Project(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('submitted', 'Submitted'),
        ('evaluated', 'Evaluated'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    team = models.OneToOneField(ProjectTeam, on_delete=models.CASCADE, related_name='project')
    project_name = models.CharField(max_length=300)
    project_report = models.FileField(upload_to='project_reports/')
    github_link = models.URLField(max_length=500)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    submitted_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.project_name} - {self.team.team_name}"