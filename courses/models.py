from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.urls import reverse
from .email_service import EmailService

User = get_user_model()

class Category(models.Model):
    """Course categories like Programming, Languages, Office Suites"""
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    icon = models.CharField(max_length=50, help_text="Font Awesome icon class", default="fa-book")
    description = models.TextField(blank=True)
    order = models.IntegerField(default=0)
    
    class Meta:
        verbose_name_plural = "Categories"
        ordering = ['order', 'name']
    
    def __str__(self):
        return self.name
    
    def get_absolute_url(self):
        return reverse('category_courses', args=[self.slug])

class Course(models.Model):
    """Main course model"""
    DIFFICULTY_CHOICES = (
        ('beginner', 'مبتدئ'),
        ('intermediate', 'متوسط'),
        ('advanced', 'متقدم'),
    )
    
    # Basic Info
    title = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    description = models.TextField()
    short_description = models.CharField(max_length=300, blank=True)
    
    # Media
    thumbnail = models.ImageField(upload_to='course_thumbnails/')
    promo_video = models.FileField(upload_to='course_videos/promo/', blank=True, null=True)
    
    # Organization
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='courses')
    instructor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='courses_teaching')
    students = models.ManyToManyField(User, through='Enrollment', related_name='courses_enrolled')
    
    # Details
    difficulty = models.CharField(max_length=20, choices=DIFFICULTY_CHOICES, default='beginner')
    duration_weeks = models.IntegerField(default=4)
    language = models.CharField(max_length=50, default="Arabic")
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # Stats
    total_students = models.IntegerField(default=0)
    rating = models.DecimalField(max_digits=3, decimal_places=2, default=0)
    total_reviews = models.IntegerField(default=0)
    
    # Status
    is_published = models.BooleanField(default=False)
    published_date = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return self.title
    
    def get_absolute_url(self):
        return reverse('course_detail', args=[self.slug])
    
    def publish(self):
        """Publish the course"""
        self.is_published = True
        self.published_date = timezone.now()
        self.save()
    
    @property
    def total_modules(self):
        return self.modules.count()
    
    @property
    def total_lessons(self):
        return sum(module.lessons.count() for module in self.modules.all())

class Module(models.Model):
    """Course module/unit"""
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='modules')
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    order = models.IntegerField(default=0)
    is_free_preview = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['order']
    
    def __str__(self):
        return f"{self.course.title} - {self.title}"

class Lesson(models.Model):
    """Individual lesson within a module"""
    LESSON_TYPES = (
        ('video', 'فيديو'),
        ('text', 'نص'),
        ('quiz', 'اختبار'),
        ('pdf', 'PDF'),
    )
    
    module = models.ForeignKey(Module, on_delete=models.CASCADE, related_name='lessons')
    title = models.CharField(max_length=200)
    lesson_type = models.CharField(max_length=20, choices=LESSON_TYPES, default='video')
    order = models.IntegerField(default=0)
    duration_minutes = models.IntegerField(default=0)
    is_free_preview = models.BooleanField(default=False)
    
    # Content based on type
    # For video lessons
    video_file = models.FileField(upload_to='course_videos/lessons/', blank=True, null=True)
    video_url = models.URLField(blank=True, null=True)  # For external videos
    
    # For text lessons
    text_content = models.TextField(blank=True, null=True)
    
    # For PDF lessons
    pdf_file = models.FileField(upload_to='course_pdfs/', blank=True, null=True)
    
    # Resources
    attachments = models.FileField(upload_to='lesson_attachments/', blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['order']
    
    def __str__(self):
        return f"{self.module.title} - {self.title}"
    
    def get_content_url(self):
        """Get the appropriate content URL based on lesson type"""
        if self.lesson_type == 'video' and self.video_file:
            return self.video_file.url
        elif self.lesson_type == 'pdf' and self.pdf_file:
            return self.pdf_file.url
        return None

class Enrollment(models.Model):
    """Track student enrollment and progress"""
    STATUS_CHOICES = (
        ('active', 'نشط'),
        ('completed', 'مكتمل'),
        ('dropped', 'منسحب'),
    )
    
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='enrollments')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='enrollments')
    enrolled_date = models.DateTimeField(auto_now_add=True)
    completed_date = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    progress_percentage = models.IntegerField(default=0)
    last_accessed = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['student', 'course']
    
    def __str__(self):
        return f"{self.student.username} - {self.course.title}"
    
    def update_progress(self):
        """Calculate and update progress based on completed lessons"""
        total_lessons = self.course.total_lessons
        if total_lessons == 0:
            return
        
        completed_lessons = LessonProgress.objects.filter(
            enrollment=self,
            is_completed=True
        ).count()
        
        self.progress_percentage = int((completed_lessons / total_lessons) * 100)
        
        if self.progress_percentage == 100 and self.status != 'completed':
            self.status = 'completed'
            self.completed_date = timezone.now()
        
        self.save()

