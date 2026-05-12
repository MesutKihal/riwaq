from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

app_name = 'users'

urlpatterns = [
    # Authentication
    path('login/', auth_views.LoginView.as_view(template_name='users/login.html'), name='login'),
    path('logout/', views.custom_logout, name='logout'),
    path('register/', views.register, name='register'),
    
    # Profile URLs - SPECIFIC patterns FIRST
    path('profile/edit/', views.edit_profile, name='edit_profile'),
    path('profile/instructor/edit/', views.edit_instructor_profile, name='edit_instructor_profile'),
    path('profile/change-password/', views.change_password, name='change_password'),
    path('profile/email-preferences/', views.email_preferences, name='email_preferences'),
    path('profile/delete/', views.delete_account, name='delete_account'),
    
    # Profile view with username - GENERAL pattern LAST
    path('profile/', views.profile, name='profile'),
    path('profile/<str:username>/', views.profile, name='profile_view'),
]