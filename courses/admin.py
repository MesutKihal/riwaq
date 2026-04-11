from django.contrib import admin
from .models import (
    Category, Course, Module, Lesson, 
    Enrollment, LessonProgress, Review
)

class ModuleInline(admin.TabularInline):
    model = Module
    extra = 1
    ordering = ['order']

class LessonInline(admin.TabularInline):
    model = Lesson
    extra = 1
    ordering = ['order']

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'order']
    prepopulated_fields = {'slug': ('name',)}
    list_editable = ['order']

@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ['title', 'instructor', 'category', 'difficulty', 'is_published', 'total_students']
    list_filter = ['is_published', 'difficulty', 'category', 'created_at']
    search_fields = ['title', 'description']
    prepopulated_fields = {'slug': ('title',)}
    inlines = [ModuleInline]
    readonly_fields = ['total_students', 'rating', 'total_reviews']
    
    fieldsets = (
        ('Basic Info', {
            'fields': ('title', 'slug', 'description', 'short_description', 'category', 'instructor')
        }),
        ('Media', {
            'fields': ('thumbnail', 'promo_video')
        }),
        ('Course Details', {
            'fields': ('difficulty', 'duration_weeks', 'language', 'price')
        }),
        ('Status', {
            'fields': ('is_published', 'published_date')
        }),
        ('Statistics', {
            'fields': ('total_students', 'rating', 'total_reviews'),
            'classes': ('collapse',)
        })
    )

@admin.register(Module)
class ModuleAdmin(admin.ModelAdmin):
    list_display = ['title', 'course', 'order']
    list_filter = ['course']
    inlines = [LessonInline]

@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display = ['title', 'module', 'lesson_type', 'order', 'duration_minutes']
    list_filter = ['lesson_type', 'module__course']

@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ['student', 'course', 'progress_percentage', 'status', 'enrolled_date']
    list_filter = ['status', 'course']
    readonly_fields = ['progress_percentage']

@admin.register(LessonProgress)
class LessonProgressAdmin(admin.ModelAdmin):
    list_display = ['enrollment', 'lesson', 'is_completed', 'completed_date']
    list_filter = ['is_completed']

@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ['course', 'student', 'rating', 'created_at']
    list_filter = ['rating', 'is_approved']