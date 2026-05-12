from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.contrib import messages
from django.db.models import Q, Count, Avg
from django.utils import timezone
from .models import Course, Category, Module, Lesson, Enrollment, LessonProgress
from .forms import CourseForm, ModuleForm, LessonForm
from django.contrib.auth import get_user_model
from django.http import HttpResponse, HttpResponseBadRequest, Http404
from django.views.decorators.http import condition
from django.core.files.storage import default_storage
import os
import re
from .models import Quiz, Question, Choice, QuizAttempt, Answer, Wishlist, Discussion, DiscussionAnswer
from .forms import QuizForm, QuestionForm, ChoiceForm
from chargily_pay import ChargilyClient
from chargily_pay.entity import Checkout
from .models import Payment, Course, Enrollment
from django.views.decorators.csrf import csrf_exempt
import json
from django.db.models import Sum, Count, Q, Avg
from django.utils import timezone
from datetime import timedelta
import plotly.express as px
import plotly.utils
from .models import CourseAnalytics, InstructorPayout
import requests

CHARGILIY_LIVE_URL = "https://pay.chargily.net/api/v2"
CHARGILIY_TEST_URL = "https://pay.chargily.net/test/api/v2"

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
    course = get_object_or_404(Course, slug=slug, is_published=True)
    
    enrollment, created = Enrollment.objects.get_or_create(
        student=request.user,
        course=course,
        defaults={'status': 'active'}
    )
    
    if created:
        course.total_students += 1
        course.save()
        
        # Notify instructor about new enrollment
        EmailService.send_new_enrollment_notification(
            instructor=course.instructor,
            student=request.user,
            course=course
        )
        
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
    """API endpoint to serve course data for search"""
    courses = Course.objects.filter(is_published=True).values(
        'id', 'title', 'slug', 'short_description', 'difficulty', 
        'price', 'total_students', 'rating', 'created_at'
    )
    
    courses_list = []
    for course in courses:
        course_obj = Course.objects.get(id=course['id'])
        courses_list.append({
            'id': course['id'],
            'title': course['title'],
            'slug': course['slug'],
            'short_description': course['short_description'],
            'difficulty': course['difficulty'],
            'price': float(course['price']),
            'total_students': course['total_students'],
            'rating': float(course['rating']) if course['rating'] else None,
            'created_at': course['created_at'].isoformat(),
            'category_name': course_obj.category.name,
            'instructor_name': course_obj.instructor.get_full_name() or course_obj.instructor.username,
            'thumbnail_url': course_obj.thumbnail.url if course_obj.thumbnail else None,
        })
    
    return JsonResponse(courses_list, safe=False)

@login_required
def instructor_dashboard(request):
    """Instructor dashboard showing all courses taught by the instructor"""
    if not request.user.is_instructor:
        messages.error(request, 'عذراً، هذه الصفحة مخصصة للمدربين فقط')
        return redirect('courses:home')
    
    # Get instructor's courses
    courses = Course.objects.filter(instructor=request.user).annotate(
        total_students_count=Count('enrollments'),
        total_modules_count=Count('modules')
    )
    
    # Get statistics
    total_courses = courses.count()
    total_students = sum(course.total_students_count for course in courses)
    total_modules = sum(course.total_modules_count for course in courses)
    
    # Get recent enrollments across all instructor's courses
    recent_enrollments = Enrollment.objects.filter(
        course__instructor=request.user
    ).select_related('student', 'course').order_by('-enrolled_date')[:10]
    
    context = {
        'courses': courses,
        'total_courses': total_courses,
        'total_students': total_students,
        'total_modules': total_modules,
        'recent_enrollments': recent_enrollments,
    }
    return render(request, 'courses/instructor/dashboard.html', context)

