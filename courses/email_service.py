from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from celery import shared_task

class EmailService:
    """Handle all email notifications"""
    
    @staticmethod
    def send_welcome_email(user):
        """Send welcome email to new user"""
        context = {
            'user': user,
            'course_catalog_url': f"{settings.SITE_URL}/catalog/",
            'support_url': f"{settings.SITE_URL}/contact/"
        }
        
        html_content = render_to_string('emails/welcome_email.html', context)
        text_content = strip_tags(html_content)
        
        send_mail(
            subject='مرحباً بك في رواق',
            message=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=html_content,
            fail_silently=False
        )
    
    @staticmethod
    def send_payment_confirmation(payment):
        """Send payment confirmation email"""
        context = {
            'student_name': payment.student.get_full_name() or payment.student.username,
            'course': payment.course,
            'amount': payment.amount,
            'payment_date': payment.paid_at.strftime('%Y-%m-%d %H:%M'),
            'transaction_id': payment.transaction_id or payment.payment_id,
            'course_url': f"{settings.SITE_URL}/course/{payment.course.slug}/learn/"
        }
        
        html_content = render_to_string('emails/payment_confirmation.html', context)
        text_content = strip_tags(html_content)
        
        send_mail(
            subject=f'تأكيد الدفع - {payment.course.title}',
            message=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[payment.student.email],
            html_message=html_content
        )
    
    @staticmethod
    def send_course_completion_email(enrollment):
        """Send course completion certificate email"""
        context = {
            'student_name': enrollment.student.get_full_name() or enrollment.student.username,
            'course': enrollment.course,
            'completion_percentage': enrollment.progress_percentage,
            'certificate_url': f"{settings.SITE_URL}/certificate/{enrollment.course.slug}/download/",
            'course_catalog_url': f"{settings.SITE_URL}/catalog/",
            'share_url': f"{settings.SITE_URL}/course/{enrollment.course.slug}/share/"
        }
        
        html_content = render_to_string('emails/course_completion.html', context)
        text_content = strip_tags(html_content)
        
        send_mail(
            subject=f'🎉 تهانينا! أكملت دورة {enrollment.course.title}',
            message=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[enrollment.student.email],
            html_message=html_content
        )
    
    @staticmethod
    def send_instructor_payout_notification(instructor, amount):
        """Notify instructor about payout"""
        context = {
            'instructor_name': instructor.get_full_name() or instructor.username,
            'amount': amount,
            'dashboard_url': f"{settings.SITE_URL}/instructor/dashboard/"
        }
        
        html_content = render_to_string('emails/instructor_payout.html', context)
        text_content = strip_tags(html_content)
        
        send_mail(
            subject='تحديث الأرباح - رواق',
            message=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[instructor.email],
            html_message=html_content
        )
    
    @staticmethod
    def send_new_enrollment_notification(instructor, student, course):
        """Notify instructor about new enrollment"""
        context = {
            'instructor_name': instructor.get_full_name() or instructor.username,
            'student_name': student.get_full_name() or student.username,
            'course': course,
            'course_url': f"{settings.SITE_URL}/course/{course.slug}/",
            'total_students': course.total_students
        }
        
        html_content = render_to_string('emails/new_enrollment.html', context)
        text_content = strip_tags(html_content)
        
        send_mail(
            subject=f'📚 طالب جديد في دورتك {course.title}',
            message=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[instructor.email],
            html_message=html_content
        )