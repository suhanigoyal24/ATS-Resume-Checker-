from django.db import models

# Create your models here.

class Resume(models.Model):
    name = models.CharField(max_length=255)
    file = models.FileField(upload_to='resumes/')
    extracted_text = models.TextField()
    match_score = models.FloatField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name