@login_required
def course_create(request):
    """Create a new course - WITH DEBUGGING"""
    if not request.user.is_instructor:
        messages.error(request, 'عذراً، هذه الصفحة مخصصة للمدربين فقط')
        return redirect('courses:home')
    
    if request.method == 'POST':
        print("=" * 50)
        print("FORM SUBMISSION DEBUG:")
        print(f"POST data: {request.POST}")
        print(f"FILES data: {request.FILES}")
        print("=" * 50)
        
        form = CourseForm(request.POST, request.FILES)
        
        # Check if form is valid
        if form.is_valid():
            course = form.save(commit=False)
            course.instructor = request.user
            course.save()
            messages.success(request, f'تم إنشاء الدورة {course.title} بنجاح')
            return redirect('courses:instructor_dashboard')
        else:
            # Print form errors for debugging
            print("FORM ERRORS:")
            for field, errors in form.errors.items():
                print(f"  {field}: {errors}")
            messages.error(request, 'يرجى تصحيح الأخطاء في النموذج')
    else:
        form = CourseForm()
    
    return render(request, 'courses/instructor/course_form.html', {'form': form, 'title': 'إنشاء دورة جديدة'})

@login_required
def course_edit(request, slug):
    """Edit an existing course"""
    course = get_object_or_404(Course, slug=slug)
    
    # Check permission
    if course.instructor != request.user:
        messages.error(request, 'عذراً، ليس لديك صلاحية تعديل هذه الدورة')
        return redirect('courses:instructor_dashboard')
    
    if request.method == 'POST':
        form = CourseForm(request.POST, request.FILES, instance=course)
        if form.is_valid():
            form.save()
            messages.success(request, f'تم تحديث الدورة {course.title} بنجاح')
            return redirect('courses:instructor_dashboard')
        else:
            messages.error(request, 'يرجى تصحيح الأخطاء في النموذج')
    else:
        form = CourseForm(instance=course)
    
    return render(request, 'courses/instructor/course_form.html', {
        'form': form, 
        'title': 'تعديل الدورة', 
        'course': course
    })

@login_required
def course_delete(request, slug):
    """Delete a course"""
    course = get_object_or_404(Course, slug=slug)
    
    if course.instructor != request.user:
        messages.error(request, 'عذراً، ليس لديك صلاحية حذف هذه الدورة')
        return redirect('courses:instructor_dashboard')
    
    if request.method == 'POST':
        course_title = course.title
        course.delete()
        messages.success(request, f'تم حذف الدورة {course_title} بنجاح')
        return redirect('courses:instructor_dashboard')
    
    return render(request, 'courses/instructor/confirm_delete.html', {'object': course, 'type': 'الدورة'})

@login_required
def module_add(request, slug):
    """Add a module to a course"""
    course = get_object_or_404(Course, slug=slug)
    
    if course.instructor != request.user:
        messages.error(request, 'عذراً، ليس لديك صلاحية إضافة محتوى لهذه الدورة')
        return redirect('courses:instructor_dashboard')
    
    if request.method == 'POST':
        form = ModuleForm(request.POST)
        if form.is_valid():
            module = form.save(commit=False)
            module.course = course
            module.order = course.modules.count() + 1
            module.save()
            messages.success(request, f'تم إضافة الوحدة {module.title} بنجاح')
            return redirect('courses:course_edit', slug=course.slug)
    else:
        form = ModuleForm()
    
    return render(request, 'courses/instructor/module_form.html', {'form': form, 'course': course, 'title': 'إضافة وحدة جديدة'})

@login_required
def module_edit(request, module_id):
    """Edit a module"""
    module = get_object_or_404(Module, id=module_id)
    
    if module.course.instructor != request.user:
        messages.error(request, 'عذراً، ليس لديك صلاحية تعديل هذا المحتوى')
        return redirect('courses:instructor_dashboard')
    
    if request.method == 'POST':
        form = ModuleForm(request.POST, instance=module)
        if form.is_valid():
            form.save()
            messages.success(request, f'تم تحديث الوحدة {module.title} بنجاح')
            return redirect('courses:course_edit', slug=module.course.slug)
    else:
        form = ModuleForm(instance=module)
    
    return render(request, 'courses/instructor/module_form.html', {'form': form, 'course': module.course, 'title': 'تعديل الوحدة'})

