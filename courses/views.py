from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.contrib import messages
from django.db.models import Q, Count, Avg
from django.utils import timezone
from .models import Course, Category, Module, Lesson, Enrollment, LessonProgress
from django.contrib.auth import get_user_model

User = get_user_model()

def home_view(request):
    """Homepage with featured courses and categories"""
    featured_courses = Course.objects.filter(is_published=True)[:6]
    categories = Category.objects.all()
    
    # Get popular courses (most enrolled)
    popular_courses = Course.objects.filter(
        is_published=True
    ).annotate(
        student_count=Count('enrollments')
    ).order_by('-student_count')[:4]
    
    # Get recently added courses
    recent_courses = Course.objects.filter(is_published=True).order_by('-created_at')[:4]
    
    context = {
        'featured_courses': featured_courses,
        'categories': categories,
        'popular_courses': popular_courses,
        'recent_courses': recent_courses,
    }
    return render(request, 'courses/home.html', context)

def course_catalog(request):
    """Course catalog with Fuse.js search"""
    categories = Category.objects.all()
    
    # Get filter parameters
    category_slug = request.GET.get('category')
    difficulty = request.GET.get('difficulty')
    
    # Base queryset
    courses = Course.objects.filter(is_published=True)
    
    if category_slug:
        courses = courses.filter(category__slug=category_slug)
    if difficulty:
        courses = courses.filter(difficulty=difficulty)
    
    context = {
        'categories': categories,
        'courses': courses,
        'selected_category': category_slug,
        'selected_difficulty': difficulty,
    }
    return render(request, 'courses/catalog.html', context)

def category_courses(request, slug):
    """Show courses in a specific category"""
    category = get_object_or_404(Category, slug=slug)
    courses = Course.objects.filter(is_published=True, category=category)
    
    context = {
        'category': category,
        'courses': courses,
    }
    return render(request, 'courses/category_courses.html', context)

def course_detail(request, slug):
    """Detailed view of a single course"""
    course = get_object_or_404(Course, slug=slug, is_published=True)
    
    # Check if user is enrolled
    is_enrolled = False
    enrollment = None
    if request.user.is_authenticated:
        enrollment = Enrollment.objects.filter(student=request.user, course=course).first()
        is_enrolled = enrollment is not None
    
    # Get modules and lessons
    modules = course.modules.all().prefetch_related('lessons')
    
    # Get reviews
    reviews = course.reviews.filter(is_approved=True)[:10]
    
    # Calculate average rating
    avg_rating = course.reviews.filter(is_approved=True).aggregate(Avg('rating'))['rating__avg'] or 0
    
    context = {
        'course': course,
        'modules': modules,
        'is_enrolled': is_enrolled,
        'enrollment': enrollment,
        'reviews': reviews,
        'avg_rating': round(avg_rating, 1),
        'total_reviews': course.reviews.filter(is_approved=True).count(),
    }
    return render(request, 'courses/course_detail.html', context)

@login_required
def enroll_course(request, slug):
    """Enroll a student in a course"""
    course = get_object_or_404(Course, slug=slug, is_published=True)
    
    # Check if already enrolled
    enrollment, created = Enrollment.objects.get_or_create(
        student=request.user,
        course=course,
        defaults={'status': 'active'}
    )
    
    if created:
        # Update course stats
        course.total_students += 1
        course.save()
        messages.success(request, f'تم التسجيل بنجاح في دورة {course.title}')
    else:
        messages.info(request, 'أنت مسجل بالفعل في هذه الدورة')
    
    return redirect('courses:course_learn', slug=course.slug)

@login_required
def course_learn(request, slug):
    """Learning page for enrolled students"""
    course = get_object_or_404(Course, slug=slug)
    
    # Check enrollment
    enrollment = get_object_or_404(Enrollment, student=request.user, course=course)
    
    # Get all modules and lessons with progress
    modules = course.modules.all().prefetch_related('lessons')
    
    # Get completed lessons for this student
    completed_lessons = LessonProgress.objects.filter(
        enrollment=enrollment,
        is_completed=True
    ).values_list('lesson_id', flat=True)
    
    # Get first lesson for "resume" functionality
    first_lesson = None
    if modules.exists():
        first_module = modules.first()
        if first_module.lessons.exists():
            first_lesson = first_module.lessons.first()
    
    context = {
        'course': course,
        'modules': modules,
        'enrollment': enrollment,
        'completed_lessons': completed_lessons,
        'first_lesson': first_lesson,
    }
    return render(request, 'courses/course_learn.html', context)