class LessonProgress(models.Model):
    """Track individual lesson completion"""
    enrollment = models.ForeignKey(Enrollment, on_delete=models.CASCADE, related_name='lesson_progress')
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE)
    is_completed = models.BooleanField(default=False)
    completed_date = models.DateTimeField(null=True, blank=True)
    last_watched_position = models.IntegerField(default=0)  # For video resume
    notes = models.TextField(blank=True)
    
    class Meta:
        unique_together = ['enrollment', 'lesson']
    
    def __str__(self):
        return f"{self.enrollment.student.username} - {self.lesson.title}"
    
    def mark_completed(self):
        """Mark lesson as completed and check for course completion"""
        if not self.is_completed:
            self.is_completed = True
            self.completed_date = timezone.now()
            self.save()
            self.enrollment.update_progress()
            
            # Check if course is now complete
            if self.enrollment.progress_percentage == 100:
                EmailService.send_course_completion_email(self.enrollment)

class Review(models.Model):
    """Course reviews and ratings"""
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='reviews')
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reviews')
    rating = models.IntegerField(choices=[(i, i) for i in range(1, 6)])
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_approved = models.BooleanField(default=True)
    
    class Meta:
        unique_together = ['course', 'student']
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.student.username} - {self.course.title} - {self.rating}★"

class Quiz(models.Model):
    """Quiz attached to a lesson"""
    lesson = models.OneToOneField(Lesson, on_delete=models.CASCADE, related_name='quiz')
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    time_limit_minutes = models.IntegerField(default=0, help_text="0 for no time limit")
    passing_score = models.IntegerField(default=70, help_text="Percentage needed to pass")
    attempts_allowed = models.IntegerField(default=1, help_text="Number of attempts allowed")
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Quiz: {self.title}"
    
    @property
    def total_questions(self):
        return self.questions.count()

class Question(models.Model):
    """Question in a quiz"""
    QUESTION_TYPES = (
        ('single', 'اختيار من متعدد (إجابة واحدة)'),
        ('multiple', 'اختيار من متعدد (إجابات متعددة)'),
        ('true_false', 'صح/خطأ'),
        ('text', 'إجابة نصية'),
    )
    
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='questions')
    question_text = models.TextField()
    question_type = models.CharField(max_length=20, choices=QUESTION_TYPES, default='single')
    points = models.IntegerField(default=1)
    order = models.IntegerField(default=0)
    
    class Meta:
        ordering = ['order']
    
    def __str__(self):
        return self.question_text[:50]

class Choice(models.Model):
    """Answer choices for questions"""
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='choices')
    choice_text = models.CharField(max_length=300)
    is_correct = models.BooleanField(default=False)
    
    def __str__(self):
        return self.choice_text

class QuizAttempt(models.Model):
    """Student's attempt at a quiz"""
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='attempts')
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='quiz_attempts')
    enrollment = models.ForeignKey(Enrollment, on_delete=models.CASCADE, related_name='quiz_attempts')
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    score = models.IntegerField(default=0)
    passed = models.BooleanField(default=False)
    attempt_number = models.IntegerField(default=1)
    
    class Meta:
        unique_together = ['quiz', 'student', 'attempt_number']
    
    def __str__(self):
        return f"{self.student.username} - {self.quiz.title} - Attempt {self.attempt_number}"