@login_required
def module_delete(request, module_id):
    """Delete a module"""
    module = get_object_or_404(Module, id=module_id)
    
    if module.course.instructor != request.user:
        messages.error(request, 'عذراً، ليس لديك صلاحية حذف هذا المحتوى')
        return redirect('courses:instructor_dashboard')
    
    if request.method == 'POST':
        module_title = module.title
        module.delete()
        messages.success(request, f'تم حذف الوحدة {module_title} بنجاح')
        return redirect('courses:course_edit', slug=module.course.slug)
    
    return render(request, 'courses/instructor/confirm_delete.html', {'object': module, 'type': 'الوحدة'})

@login_required
def lesson_add(request, module_id):
    """Add a lesson to a module"""
    module = get_object_or_404(Module, id=module_id)
    
    if module.course.instructor != request.user:
        messages.error(request, 'عذراً، ليس لديك صلاحية إضافة محتوى لهذه الدورة')
        return redirect('courses:instructor_dashboard')
    
    if request.method == 'POST':
        form = LessonForm(request.POST, request.FILES)
        if form.is_valid():
            lesson = form.save(commit=False)
            lesson.module = module
            lesson.order = module.lessons.count() + 1
            lesson.save()
            messages.success(request, f'تم إضافة الدرس {lesson.title} بنجاح')
            return redirect('courses:course_edit', slug=module.course.slug)
    else:
        form = LessonForm()
    
    return render(request, 'courses/instructor/lesson_form.html', {'form': form, 'module': module, 'title': 'إضافة درس جديد'})

@login_required
def lesson_edit(request, lesson_id):
    """Edit a lesson"""
    lesson = get_object_or_404(Lesson, id=lesson_id)
    
    if lesson.module.course.instructor != request.user:
        messages.error(request, 'عذراً، ليس لديك صلاحية تعديل هذا المحتوى')
        return redirect('courses:instructor_dashboard')
    
    if request.method == 'POST':
        form = LessonForm(request.POST, request.FILES, instance=lesson)
        if form.is_valid():
            form.save()
            messages.success(request, f'تم تحديث الدرس {lesson.title} بنجاح')
            return redirect('courses:course_edit', slug=lesson.module.course.slug)
    else:
        form = LessonForm(instance=lesson)
    
    return render(request, 'courses/instructor/lesson_form.html', {'form': form, 'module': lesson.module, 'title': 'تعديل الدرس'})

@login_required
def lesson_delete(request, lesson_id):
    """Delete a lesson"""
    lesson = get_object_or_404(Lesson, id=lesson_id)
    
    if lesson.module.course.instructor != request.user:
        messages.error(request, 'عذراً، ليس لديك صلاحية حذف هذا المحتوى')
        return redirect('courses:instructor_dashboard')
    
    if request.method == 'POST':
        lesson_title = lesson.title
        lesson.delete()
        messages.success(request, f'تم حذف الدرس {lesson_title} بنجاح')
        return redirect('courses:course_edit', slug=lesson.module.course.slug)
    
    return render(request, 'courses/instructor/confirm_delete.html', {'object': lesson, 'type': 'الدرس'})

def stream_video(request, file_path):
    """
    Stream video files with support for range requests (seeking)
    This is crucial for video playback in browsers
    """
    if not default_storage.exists(file_path):
        raise Http404("Video not found")
    
    # Get file size
    file_size = default_storage.size(file_path)
    
    # Get range header
    range_header = request.META.get('HTTP_RANGE', '').strip()
    range_match = re.match(r'bytes=(\d+)-(\d*)', range_header)
    
    if range_match:
        start_byte = int(range_match.group(1))
        end_byte = range_match.group(2)
        
        if end_byte:
            end_byte = int(end_byte)
        else:
            end_byte = file_size - 1
        
        if start_byte >= file_size or end_byte >= file_size:
            return HttpResponse(status=416)  # Range not satisfiable
        
        # Calculate content length
        content_length = end_byte - start_byte + 1
        
        # Open file and seek to start position
        with default_storage.open(file_path, 'rb') as f:
            f.seek(start_byte)
            content = f.read(content_length)
        
        response = HttpResponse(content, status=206)  # Partial content
        response['Content-Type'] = 'video/mp4'
        response['Content-Length'] = str(content_length)
        response['Content-Range'] = f'bytes {start_byte}-{end_byte}/{file_size}'
        response['Accept-Ranges'] = 'bytes'
    else:
        # Return entire file
        with default_storage.open(file_path, 'rb') as f:
            content = f.read()
        
        response = HttpResponse(content, status=200)
        response['Content-Type'] = 'video/mp4'
        response['Content-Length'] = str(file_size)
        response['Accept-Ranges'] = 'bytes'
    
    return response

