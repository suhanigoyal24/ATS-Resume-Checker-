from rest_framework.decorators import api_view
from rest_framework.response import Response
from .models import Resume
from .utils import get_text, calculate_similarity
from django.http import JsonResponse

def home(request):
    return JsonResponse({
        "message": "ATS Checker Backend is Running"
    })

@api_view(['POST'])
def upload_resume(request):
    file = request.FILES.get('file')
    name = request.data.get('name', 'Unknown')

    text = get_text(file)

    resume = Resume.objects.create(
        name=name,
        file=file,
        extracted_text=text
    )

    return Response({
        "message": "Resume uploaded successfully",
        "resume_id": resume.id
    })


@api_view(['POST'])
def match_resume(request):
    resume_id = request.data.get('resume_id')
    job_description = request.data.get('job_description')

    try:
        resume = Resume.objects.get(id=resume_id)
    except:
        return Response({"error": "Resume not found"}, status=404)

    score = calculate_similarity(resume.extracted_text, job_description)

    resume.match_score = score
    resume.save()

    return Response({
        "resume": resume.name,
        "match_score": score
    })


@api_view(['GET'])
def get_all_resumes(request):
    resumes = Resume.objects.all().order_by('-match_score')

    data = []
    for r in resumes:
        data.append({
            "id": r.id,
            "name": r.name,
            "score": r.match_score
        })

    return Response(data)