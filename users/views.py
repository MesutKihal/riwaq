from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Count, Sum, Avg
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_http_methods
from django.http import Http404
from .forms import UserRegistrationForm, UserProfileForm, InstructorProfileForm, ChangePasswordForm
from .models import User
from courses.models import Enrollment, Certificate, Course
from courses.email_service import EmailService

def register(request):
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            # Ensure new users are students by default and NOT staff
            user.role = 'student'
            user.is_staff = False
            user.is_superuser = False
            user.save()
            
            login(request, user)
            
            # Send welcome email
            EmailService.send_welcome_email(user)
            
            messages.success(request, 'تم التسجيل بنجاح! مرحباً بك في رواق')
            return redirect('courses:home')
    else:
        form = UserRegistrationForm()
    return render(request, 'users/register.html', {'form': form})

@csrf_protect
@require_http_methods(["POST"])
def custom_logout(request):
    """Custom logout view that only accepts POST requests"""
    logout(request)
    messages.success(request, 'تم تسجيل الخروج بنجاح')
    return redirect('courses:home')

@login_required
def profile(request, username=None):
    """View user profile - FIXED with better error handling"""
    
    # If no username provided, show current user's profile
    if username is None:
        profile_user = request.user
    else:
        # Try to get the user, but handle gracefully
        try:
            profile_user = User.objects.get(username=username)
        except User.DoesNotExist:
            messages.error(request, f'المستخدم "{username}" غير موجود')
            return redirect('users:profile')
    
    # Get user statistics
    enrollments = Enrollment.objects.filter(student=profile_user)
    completed_courses = enrollments.filter(status='completed')
    
    # Calculate learning stats
    total_courses = enrollments.count()
    completed_count = completed_courses.count()
    completion_rate = int((completed_count / total_courses) * 100) if total_courses > 0 else 0
    
    # Total hours learned
    total_hours = sum(e.course.duration_weeks * 5 for e in enrollments)
    
    # Certificates
    certificates = Certificate.objects.filter(student=profile_user)
    
    # Recent activity
    recent_activities = []
    
    # Recent enrollments
    recent_enrollments = enrollments.select_related('course').order_by('-enrolled_date')[:5]
    for enrollment in recent_enrollments:
        recent_activities.append({
            'type': 'enrollment',
            'title': f'سجلت في دورة {enrollment.course.title}',
            'date': enrollment.enrolled_date,
            'icon': 'fa-graduation-cap',
            'color': 'success'
        })
    
    # Recent completions
    recent_completions = completed_courses.select_related('course').order_by('-completed_date')[:5]
    for completion in recent_completions:
        recent_activities.append({
            'type': 'completion',
            'title': f'أكملت دورة {completion.course.title}',
            'date': completion.completed_date,
            'icon': 'fa-trophy',
            'color': 'warning'
        })
    
    # Sort by date
    recent_activities.sort(key=lambda x: x['date'], reverse=True)
    recent_activities = recent_activities[:10]
    
    # Instructor stats
    instructor_stats = None
    if profile_user.is_instructor:
        courses = Course.objects.filter(instructor=profile_user)
        instructor_stats = {
            'total_courses': courses.count(),
            'total_students': sum(c.total_students for c in courses),
            'total_revenue': sum(c.payments.aggregate(Sum('amount'))['amount__sum'] or 0 for c in courses),
            'published_courses': courses.filter(is_published=True).count(),
        }
    
    context = {
        'profile_user': profile_user,
        'is_own_profile': profile_user == request.user,
        'total_courses': total_courses,
        'completed_count': completed_count,
        'completion_rate': completion_rate,
        'total_hours': total_hours,
        'certificates_count': certificates.count(),
        'recent_activities': recent_activities,
        'instructor_stats': instructor_stats,
    }
    return render(request, 'users/profile.html', context)

@login_required
def edit_profile(request):
    """Edit user profile - FIXED"""
    if request.method == 'POST':
        form = UserProfileForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'تم تحديث الملف الشخصي بنجاح')
            return redirect('users:profile')
        else:
            messages.error(request, 'يرجى تصحيح الأخطاء في النموذج')
    else:
        form = UserProfileForm(instance=request.user)
    
    return render(request, 'users/edit_profile.html', {'form': form, 'title': 'تعديل الملف الشخصي'})

@login_required
def edit_instructor_profile(request):
    """Edit instructor specific profile"""
    if not request.user.is_instructor:
        messages.error(request, 'هذه الصفحة مخصصة للمدربين فقط')
        return redirect('users:profile')
    
    if request.method == 'POST':
        form = InstructorProfileForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'تم تحديث الملف المهني بنجاح')
            return redirect('users:profile')
        else:
            messages.error(request, 'يرجى تصحيح الأخطاء')
    else:
        form = InstructorProfileForm(instance=request.user)
    
    return render(request, 'users/edit_instructor_profile.html', {'form': form})

@login_required
def change_password(request):
    """Change user password"""
    if request.method == 'POST':
        form = ChangePasswordForm(request.POST)
        if form.is_valid():
            old_password = form.cleaned_data['old_password']
            new_password = form.cleaned_data['new_password1']
            
            if request.user.check_password(old_password):
                request.user.set_password(new_password)
                request.user.save()
                update_session_auth_hash(request, request.user)
                messages.success(request, 'تم تغيير كلمة المرور بنجاح')
                return redirect('users:profile')
            else:
                messages.error(request, 'كلمة المرور الحالية غير صحيحة')
        else:
            messages.error(request, 'يرجى تصحيح الأخطاء')
    else:
        form = ChangePasswordForm()
    
    return render(request, 'users/change_password.html', {'form': form})

@login_required
def email_preferences(request):
    """Email notification preferences"""
    if request.method == 'POST':
        request.user.email_notifications = request.POST.get('email_notifications') == 'on'
        request.user.marketing_emails = request.POST.get('marketing_emails') == 'on'
        request.user.course_updates = request.POST.get('course_updates') == 'on'
        request.user.save()
        
        messages.success(request, 'تم تحديث تفضيلات البريد الإلكتروني')
        return redirect('users:profile')
    
    return render(request, 'users/email_preferences.html')

@login_required
def delete_account(request):
    """Request account deletion"""
    if request.method == 'POST':
        confirm = request.POST.get('confirm')
        if confirm == 'DELETE':
            # Soft delete - deactivate account
            request.user.is_active = False
            request.user.save()
            logout(request)
            messages.success(request, 'تم حذف حسابك بنجاح')
            return redirect('courses:home')
        else:
            messages.error(request, 'الرجاء كتابة DELETE لتأكيد الحذف')
    
    return render(request, 'users/delete_account.html')