@login_required
def save_video_progress(request):
    """Save video watching progress"""
    if request.method == 'POST':
        import json
        data = json.loads(request.body)
        lesson_id = data.get('lesson_id')
        position = data.get('position', 0)
        
        lesson = get_object_or_404(Lesson, id=lesson_id)
        enrollment = get_object_or_404(Enrollment, student=request.user, course=lesson.module.course)
        
        progress, created = LessonProgress.objects.get_or_create(
            enrollment=enrollment,
            lesson=lesson
        )
        
        progress.last_watched_position = position
        progress.save()
        
        return JsonResponse({'success': True, 'position': position})
    
    return JsonResponse({'success': False}, status=400)

@login_required
def take_quiz(request, lesson_id):
    """Take a quiz for a lesson"""
    lesson = get_object_or_404(Lesson, id=lesson_id, lesson_type='quiz')
    quiz = get_object_or_404(Quiz, lesson=lesson)
    enrollment = get_object_or_404(Enrollment, student=request.user, course=lesson.module.course)
    
    # Check if quiz is already completed
    existing_attempt = QuizAttempt.objects.filter(
        quiz=quiz, 
        student=request.user, 
        passed=True
    ).first()
    
    if existing_attempt:
        messages.info(request, 'لقد اجتزت هذا الاختبار بالفعل')
        return redirect('courses:lesson_view', slug=lesson.module.course.slug, lesson_id=lesson.id)
    
    # Check attempts limit
    attempts_count = QuizAttempt.objects.filter(
        quiz=quiz, 
        student=request.user
    ).count()
    
    if attempts_count >= quiz.attempts_allowed:
        messages.error(request, 'لقد استنفدت جميع المحاولات المسموح بها')
        return redirect('courses:lesson_view', slug=lesson.module.course.slug, lesson_id=lesson.id)
    
    # Get or create attempt
    attempt, created = QuizAttempt.objects.get_or_create(
        quiz=quiz,
        student=request.user,
        attempt_number=attempts_count + 1,
        defaults={'enrollment': enrollment}
    )
    
    if request.method == 'POST':
        # Process answers
        score = 0
        total_points = 0
        
        for question in quiz.questions.all():
            total_points += question.points
            answer_key = f'question_{question.id}'
            
            if question.question_type == 'single':
                choice_id = request.POST.get(answer_key)
                if choice_id:
                    choice = Choice.objects.get(id=choice_id)
                    is_correct = choice.is_correct
                    points_earned = question.points if is_correct else 0
                    
                    Answer.objects.create(
                        attempt=attempt,
                        question=question,
                        choice=choice,
                        is_correct=is_correct,
                        points_earned=points_earned
                    )
                    
                    if is_correct:
                        score += points_earned
                        
            elif question.question_type == 'multiple':
                choice_ids = request.POST.getlist(answer_key)
                choices = Choice.objects.filter(id__in=choice_ids)
                correct_choices = choices.filter(is_correct=True).count()
                total_correct = question.choices.filter(is_correct=True).count()
                
                if correct_choices == total_correct and len(choice_ids) == total_correct:
                    points_earned = question.points
                    score += points_earned
                else:
                    points_earned = 0
                
                for choice in choices:
                    Answer.objects.create(
                        attempt=attempt,
                        question=question,
                        choice=choice,
                        is_correct=choice.is_correct,
                        points_earned=points_earned if choice.is_correct else 0
                    )
                    
            elif question.question_type == 'true_false':
                choice_id = request.POST.get(answer_key)
                if choice_id:
                    choice = Choice.objects.get(id=choice_id)
                    is_correct = choice.is_correct
                    points_earned = question.points if is_correct else 0
                    
                    Answer.objects.create(
                        attempt=attempt,
                        question=question,
                        choice=choice,
                        is_correct=is_correct,
                        points_earned=points_earned
                    )
                    
                    if is_correct:
                        score += points_earned
                        
            elif question.question_type == 'text':
                text_answer = request.POST.get(answer_key, '')
                # For text questions, instructor needs to grade manually
                Answer.objects.create(
                    attempt=attempt,
                    question=question,
                    text_answer=text_answer,
                    is_correct=False,  # Needs manual grading
                    points_earned=0
                )
        
        # Calculate score percentage
        score_percentage = int((score / total_points) * 100) if total_points > 0 else 0
        passed = score_percentage >= quiz.passing_score
        
        attempt.score = score_percentage
        attempt.passed = passed
        attempt.completed_at = timezone.now()
        attempt.save()
        
        if passed:
            # Mark lesson as completed
            progress, created = LessonProgress.objects.get_or_create(
                enrollment=enrollment,
                lesson=lesson
            )
            if not progress.is_completed:
                progress.mark_completed()
            
            messages.success(request, f'تهانينا! لقد اجتزت الاختبار بنسبة {score_percentage}%')
        else:
            messages.warning(request, f'لم تجتز الاختبار. حصلت على {score_percentage}%. المطلوب {quiz.passing_score}%')
        
        return redirect('courses:quiz_result', attempt_id=attempt.id)
    
    context = {
        'quiz': quiz,
        'attempt': attempt,
        'lesson': lesson,
        'course': lesson.module.course,
    }
    return render(request, 'courses/quiz/take_quiz.html', context)

