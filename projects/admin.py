from django.contrib import admin
from .models import ProjectTeam, TeamMember, Project

@admin.register(ProjectTeam)
class ProjectTeamAdmin(admin.ModelAdmin):
    list_display = ('team_name', 'faculty', 'leader', 'created_at')
    list_filter = ('faculty', 'created_at')
    search_fields = ('team_name', 'faculty__full_name')
    ordering = ('-created_at',)

@admin.register(TeamMember)
class TeamMemberAdmin(admin.ModelAdmin):
    list_display = ('team', 'student', 'is_leader', 'added_at')
    list_filter = ('is_leader', 'added_at')
    search_fields = ('team__team_name', 'student__full_name', 'student__usn')
    ordering = ('-added_at',)

@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ('project_name', 'team', 'status', 'submitted_at')
    list_filter = ('status', 'submitted_at')
    search_fields = ('project_name', 'team__team_name')
    ordering = ('-submitted_at',)