class Answer(models.Model):
    """Student's answer to a question"""
    attempt = models.ForeignKey(QuizAttempt, on_delete=models.CASCADE, related_name='answers')
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    choice = models.ForeignKey(Choice, on_delete=models.CASCADE, null=True, blank=True)
    text_answer = models.TextField(blank=True, null=True)  # For text questions
    is_correct = models.BooleanField(default=False)
    points_earned = models.IntegerField(default=0)
    
    def __str__(self):
        return f"Answer for {self.question.question_text[:50]}"

class Certificate(models.Model):
    """Certificate issued to students upon course completion"""
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='certificates')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='certificates')
    enrollment = models.OneToOneField(Enrollment, on_delete=models.CASCADE, related_name='certificate')
    certificate_number = models.CharField(max_length=100, unique=True)
    issued_date = models.DateTimeField(auto_now_add=True)
    pdf_file = models.FileField(upload_to='certificates/', blank=True, null=True)
    
    class Meta:
        unique_together = ['student', 'course']
    
    def __str__(self):
        return f"Certificate for {self.student.username} - {self.course.title}"
    
    def generate_certificate_number(self):
        import hashlib
        import time
        unique_string = f"{self.student.id}_{self.course.id}_{int(time.time())}"
        return hashlib.md5(unique_string.encode()).hexdigest()[:12].upper()

def update_progress(self):
    """Calculate and update progress based on completed lessons"""
    total_lessons = self.course.total_lessons
    if total_lessons == 0:
        return
    
    completed_lessons = LessonProgress.objects.filter(
        enrollment=self,
        is_completed=True
    ).count()
    
    self.progress_percentage = int((completed_lessons / total_lessons) * 100)
    
    if self.progress_percentage == 100 and self.status != 'completed':
        self.status = 'completed'
        self.completed_date = timezone.now()
        self.save()
        
        # Auto-generate certificate
        from .certificate_generator import generate_certificate
        from .models import Certificate
        
        certificate, created = Certificate.objects.get_or_create(
            student=self.student,
            course=self.course,
            enrollment=self,
            defaults={
                'certificate_number': Certificate.generate_certificate_number(self)
            }
        )
        
        if created:
            # Generate PDF
            pdf_path = generate_certificate(
                student_name=self.student.get_full_name() or self.student.username,
                course_title=self.course.title,
                certificate_number=certificate.certificate_number,
                issued_date=timezone.now()
            )
            
            # Save PDF file
            with open(pdf_path, 'rb') as f:
                certificate.pdf_file.save(
                    f"certificate_{certificate.certificate_number}.pdf",
                    f,
                    save=True
                )
            
            # Clean up temp file
            import os
            os.remove(pdf_path)
    
    self.save()

class Payment(models.Model):
    """Course payment transactions"""
    PAYMENT_STATUS = (
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
        ('refunded', 'Refunded'),
    )
    
    PAYMENT_METHODS = (
        ('edahabia', 'EDAHABIA (Algérie Poste)'),
        ('cib', 'CIB (SATIM)'),
    )
    
    # Relations
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='payments')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='payments')
    enrollment = models.OneToOneField('Enrollment', on_delete=models.SET_NULL, null=True, blank=True, related_name='payment')
    
    # Payment details
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default='DZD')
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS, null=True, blank=True)
    
    # Chargily specific fields
    checkout_id = models.CharField(max_length=200, blank=True, null=True)
    payment_id = models.CharField(max_length=200, blank=True, null=True)
    
    # Status tracking
    status = models.CharField(max_length=20, choices=PAYMENT_STATUS, default='pending')
    transaction_id = models.CharField(max_length=200, blank=True, null=True)
    
    # URLs
    checkout_url = models.URLField(blank=True, null=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.student.username} - {self.course.title} - {self.amount} DZD"
    
    def mark_as_paid(self, payment_id=None):
        """Mark payment as successful"""
        self.status = 'paid'
        self.paid_at = timezone.now()
        if payment_id:
            self.payment_id = payment_id
        self.save()
        
        # Create enrollment if not exists
        if not self.enrollment:
            enrollment = Enrollment.objects.create(
                student=self.student,
                course=self.course,
                status='active'
            )
            self.enrollment = enrollment
            self.save()
            
            # Update course stats
            self.course.total_students += 1
            self.course.save()

