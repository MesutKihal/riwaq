from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.urls import reverse

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
        """Mark lesson as completed"""
        if not self.is_completed:
            self.is_completed = True
            self.completed_date = timezone.now()
            self.save()
            self.enrollment.update_progress()

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