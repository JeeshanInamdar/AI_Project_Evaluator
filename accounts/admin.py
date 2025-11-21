from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, Faculty, Student


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('email', 'user_type', 'is_active', 'is_staff', 'date_joined')
    list_filter = ('user_type', 'is_active', 'is_staff')
    search_fields = ('email',)
    ordering = ('-date_joined',)

    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal info', {'fields': ('user_type',)}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'user_type', 'password1', 'password2'),
        }),
    )


@admin.register(Faculty)
class FacultyAdmin(admin.ModelAdmin):
    list_display = ('faculty_id', 'full_name', 'department', 'designation', 'user')
    list_filter = ('department', 'designation')
    search_fields = ('faculty_id', 'full_name', 'department')
    ordering = ('-created_at',)


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ('usn', 'full_name', 'department', 'semester', 'user')
    list_filter = ('department', 'semester')
    search_fields = ('usn', 'full_name', 'department')
    ordering = ('-created_at',)