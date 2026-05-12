from django.core.cache import cache
from django.http import JsonResponse
import re
from .models import CourseAnalytics
from .models import DeviceSession
from django.utils import timezone

class AntiScrapingMiddleware:
    """Detect and block bots and scrapers"""
    
    BOT_PATTERNS = [
        r'(?i)python-requests',
        r'(?i)scrapy',
        r'(?i)selenium',
        r'(?i)headless',
        r'(?i)phantomjs',
        r'(?i)curl',
        r'(?i)wget',
    ]
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        
        # Check for bot patterns
        for pattern in self.BOT_PATTERNS:
            if re.search(pattern, user_agent):
                # Log suspicious activity
                self.log_suspicious_request(request)
                return JsonResponse({'error': 'Access denied'}, status=403)
        
        # Rate limiting
        ip = request.META.get('REMOTE_ADDR')
        key = f"rate_limit_{ip}"
        requests_count = cache.get(key, 0)
        
        if requests_count > 100:  # 100 requests per minute
            return JsonResponse({'error': 'Rate limit exceeded'}, status=429)
        
        cache.set(key, requests_count + 1, 60)
        
        return self.get_response(request)
    
    def log_suspicious_request(self, request):
        """Log suspicious activity for review"""
        from .models import SecurityLog
        
        SecurityLog.objects.create(
            ip=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT'),
            path=request.path,
            method=request.method
        )

class DeviceLimitMiddleware:
    """Limit number of active devices per user"""
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        if request.user.is_authenticated:
            device_id = request.session.get('device_id')
            
            if not device_id:
                # Generate new device ID
                import uuid
                device_id = str(uuid.uuid4())
                request.session['device_id'] = device_id
            
            # Check device limit
            if not DeviceSession.can_add_device(request.user):
                # Revoke oldest session
                oldest = DeviceSession.objects.filter(
                    user=request.user, 
                    is_active=True
                ).order_by('last_active').first()
                if oldest:
                    oldest.is_active = False
                    oldest.save()
            
            # Update or create device session
            DeviceSession.objects.update_or_create(
                device_id=device_id,
                defaults={
                    'user': request.user,
                    'device_name': request.META.get('HTTP_USER_AGENT', 'Unknown')[:200],
                    'ip_address': request.META.get('REMOTE_ADDR'),
                    'user_agent': request.META.get('HTTP_USER_AGENT', ''),
                    'is_active': True
                }
            )
        
        return self.get_response(request)

class CourseAnalyticsMiddleware:
    """Track course views and unique visitors"""
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        response = self.get_response(request)
        
        # Track course detail views
        if request.path.startswith('/course/') and 'course' in request.resolver_match.url_name:
            from .models import Course
            slug = request.resolver_match.kwargs.get('slug')
            
            if slug:
                try:
                    course = Course.objects.get(slug=slug)
                    today = timezone.now().date()
                    
                    analytics, created = CourseAnalytics.objects.get_or_create(
                        course=course,
                        date=today
                    )
                    
                    analytics.views += 1
                    
                    # Track unique visitors by session
                    session_key = f'visited_course_{course.id}'
                    if not request.session.get(session_key):
                        analytics.unique_visitors += 1
                        request.session[session_key] = True
                    
                    analytics.save()
                    
                except Course.DoesNotExist:
                    pass
        
        return response