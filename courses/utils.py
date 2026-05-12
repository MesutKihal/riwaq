from django.core.files.storage import default_storage
from django.conf import settings
import mimetypes
import hashlib
import time
import hmac



def get_video_streaming_url(file_path):
    """
    Get optimized streaming URL for videos
    Supports seeking and partial content (HTTP Range requests)
    """
    if settings.DEBUG:
        return default_storage.url(file_path)
    else:
        # For R2, return direct URL with proper headers
        return f"{settings.MEDIA_URL}{file_path}"

def get_file_size(file_path):
    """Get file size in bytes"""
    if default_storage.exists(file_path):
        return default_storage.size(file_path)
    return 0

def get_mime_type(file_path):
    """Get MIME type for file"""
    mime_type, _ = mimetypes.guess_type(file_path)
    return mime_type or 'application/octet-stream'

def delete_file(file_path):
    """Delete file from storage"""
    if default_storage.exists(file_path):
        default_storage.delete(file_path)
        return True
    return False

def generate_signed_url(file_path, expiry_seconds=3600):
    """Generate a time-limited signed URL for video access"""
    expiry = int(time.time()) + expiry_seconds
    signature = hmac.new(
        settings.SECRET_KEY.encode('utf-8'),
        f"{file_path}{expiry}".encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    
    return f"/api/stream/{file_path}?expiry={expiry}&signature={signature}"

def verify_signed_url(file_path, expiry, signature):
    """Verify signed URL before serving content"""
    if int(expiry) < time.time():
        return False
    
    expected = hmac.new(
        settings.SECRET_KEY.encode('utf-8'),
        f"{file_path}{expiry}".encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(signature, expected)