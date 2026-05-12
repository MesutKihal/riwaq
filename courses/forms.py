from django import forms
from .models import Course, Module, Lesson, Category, Quiz, Choice, Question
from django.utils.text import slugify


class CourseForm(forms.ModelForm):
    """Fixed course form with proper validation"""
    
    class Meta:
        model = Course
        fields = [
            'title', 'slug', 'description', 'short_description',
            'thumbnail', 'promo_video', 'category', 'difficulty',
            'duration_weeks', 'language', 'price', 'is_published'
        ]
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'مثال: دورة احتراف بايثون'}),
            'slug': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'python-professional-course'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 5, 'placeholder': 'وصف مفصل للدورة...'}),
            'short_description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'وصف قصير يظهر في بطاقات الدورة'}),
            'thumbnail': forms.FileInput(attrs={'class': 'form-control'}),
            'promo_video': forms.FileInput(attrs={'class': 'form-control'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'difficulty': forms.Select(attrs={'class': 'form-select'}),
            'duration_weeks': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'language': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'العربية'}),
            'price': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'step': 100, 'placeholder': '0 للدورات المجانية'}),
            'is_published': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make slug optional - we'll auto-generate it if empty
        self.fields['slug'].required = False
    
    def clean_slug(self):
        slug = self.cleaned_data.get('slug')
        title = self.cleaned_data.get('title')
        
        # Auto-generate slug from title if not provided
        if not slug and title:
            slug = slugify(title)
        
        # Check uniqueness
        if slug:
            instance = getattr(self, 'instance', None)
            if instance and instance.pk:
                if Course.objects.filter(slug=slug).exclude(pk=instance.pk).exists():
                    raise forms.ValidationError('هذا المعرف مستخدم بالفعل. الرجاء استخدام معرف آخر.')
            elif Course.objects.filter(slug=slug).exists():
                raise forms.ValidationError('هذا المعرف مستخدم بالفعل. الرجاء استخدام معرف آخر.')
        
        return slug
    
    def clean_title(self):
        title = self.cleaned_data.get('title')
        if not title:
            raise forms.ValidationError('عنوان الدورة مطلوب')
        return title
    
    def clean_description(self):
        description = self.cleaned_data.get('description')
        if not description:
            raise forms.ValidationError('وصف الدورة مطلوب')
        return description
    
    def clean_category(self):
        category = self.cleaned_data.get('category')
        if not category:
            raise forms.ValidationError('التصنيف مطلوب')
        return category
    
    def clean_price(self):
        price = self.cleaned_data.get('price')
        if price is None:
            return 0
        if price < 0:
            raise forms.ValidationError('السعر لا يمكن أن يكون سالباً')
        return price
class ModuleForm(forms.ModelForm):
    class Meta:
        model = Module
        fields = ['title', 'description', 'is_free_preview']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'modern-input',
                'placeholder': 'مثال: مقدمة في البرمجة'
            }),
            'description': forms.Textarea(attrs={
                'class': 'modern-textarea',
                'rows': 3,
                'placeholder': 'وصف الوحدة...'
            }),
            'is_free_preview': forms.CheckboxInput(attrs={
                'class': 'modern-checkbox'
            }),
        }

class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True

class MultipleFileField(forms.FileField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", MultipleFileInput())
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        single_file_clean = super().clean
        if isinstance(data, (list, tuple)):
            result = [single_file_clean(d, initial) for d in data]
        else:
            result = single_file_clean(data, initial)
        return result


class LessonForm(forms.ModelForm):
    class Meta:
        model = Lesson
        fields = [
            'title', 'lesson_type', 'duration_minutes', 'is_free_preview',
            'video_file', 'video_url', 'text_content', 'pdf_file', 'attachments'
        ]
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'modern-input',
                'placeholder': 'مثال: تثبيت بيئة العمل'
            }),
            'lesson_type': forms.Select(attrs={
                'class': 'modern-select',
                'id': 'lesson-type-select'
            }),
            'duration_minutes': forms.NumberInput(attrs={
                'class': 'modern-input',
                'min': 1,
                'placeholder': 'المدة بالدقائق'
            }),
            'is_free_preview': forms.CheckboxInput(attrs={
                'class': 'modern-checkbox'
            }),
            'video_file': forms.FileInput(attrs={
                'class': 'modern-file-input',
                'accept': 'video/*',
                'data-preview': 'video-preview'
            }),
            'video_url': forms.URLInput(attrs={
                'class': 'modern-input',
                'placeholder': 'https://www.youtube.com/watch?v=...'
            }),
            'text_content': forms.Textarea(attrs={
                'class': 'modern-textarea rich-editor',
                'rows': 12,
                'placeholder': 'اكتب محتوى الدرس هنا...'
            }),
            'pdf_file': forms.FileInput(attrs={
                'class': 'modern-file-input',
                'accept': '.pdf',
                'data-preview': 'pdf-preview'
            }),
            'attachments': MultipleFileInput(attrs={
                'class': 'modern-file-input',
                'multiple': True
            }),
        }

class QuizForm(forms.ModelForm):
    class Meta:
        model = Quiz
        fields = ['title', 'description', 'time_limit_minutes', 'passing_score', 'attempts_allowed']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'time_limit_minutes': forms.NumberInput(attrs={'class': 'form-control'}),
            'passing_score': forms.NumberInput(attrs={'class': 'form-control'}),
            'attempts_allowed': forms.NumberInput(attrs={'class': 'form-control'}),
        }

class QuestionForm(forms.ModelForm):
    class Meta:
        model = Question
        fields = ['question_text', 'question_type', 'points', 'order']
        widgets = {
            'question_text': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'question_type': forms.Select(attrs={'class': 'form-select'}),
            'points': forms.NumberInput(attrs={'class': 'form-control'}),
            'order': forms.NumberInput(attrs={'class': 'form-control'}),
        }

class ChoiceForm(forms.ModelForm):
    class Meta:
        model = Choice
        fields = ['choice_text', 'is_correct']
        widgets = {
            'choice_text': forms.TextInput(attrs={'class': 'form-control'}),
            'is_correct': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }