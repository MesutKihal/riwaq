from django.urls import path
from . import views

app_name = 'courses'

urlpatterns = [
    # Home & Catalog
    path('', views.home_view, name='home'),
    path('catalog/', views.course_catalog, name='course_catalog'),
    path('category/<slug:slug>/', views.category_courses, name='category_courses'),

    
    # Enrollment
    path('course/<slug:slug>/enroll/', views.enroll_course, name='enroll_course'),
    
    # Student Dashboard
    path('my-courses/', views.my_courses, name='my_courses'),
    path('my-progress/', views.my_progress, name='my_progress'),
    
    # Instructor Dashboard - SPECIFIC paths FIRST
    path('instructor/dashboard/', views.instructor_dashboard, name='instructor_dashboard'),
    path('instructor/course/create/', views.course_create, name='course_create'),
    path('instructor/course/<slug:slug>/edit/', views.course_edit, name='course_edit'),
    path('instructor/course/<slug:slug>/delete/', views.course_delete, name='course_delete'),
    path('instructor/course/<slug:slug>/module/add/', views.module_add, name='module_add'),
    path('instructor/module/<int:module_id>/edit/', views.module_edit, name='module_edit'),
    path('instructor/module/<int:module_id>/delete/', views.module_delete, name='module_delete'),
    path('instructor/module/<int:module_id>/lesson/add/', views.lesson_add, name='lesson_add'),
    path('instructor/lesson/<int:lesson_id>/edit/', views.lesson_edit, name='lesson_edit'),
    path('instructor/lesson/<int:lesson_id>/delete/', views.lesson_delete, name='lesson_delete'),
    
    # Course Detail - GENERAL path LAST
    path('course/<slug:slug>/', views.course_detail, name='course_detail'),
    path('course/<slug:slug>/learn/', views.course_learn, name='course_learn'),
    path('course/<slug:slug>/lesson/<int:lesson_id>/', views.lesson_view, name='lesson_view'),
    path('course/<slug:slug>/enroll/', views.enroll_course, name='enroll_course'),
    
    # API endpoints
    path('api/lesson-complete/', views.mark_lesson_complete, name='mark_lesson_complete'),
    path('api/courses-data/', views.courses_json_data, name='courses_json_data'),

    # Video streaming
    path('stream/<path:file_path>/', views.stream_video, name='stream_video'),
    path('api/save-video-progress/', views.save_video_progress, name='save_video_progress'),

    # Certificate
    path('certificate/<slug:slug>/download/', views.download_certificate, name='download_certificate'),

    # Payment URLs
    path('payment/course/<slug:slug>/', views.initiate_payment, name='initiate_payment'),
    path('payment/success/', views.payment_success, name='payment_success'),
    path('payment/failure/', views.payment_failure, name='payment_failure'),
    path('payment/webhook/', views.payment_webhook, name='payment_webhook'),

    # Add Review
    path('course/<slug:slug>/review/', views.add_review, name='add_review'),

    # Request Payout
    path('instructor/request-payout/', views.request_payout, name='request_payout'),
    path('api/categories-data/', views.categories_json_data, name='categories_json_data'),

    # Wishlist
    path('wishlist/', views.wishlist_view, name='wishlist'),
    path('wishlist/toggle/<slug:slug>/', views.toggle_wishlist, name='toggle_wishlist'),

    # Discussions
    path('course/<slug:slug>/discussions/', views.discussion_list, name='discussion_list'),
    path('discussion/<int:discussion_id>/', views.discussion_detail, name='discussion_detail'),
    path('course/<slug:slug>/ask/', views.ask_question, name='ask_question'),
    path('discussion/accept/<int:answer_id>/', views.accept_answer, name='accept_answer'),
]