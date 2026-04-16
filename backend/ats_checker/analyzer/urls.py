from django.urls import path
from .views import upload_resume, list_candidates , ml_analyze  # Import all three functions

urlpatterns = [
    path('upload/', upload_resume, name='upload_resume'),           # POST /api/upload/
    path('candidates/', list_candidates, name='list_candidates'),   # GET /api/candidates/
    path('ml-analyze/', ml_analyze, name='ml-analyze')
]