@login_required
def quiz_result(request, attempt_id):
    """Show quiz results"""
    attempt = get_object_or_404(QuizAttempt, id=attempt_id, student=request.user)
    
    context = {
        'attempt': attempt,
        'quiz': attempt.quiz,
    }
    return render(request, 'courses/quiz/quiz_result.html', context)

@login_required
def quiz_review(request, attempt_id):
    """Review quiz answers"""
    attempt = get_object_or_404(QuizAttempt, id=attempt_id, student=request.user)
    
    context = {
        'attempt': attempt,
        'quiz': attempt.quiz,
    }
    return render(request, 'courses/quiz/quiz_review.html', context)

@login_required
def download_certificate(request, course_slug):
    """Download certificate for completed course"""
    course = get_object_or_404(Course, slug=course_slug)
    certificate = get_object_or_404(Certificate, student=request.user, course=course)
    
    if certificate.pdf_file:
        return redirect(certificate.pdf_file.url)
    else:
        messages.error(request, 'الشهادة غير متاحة حالياً')
        return redirect('courses:course_detail', slug=course.slug)


@login_required
def initiate_payment(request, slug):
    """Initiate payment for a course"""
    course = get_object_or_404(Course, slug=slug)
    
    # Check if already enrolled
    existing_enrollment = Enrollment.objects.filter(student=request.user, course=course).first()
    if existing_enrollment:
        messages.info(request, 'أنت مسجل بالفعل في هذه الدورة')
        return redirect('courses:course_learn', slug=course.slug)
    
    # Check for existing pending payment
    existing_payment = Payment.objects.filter(
        student=request.user,
        course=course,
        status='pending'
    ).first()
    
    if existing_payment and existing_payment.checkout_url:
        # Redirect to existing checkout
        return redirect(existing_payment.checkout_url)
    
    if request.method == 'POST':
        amount = float(course.price)
        payment_method = request.POST.get('payment_method')
        
        # Initialize Chargily client
        api_url = CHARGILIY_TEST_URL if CHARGILY_MODE == 'test' else CHARGILIY_LIVE_URL
        chargily = ChargilyClient(CHARGILY_API_KEY, CHARGILY_SECRET_KEY, api_url)
        
        # Create checkout session
        checkout = chargily.create_checkout(
            Checkout(
                amount=int(amount * 100),  # Chargily expects amount in cents/centimes
                currency="dzd",
                success_url=settings.CHARGILY_SUCCESS_URL,
                failure_url=settings.CHARGILY_FAILURE_URL,
                metadata={
                    'course_id': course.id,
                    'course_slug': course.slug,
                    'student_id': request.user.id,
                    'student_email': request.user.email
                }
            )
        )
        
        # Create payment record
        payment = Payment.objects.create(
            student=request.user,
            course=course,
            amount=amount,
            status='pending',
            checkout_id=checkout.get('id'),
            checkout_url=checkout.get('url'),
            payment_method=payment_method
        )
        
        # Redirect to Chargily payment page
        return redirect(checkout.get('url'))
    
    context = {
        'course': course,
        'payment_methods': [
            {'value': 'edahabia', 'label': 'EDAHABIA (بطاقة الذهبية)', 'icon': 'fas fa-credit-card'},
            {'value': 'cib', 'label': 'CIB (بطاقة سيب)', 'icon': 'fas fa-credit-card'},
        ]
    }
    return render(request, 'courses/payment/initiate.html', context)

