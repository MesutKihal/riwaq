from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User


class UserRegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True, widget=forms.EmailInput(attrs={'class': 'form-control'}))
    
    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
        }
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.role = 'student'  # Force student role
        user.is_staff = False   # No admin access
        user.is_superuser = False  # No superuser access
        
        if commit:
            user.save()
        return user
    

class UserProfileForm(forms.ModelForm):
    """Basic profile information form"""
    class Meta:
        model = User
        fields = [
            'first_name', 'last_name', 'email', 'bio', 
            'profile_picture', 'phone_number', 'country', 'city'
        ]
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'الاسم الأول'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'الاسم الأخير'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'البريد الإلكتروني'}),
            'bio': forms.Textarea(attrs={'rows': 4, 'class': 'form-control', 'placeholder': 'اكتب نبذة عن نفسك...'}),
            'profile_picture': forms.FileInput(attrs={'class': 'form-control'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+213 XX XXX XXXX'}),
            'country': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'الدولة'}),
            'city': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'المدينة'}),
        }

class InstructorProfileForm(forms.ModelForm):
    """Extended profile for instructors"""
    class Meta:
        model = User
        fields = [
            'instructor_bio', 'expertise_areas', 'years_experience',
            'company', 'position', 'website', 'github', 'linkedin', 'twitter'
        ]
        widgets = {
            'instructor_bio': forms.Textarea(attrs={'rows': 4, 'class': 'form-control', 'placeholder': 'نبذة مهنية عن خبراتك...'}),
            'expertise_areas': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'تطوير ويب, ذكاء اصطناعي, بايثون, ...'}),
            'years_experience': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'عدد سنوات الخبرة'}),
            'company': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'الشركة / المؤسسة'}),
            'position': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'المسمى الوظيفي'}),
            'website': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'https://your-website.com'}),
            'github': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'https://github.com/username'}),
            'linkedin': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'https://linkedin.com/in/username'}),
            'twitter': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'https://twitter.com/username'}),
        }

class ChangePasswordForm(forms.Form):
    """Change password form"""
    old_password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control'}), label='كلمة المرور الحالية')
    new_password1 = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control'}), label='كلمة المرور الجديدة')
    new_password2 = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control'}), label='تأكيد كلمة المرور الجديدة')
    
    def clean(self):
        cleaned_data = super().clean()
        new_password1 = cleaned_data.get('new_password1')
        new_password2 = cleaned_data.get('new_password2')
        
        if new_password1 and new_password2 and new_password1 != new_password2:
            raise forms.ValidationError("كلمات المرور غير متطابقة")
        return cleaned_data