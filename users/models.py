from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    """Custom user model for Students and Instructors"""
    
    ROLE_CHOICES = (
        ('student', 'Student'),
        ('instructor', 'Instructor'),
        ('admin', 'Admin'),
    )
    
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='student')
    
    # Profile Information
    bio = models.TextField(blank=True, null=True)
    profile_picture = models.ImageField(upload_to='profiles/', blank=True, null=True)
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    
    # Location
    country = models.CharField(max_length=100, blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    
    # Social Links
    website = models.URLField(blank=True, null=True)
    github = models.URLField(blank=True, null=True)
    linkedin = models.URLField(blank=True, null=True)
    twitter = models.URLField(blank=True, null=True)
    
    # Professional Info (for instructors)
    instructor_bio = models.TextField(blank=True, null=True)
    expertise_areas = models.CharField(max_length=500, blank=True, null=True)
    years_experience = models.IntegerField(default=0)
    company = models.CharField(max_length=200, blank=True, null=True)
    position = models.CharField(max_length=200, blank=True, null=True)
    
    # Preferences
    email_notifications = models.BooleanField(default=True)
    marketing_emails = models.BooleanField(default=True)
    course_updates = models.BooleanField(default=True)
    
    # Stats
    total_courses_completed = models.IntegerField(default=0)
    total_hours_learned = models.IntegerField(default=0)
    total_certificates = models.IntegerField(default=0)
    joined_date = models.DateTimeField(auto_now_add=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.username} - {self.role}"
    
    @property
    def is_instructor(self):
        return self.role == 'instructor'
    
    @property
    def is_student(self):
        return self.role == 'student'
    
    @property
    def is_admin_user(self):
        """Check if user has admin role or is superuser"""
        return self.role == 'admin' or self.is_superuser
    
    @property
    def get_full_name_or_username(self):
        return self.get_full_name() or self.username
    
    @property
    def get_expertise_list(self):
        if self.expertise_areas:
            return [area.strip() for area in self.expertise_areas.split(',')]
        return []
    
    @property
    def profile_completion_percentage(self):
        """Calculate profile completion percentage"""
        fields = ['bio', 'phone_number', 'profile_picture', 'country', 'city']
        completed = sum(1 for field in fields if getattr(self, field))
        
        if self.is_instructor:
            instructor_fields = ['instructor_bio', 'expertise_areas', 'years_experience']
            completed += sum(1 for field in instructor_fields if getattr(self, field))
            return int((completed / (len(fields) + len(instructor_fields))) * 100)
        
        return int((completed / len(fields)) * 100)