@login_required
def payment_success(request):
    checkout_id = request.GET.get('checkout_id')
    
    if checkout_id:
        payment = Payment.objects.filter(checkout_id=checkout_id).first()
        if payment:
            payment.mark_as_paid()
            
            # Send payment confirmation email
            EmailService.send_payment_confirmation(payment)
            
            messages.success(request, f'تم الدفع بنجاح! تم تفعيل اشتراكك في دورة {payment.course.title}')
            return redirect('courses:course_learn', slug=payment.course.slug)
    
    messages.success(request, 'تم الدفع بنجاح! يمكنك الآن البدء في التعلم')
    return redirect('courses:my_courses')

@login_required
def payment_failure(request):
    """Handle failed payment"""
    messages.error(request, 'عذراً، فشلت عملية الدفع. يرجى المحاولة مرة أخرى')
    return redirect('courses:my_courses')

@csrf_exempt
def payment_webhook(request):
    """Webhook for Chargily to confirm payments"""
    if request.method == 'POST':
        try:
            payload = json.loads(request.body)
            
            # Verify webhook signature (implement based on Chargily docs)
            checkout_id = payload.get('data', {}).get('id')
            event_type = payload.get('type')
            
            if event_type == 'checkout.paid' and checkout_id:
                payment = Payment.objects.filter(checkout_id=checkout_id).first()
                if payment and payment.status == 'pending':
                    payment.mark_as_paid(payment_id=payload.get('data', {}).get('payment_intent'))
                    
                    # Send email notification
                    send_payment_confirmation_email(payment)
                    
                    return JsonResponse({'status': 'success'}, status=200)
            
            return JsonResponse({'status': 'ignored'}, status=200)
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)

def send_payment_confirmation_email(payment):
    """Send email confirmation after successful payment"""
    from django.core.mail import send_mail
    from django.conf import settings
    
    subject = f'تأكيد الدفع - {payment.course.title}'
    message = f'''
    مرحباً {payment.student.get_full_name() or payment.student.username},
    
    تم تأكيد دفعك بنجاح لدورة "{payment.course.title}".
    
    تفاصيل الدفع:
    - المبلغ: {payment.amount} DZD
    - التاريخ: {payment.paid_at}
    - رقم العملية: {payment.transaction_id or payment.payment_id}
    
    يمكنك الآن الوصول إلى محتوى الدورة من خلال حسابك في رواق.
    
    رابط الدورة: https://your-domain.com/course/{payment.course.slug}/learn/
    
    شكراً لانضمامك إلى رواق!
    '''
    
    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [payment.student.email],
        fail_silently=True,
    )

@login_required
def add_review(request, slug):
    """Add a review for a course"""
    course = get_object_or_404(Course, slug=slug)
    
    if request.method == 'POST':
        rating = request.POST.get('rating')
        comment = request.POST.get('comment')
        
        if rating and comment:
            review, created = Review.objects.get_or_create(
                course=course,
                student=request.user,
                defaults={
                    'rating': int(rating),
                    'comment': comment
                }
            )
            
            if not created:
                # Update existing review
                review.rating = int(rating)
                review.comment = comment
                review.updated_at = timezone.now()
                review.save()
            
            # Update course average rating
            avg_rating = course.reviews.filter(is_approved=True).aggregate(Avg('rating'))['rating__avg']
            course.rating = avg_rating or 0
            course.total_reviews = course.reviews.filter(is_approved=True).count()
            course.save()
            
            messages.success(request, 'تم إضافة تقييمك بنجاح!')
        else:
            messages.error(request, 'الرجاء إدخال التقييم والتعليق')
    
    return redirect('courses:course_detail', slug=course.slug)

