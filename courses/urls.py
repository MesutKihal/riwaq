from django.urls import path
from . import views

app_name = 'courses'

urlpatterns = [
    # Home & Catalog
    path('', views.home_view, name='home'),
    path('catalog/', views.course_catalog, name='course_catalog'),
    path('category/<slug:slug>/', views.category_courses, name='category_courses'),
    
    # Course Detail & Learning
    path('course/<slug:slug>/', views.course_detail, name='course_detail'),
    path('course/<slug:slug>/learn/', views.course_learn, name='course_learn'),
    path('course/<slug:slug>/lesson/<int:lesson_id>/', views.lesson_view, name='lesson_view'),
    
    # Enrollment
    path('course/<slug:slug>/enroll/', views.enroll_course, name='enroll_course'),
    
    # Student Dashboard
    path('my-courses/', views.my_courses, name='my_courses'),
    path('my-progress/', views.my_progress, name='my_progress'),
    
    # API endpoints for AJAX
    path('api/lesson-complete/', views.mark_lesson_complete, name='mark_lesson_complete'),
    path('api/courses-data/', views.courses_json_data, name='courses_json_data'),
]