@login_required
def lesson_view(request, slug, lesson_id):
    """View a specific lesson"""
    course = get_object_or_404(Course, slug=slug)
    enrollment = get_object_or_404(Enrollment, student=request.user, course=course)
    lesson = get_object_or_404(Lesson, id=lesson_id, module__course=course)
    
    # Get or create progress record
    progress, created = LessonProgress.objects.get_or_create(
        enrollment=enrollment,
        lesson=lesson
    )
    
    # Get next and previous lessons
    current_lesson_index = list(lesson.module.lessons.all().values_list('id', flat=True)).index(lesson.id)
    lessons_list = list(lesson.module.lessons.all())
    
    prev_lesson = lessons_list[current_lesson_index - 1] if current_lesson_index > 0 else None
    next_lesson = lessons_list[current_lesson_index + 1] if current_lesson_index < len(lessons_list) - 1 else None
    
    # If next lesson doesn't exist in same module, check next module
    if not next_lesson:
        next_modules = list(lesson.module.course.modules.filter(order__gt=lesson.module.order))
        if next_modules:
            next_lessons = next_modules[0].lessons.all()
            if next_lessons:
                next_lesson = next_lessons.first()
    
    context = {
        'course': course,
        'lesson': lesson,
        'progress': progress,
        'prev_lesson': prev_lesson,
        'next_lesson': next_lesson,
        'enrollment': enrollment,
    }
    return render(request, 'courses/lesson_view.html', context)

@login_required
def my_courses(request):
    """Show all courses the student is enrolled in"""
    enrollments = Enrollment.objects.filter(
        student=request.user
    ).select_related('course').order_by('-enrolled_date')
    
    context = {
        'enrollments': enrollments,
    }
    return render(request, 'courses/my_courses.html', context)

@login_required
def my_progress(request):
    """Show detailed progress across all courses"""
    enrollments = Enrollment.objects.filter(
        student=request.user
    ).select_related('course')
    
    total_progress = 0
    if enrollments:
        total_progress = sum(e.progress_percentage for e in enrollments) / enrollments.count()
    
    context = {
        'enrollments': enrollments,
        'total_progress': round(total_progress, 1),
    }
    return render(request, 'courses/my_progress.html', context)

@login_required
def mark_lesson_complete(request):
    """AJAX endpoint to mark a lesson as complete"""
    if request.method == 'POST':
        import json
        data = json.loads(request.body)
        lesson_id = data.get('lesson_id')
        
        lesson = get_object_or_404(Lesson, id=lesson_id)
        enrollment = get_object_or_404(Enrollment, student=request.user, course=lesson.module.course)
        
        progress, created = LessonProgress.objects.get_or_create(
            enrollment=enrollment,
            lesson=lesson
        )
        
        if not progress.is_completed:
            progress.mark_completed()
            return JsonResponse({'success': True, 'progress': enrollment.progress_percentage})
        
        return JsonResponse({'success': True, 'already_completed': True, 'progress': enrollment.progress_percentage})
    
    return JsonResponse({'success': False}, status=400)

def courses_json_data(request):
    """API endpoint to serve course data for Fuse.js search"""
    courses = Course.objects.filter(is_published=True).values(
        'id', 'title', 'slug', 'short_description', 'difficulty'
    )
    
    # Add instructor name and category
    courses_list = list(courses)
    for course in courses_list:
        course_obj = Course.objects.get(id=course['id'])
        course['instructor_name'] = course_obj.instructor.get_full_name() or course_obj.instructor.username
        course['category_name'] = course_obj.category.name
        course['thumbnail_url'] = course_obj.thumbnail.url if course_obj.thumbnail else None
    
    return JsonResponse(courses_list, safe=False)