def verify_turnstile(token):
    """Verify Cloudflare Turnstile captcha"""
    response = requests.post(
        'https://challenges.cloudflare.com/turnstile/v0/siteverify',
        data={
            'secret': settings.TURNSTILE_SECRET_KEY,
            'response': token
        }
    )
    return response.json().get('success', False)



@login_required
def instructor_dashboard(request):
    """Enhanced instructor dashboard with analytics"""
    if not request.user.is_instructor:
        messages.error(request, 'عذراً، هذه الصفحة مخصصة للمدربين فقط')
        return redirect('courses:home')
    
    # Get instructor's courses
    courses = Course.objects.filter(instructor=request.user).annotate(
        total_students_count=Count('enrollments', distinct=True),
        total_modules_count=Count('modules', distinct=True),
        total_lessons_count=Count('modules__lessons', distinct=True),
        completion_rate=Avg('enrollments__progress_percentage')
    )
    
    # Overall statistics
    total_courses = courses.count()
    total_students = sum(course.total_students_count for course in courses)
    total_revenue = courses.aggregate(total=Sum('payments__amount'))['total'] or 0
    
    # Calculate average completion rate
    avg_completion = courses.aggregate(avg=Avg('completion_rate'))['avg'] or 0
    
    # Get recent enrollments (last 30 days)
    thirty_days_ago = timezone.now() - timedelta(days=30)
    recent_enrollments = Enrollment.objects.filter(
        course__instructor=request.user,
        enrolled_date__gte=thirty_days_ago
    ).select_related('student', 'course').order_by('-enrolled_date')[:10]
    
    # Chart data: Enrollments over time
    enrollments_by_date = Enrollment.objects.filter(
        course__instructor=request.user,
        enrolled_date__gte=thirty_days_ago
    ).extra({'date': "date(enrolled_date)"}).values('date').annotate(
        count=Count('id')
    ).order_by('date')
    
    # Prepare chart JSON
    enrollment_dates = [item['date'] for item in enrollments_by_date]
    enrollment_counts = [item['count'] for item in enrollments_by_date]
    
    # 1. Prepare the data in a dictionary (or DataFrame)
    data = {
        'التاريخ': enrollment_dates,
        'عدد الطلاب': enrollment_counts
    }

    # 2. Use the keys as references
    fig = px.line(
        data, 
        x='التاريخ', 
        y='عدد الطلاب',
        title="التسجيلات خلال الـ 30 يوم الماضية",
        labels={'x': 'التاريخ', 'y': 'عدد الطلاب'}
    )
    fig.update_layout(template='plotly_white')
    enrollment_chart = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
    
    # Course performance data
    course_performance = []
    for course in courses:
        course_performance.append({
            'name': course.title,
            'students': course.total_students_count,
            'completion': round(course.completion_rate or 0),
            'revenue': float(course.payments.aggregate(total=Sum('amount'))['total'] or 0)
        })
    
    # Payout summary
    total_pending_payout = InstructorPayout.objects.filter(
        instructor=request.user,
        status='pending'
    ).aggregate(total=Sum('net_amount'))['total'] or 0
    
    total_paid_payout = InstructorPayout.objects.filter(
        instructor=request.user,
        status='completed'
    ).aggregate(total=Sum('net_amount'))['total'] or 0
    
    context = {
        'courses': courses,
        'total_courses': total_courses,
        'total_students': total_students,
        'total_revenue': total_revenue,
        'avg_completion': round(avg_completion),
        'recent_enrollments': recent_enrollments,
        'enrollment_chart': enrollment_chart,
        'course_performance': course_performance,
        'total_pending_payout': total_pending_payout,
        'total_paid_payout': total_paid_payout,
    }
    return render(request, 'courses/instructor/dashboard.html', context)

