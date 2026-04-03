from django.urls import path
from .views import upload_resume, match_resume, get_all_resumes

urlpatterns = [
    path('upload/', upload_resume),
    path('match/', match_resume),
    path('resumes/', get_all_resumes),
]