class SecurityLog(models.Model):
    """Log all security-related events"""
    EVENT_TYPES = (
        ('bot_detected', 'Bot Detected'),
        ('rate_limit', 'Rate Limit Exceeded'),
        ('suspicious_download', 'Suspicious Download'),
        ('multiple_logins', 'Multiple Device Login'),
        ('content_leak', 'Potential Content Leak'),
    )
    
    event_type = models.CharField(max_length=50, choices=EVENT_TYPES)
    ip = models.GenericIPAddressField()
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    user_agent = models.TextField()
    path = models.CharField(max_length=500)
    details = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['ip', 'created_at']),
            models.Index(fields=['event_type']),
        ]

class DeviceSession(models.Model):
    """Track active devices per user"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='devices')
    device_id = models.CharField(max_length=200, unique=True)
    device_name = models.CharField(max_length=200)
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField()
    last_active = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    
    @classmethod
    def get_active_device_count(cls, user):
        return cls.objects.filter(user=user, is_active=True).count()
    
    @classmethod
    def can_add_device(cls, user, max_devices=3):
        return cls.get_active_device_count(user) < max_devices

class ContentAccessLog(models.Model):
    """Log every content access (video, PDF, etc.)"""
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, null=True)
    content_type = models.CharField(max_length=20)  # video, pdf, quiz
    file_path = models.CharField(max_length=500)
    accessed_at = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField()
    session_id = models.CharField(max_length=200)
    
    class Meta:
        indexes = [
            models.Index(fields=['user', 'accessed_at']),
            models.Index(fields=['file_path']),
        ]
        
class CourseAnalytics(models.Model):
    """Track daily analytics for each course"""
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='analytics')
    date = models.DateField(auto_now_add=True)
    
    # Daily stats
    views = models.IntegerField(default=0)
    unique_visitors = models.IntegerField(default=0)
    enrollments = models.IntegerField(default=0)
    completions = models.IntegerField(default=0)
    
    # Revenue tracking
    revenue = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    class Meta:
        unique_together = ['course', 'date']
        ordering = ['-date']
    
    def __str__(self):
        return f"{self.course.title} - {self.date}"

class InstructorPayout(models.Model):
    """Track instructor payouts"""
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    )
    
    instructor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='payouts')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    commission_rate = models.IntegerField()  # e.g., 10 means 10%
    platform_fee = models.DecimalField(max_digits=10, decimal_places=2)
    net_amount = models.DecimalField(max_digits=10, decimal_places=2)
    
    payment_period_start = models.DateField()
    payment_period_end = models.DateField()
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    transaction_id = models.CharField(max_length=200, blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return f"{self.instructor.username} - {self.amount} DZD - {self.status}"

class Wishlist(models.Model):
    """Student's saved courses for later"""
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='wishlist_items')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='wishlisted_by')
    added_date = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['student', 'course']
        ordering = ['-added_date']
    
    def __str__(self):
        return f"{self.student.username} - {self.course.title}"

class Discussion(models.Model):
    """Q&A discussion for a course"""
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='discussions')
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='questions')
    title = models.CharField(max_length=200)
    content = models.TextField()
    is_resolved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.title} - {self.student.username}"
    
    @property
    def answers_count(self):
        return self.answers.count()

class DiscussionAnswer(models.Model):
    """Answer to a discussion question"""
    discussion = models.ForeignKey(Discussion, on_delete=models.CASCADE, related_name='answers')
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='answers')
    content = models.TextField()
    is_accepted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['created_at']
    
    def __str__(self):
        return f"Answer by {self.author.username} on {self.discussion.title}"