@login_required
def request_payout(request):
    """Request instructor payout"""
    if not request.user.is_instructor:
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    if request.method == 'POST':
        # Get all pending payouts
        pending_payouts = InstructorPayout.objects.filter(
            instructor=request.user,
            status='pending'
        )
        
        total_amount = pending_payouts.aggregate(total=Sum('net_amount'))['total'] or 0
        
        if total_amount > 0:
            # Create payout request record
            PayoutRequest.objects.create(
                instructor=request.user,
                amount=total_amount,
                payouts=pending_payouts
            )
            
            # Mark payouts as processing
            pending_payouts.update(status='processing')
            
            # Send notification to admin
            send_payout_notification_to_admin(request.user, total_amount)
            
            return JsonResponse({'success': True, 'amount': float(total_amount)})
    
    return JsonResponse({'success': False})

def categories_json_data(request):
    """API endpoint for categories with course counts"""
    categories = Category.objects.annotate(
        course_count=Count('courses', filter=Q(courses__is_published=True))
    ).values('id', 'name', 'slug', 'course_count')
    
    return JsonResponse(list(categories), safe=False)

@login_required
def toggle_wishlist(request, slug):
    """Add or remove course from wishlist"""
    course = get_object_or_404(Course, slug=slug)
    
    wishlist_item = Wishlist.objects.filter(student=request.user, course=course)
    
    if wishlist_item.exists():
        wishlist_item.delete()
        messages.success(request, f'تم إزالة {course.title} من المفضلة')
    else:
        Wishlist.objects.create(student=request.user, course=course)
        messages.success(request, f'تم إضافة {course.title} إلى المفضلة')

    referer = request.META.get('HTTP_REFERER')
    if referer:
        return redirect(referer)
    else:
        return redirect('courses:course_detail', slug=slug)

@login_required
def wishlist_view(request):
    """Display user's wishlist"""
    wishlist_items = Wishlist.objects.filter(student=request.user).select_related('course')
    
    context = {
        'wishlist_items': wishlist_items,
    }
    return render(request, 'courses/wishlist.html', context)


@login_required
def discussion_list(request, slug):
    """View all questions for a course"""
    course = get_object_or_404(Course, slug=slug)
    discussions = Discussion.objects.filter(course=course)
    
    context = {
        'course': course,
        'discussions': discussions,
    }
    return render(request, 'courses/discussion_list.html', context)

@login_required
def discussion_detail(request, discussion_id):
    """View a single question and its answers"""
    discussion = get_object_or_404(Discussion, id=discussion_id)
    
    if request.method == 'POST':
        content = request.POST.get('content')
        if content:
            DiscussionAnswer.objects.create(
                discussion=discussion,
                author=request.user,
                content=content
            )
            messages.success(request, 'تم إضافة إجابتك')
            return redirect('courses:discussion_detail', discussion_id=discussion.id)
    
    context = {
        'discussion': discussion,
    }
    return render(request, 'courses/discussion_detail.html', context)

@login_required
def ask_question(request, slug):
    """Ask a new question"""
    course = get_object_or_404(Course, slug=slug)
    
    if request.method == 'POST':
        title = request.POST.get('title')
        content = request.POST.get('content')
        
        if title and content:
            Discussion.objects.create(
                course=course,
                student=request.user,
                title=title,
                content=content
            )
            messages.success(request, 'تم نشر سؤالك')
            return redirect('courses:discussion_list', slug=course.slug)
        else:
            messages.error(request, 'الرجاء ملء جميع الحقول')
    
    context = {
        'course': course,
    }
    return render(request, 'courses/ask_question.html', context)

@login_required
def accept_answer(request, answer_id):
    """Mark an answer as accepted (instructor only)"""
    answer = get_object_or_404(DiscussionAnswer, id=answer_id)
    discussion = answer.discussion
    
    if request.user == discussion.course.instructor or request.user.is_staff:
        # Remove accepted status from other answers
        discussion.answers.update(is_accepted=False)
        # Accept this answer
        answer.is_accepted = True
        answer.save()
        discussion.is_resolved = True
        discussion.save()
        messages.success(request, 'تم قبول الإجابة')
    
    return redirect('courses:discussion_detail', discussion_id=discussion.id)