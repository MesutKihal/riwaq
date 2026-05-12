from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import gettext_lazy as _
from .models import User

class CustomUserAdmin(UserAdmin):
    """Custom admin for User model"""
    
    list_display = ('username', 'email', 'role', 'is_staff', 'is_active')
    list_filter = ('role', 'is_staff', 'is_active', 'is_superuser')
    search_fields = ('username', 'email', 'first_name', 'last_name')
    
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        (_('Personal info'), {'fields': ('first_name', 'last_name', 'email', 'bio', 'profile_picture', 'phone_number')}),
        (_('Location'), {'fields': ('country', 'city')}),
        (_('Social Links'), {'fields': ('website', 'github', 'linkedin', 'twitter')}),
        (_('Role & Permissions'), {'fields': ('role', 'is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        (_('Instructor Info'), {'fields': ('instructor_bio', 'expertise_areas', 'years_experience', 'company', 'position')}),
        (_('Preferences'), {'fields': ('email_notifications', 'marketing_emails', 'course_updates')}),
        (_('Stats'), {'fields': ('total_courses_completed', 'total_hours_learned', 'total_certificates')}),
        (_('Important dates'), {'fields': ('last_login', 'date_joined', 'joined_date')}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'password1', 'password2', 'role'),
        }),
    )
    
    def save_model(self, request, obj, form, change):
        """Ensure non-admin users don't get staff privileges"""
        if not obj.is_admin_user:
            obj.is_staff = False
            obj.is_superuser = False
        super().save_model(request, obj, form, change)

admin.site.register(User, CustomUserAdmin)