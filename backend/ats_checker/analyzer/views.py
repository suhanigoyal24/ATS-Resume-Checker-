# analyzer/views.py
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from django.core.files.storage import default_storage
from django.conf import settings
import os, re
from .models import Candidate, JobDescription, MatchScore
from .utils import extract_text_from_file, extract_skills, calculate_weighted_score, nlp
from django.apps import apps

# Simple keyword extractor (replace with your NLP logic)
def extract_keywords(text, max_keywords=30):
    """Extract meaningful keywords from text for matching"""
    # Basic tokenization + filtering
    words = re.findall(r'\b[A-Za-z]{3,20}\b', text.lower())
    # Common stopwords to remove
    stopwords = {
        'the', 'and', 'for', 'with', 'this', 'that', 'you', 'are', 'will', 'can',
        'have', 'has', 'had', 'was', 'were', 'been', 'being', 'are', 'is', 'am',
        'from', 'into', 'through', 'during', 'before', 'after', 'above', 'below',
        'between', 'under', 'again', 'further', 'then', 'once', 'here', 'there',
        'when', 'where', 'why', 'how', 'all', 'each', 'few', 'more', 'most',
        'other', 'some', 'such', 'no', 'nor', 'not', 'only', 'own', 'same', 'so',
        'than', 'too', 'very', 'just', 'also', 'now', 'our', 'your', 'they', 'them',
        'which', 'who', 'what', 'would', 'could', 'should', 'may', 'might', 'must'
    }
    # Count frequency and return top keywords
    from collections import Counter
    filtered = [w for w in words if w not in stopwords]
    return [word for word, _ in Counter(filtered).most_common(max_keywords)]

@api_view(['POST'])
@permission_classes([AllowAny])
def upload_resume(request):
    if request.method != 'POST':
        return Response({"error": "Method not allowed"}, status=status.HTTP_405_METHOD_NOT_ALLOWED)
    
    resume = request.FILES.get('resume')
    job_description_text = request.data.get('job_description')
    
    if not resume or not job_description_text:
        return Response({"error": "Missing resume or job description"}, status=status.HTTP_400_BAD_REQUEST)
    
    # Validate file type
    file_ext = os.path.splitext(resume.name)[1].lower()
    if file_ext not in ['.pdf', '.docx', '.doc']:
        return Response({"error": "Unsupported file type"}, status=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE)
    
    # Save file temporarily
    file_path = default_storage.save(f"resumes/{resume.name}", resume)
    full_path = os.path.join(settings.MEDIA_ROOT, file_path)
    
    try:
        # Extract & process
        resume_text = extract_text_from_file(full_path, file_ext[1:])
        if not resume_text.strip():
            return Response({"error": "Could not extract text from resume"}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)
        
        # Extract skills (your existing function)
        resume_skills = extract_skills(resume_text)
        job_skills = extract_skills(job_description_text)
        
        # Extract keywords for matching (new)
        resume_keywords = extract_keywords(resume_text)
        job_keywords = extract_keywords(job_description_text)
        
        # Calculate matches
        matched_keywords = list(set(resume_keywords) & set(job_keywords))
        missing_keywords = list(set(job_keywords) - set(resume_keywords))
        
        # Parse with spaCy for experience/education heuristics
        resume_doc = nlp(resume_text)
        job_doc = nlp(job_description_text)
        
        # Calculate base score
        base_result = calculate_weighted_score(
            resume_text, job_description_text,
            resume_skills, job_skills,
            resume_doc, job_doc
        )
        
        # Build section scores (enhanced)
        keyword_match_rate = len(matched_keywords) / max(len(job_keywords), 1)
        skill_match_rate = len(set(resume_skills) & set(job_skills)) / max(len(job_skills), 1)
        
        section_scores = {
            "skills": min(100, round(skill_match_rate * 100 + 5)),
            "experience": min(100, round(base_result['score'] * 0.9)),
            "education": min(100, round(base_result['score'] * 0.85 + 10)),
            "keywords": min(100, round(keyword_match_rate * 100))
        }
        
        # Generate AI-style recommendations
        recommendations = []
        if missing_keywords:
            recommendations.append(f"Add missing keywords: {', '.join(missing_keywords[:3])}")
        if base_result['score'] < 70:
            recommendations.append("Quantify achievements with metrics (e.g., 'Increased X by 40%')")
        if len(resume_skills) < len(job_skills) * 0.7:
            recommendations.append("Highlight more technical skills from the job description")
        recommendations.append("Use standard section headings: Experience, Skills, Education")
        
        # Final score (weighted average)
        final_score = round(
            base_result['score'] * 0.6 + 
            keyword_match_rate * 100 * 0.25 + 
            skill_match_rate * 100 * 0.15, 
            1
        )
        
        # Build structured response
        response_data = {
            "id": None,  # Will be set after DB save
            "name": resume.name.rsplit('.', 1)[0],
            "score": final_score,
            "skills": list(set(resume_skills)),
            "matched_keywords": matched_keywords,
            "resume_url": f"/media/{file_path}",
            "match_report": {
                "matched_keywords": matched_keywords,
                "missing_keywords": missing_keywords[:15],  # Limit for UI
                "section_scores": section_scores,
                "recommendations": recommendations[:4]  # Top 4 tips
            }
        }
        
        # Save to DB
        candidate = Candidate.objects.create(
            name=response_data['name'],
            resume_file=file_path,
            extracted_text=resume_text[:5000],
            extracted_skills=resume_skills
        )
        response_data['id'] = candidate.id
        response_data['resume_url'] = f"http://127.0.0.1:8000/media/{file_path}"
        
        MatchScore.objects.create(
            candidate=candidate,
            score=final_score/100,
            missing_skills=missing_keywords
        )
        
        return Response(response_data, status=status.HTTP_200_OK)
        
    except Exception as e:
        print(f"[CRITICAL ERROR] {str(e)}")
        return Response({"error": "Processing failed", "details": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    finally:
        # Cleanup temp file
        if os.path.exists(full_path):
            os.remove(full_path)


# analyzer/views.py — ADD THIS NEW FUNCTION

@api_view(['GET'])
@permission_classes([AllowAny])
def list_candidates(request):
    """Return all candidates for dashboard display"""
    try:
        candidates = Candidate.objects.all().order_by('-id')  # Newest first
        
        # Build response with match_report if available
        results = []
        for c in candidates:
            # Get latest MatchScore if exists
            match_score = MatchScore.objects.filter(candidate=c).first()
            
            candidate_data = {
                "id": c.id,
                "name": c.name,
                "score": round((match_score.score * 100) if match_score else 0, 1),
                "skills": c.extracted_skills or [],
                "resume_url": f"http://127.0.0.1:8000{c.resume_file}" if c.resume_file else None,
            }
            
            # Add match_report if we have missing skills
            if match_score and match_score.missing_skills:
                candidate_data["match_report"] = {
                    "matched_keywords": [s for s in (c.extracted_skills or []) if s not in (match_score.missing_skills or [])],
                    "missing_keywords": match_score.missing_skills or [],
                    "section_scores": {
                        "skills": 70,  # Placeholder — replace with real calculation
                        "experience": 65,
                        "education": 75,
                        "keywords": 60
                    },
                    "recommendations": [
                        f"Add missing skills: {', '.join(match_score.missing_skills[:3])}" if match_score.missing_skills else "Great skill coverage!",
                        "Quantify achievements with metrics",
                        "Use standard section headings"
                    ]
                }
            
            results.append(candidate_data)
        
        return Response(results, status=status.HTTP_200_OK)
        
    except Exception as e:
        print(f"[ERROR] list_candidates: {str(e)}")
        return Response({"error": "Failed to load candidates"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    

#=============== Machine Learning Endpoint ===============
@api_view(['POST'])
@permission_classes([AllowAny])
def ml_analyze(request):
    import traceback  # Add this import at top of function for debugging
    
    resume_file = request.FILES.get('resume')
    jd = request.data.get('job_description', '').strip()

    if not resume_file or not jd:
        return Response({"error": "Missing 'resume' file or 'job_description'"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        # Save file temporarily
        file_ext = os.path.splitext(resume_file.name)[1].lower().replace('.', '')
        file_path = default_storage.save(f"temp_ml/{resume_file.name}", resume_file)
        full_path = os.path.join(settings.MEDIA_ROOT, file_path)
        print(f"[DEBUG] Saved temp file: {full_path}")

        # Extract text using YOUR existing function
        print(f"[DEBUG] Calling extract_text_from_file('{full_path}', '{file_ext}')")
        resume_text = extract_text_from_file(full_path, file_ext)
        print(f"[DEBUG] Extracted text length: {len(resume_text) if resume_text else 0}")
        
        if not resume_text or not resume_text.strip():
            return Response({"error": "Could not extract text"}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)

        # Get ML engine
        print("[DEBUG] Getting ML engine from app config...")
        engine = apps.get_app_config('analyzer').ats_engine
        print(f"[DEBUG] Engine loaded: {type(engine).__name__}")

        # Run inference
        print("[DEBUG] Running inference...")
        score = engine.score(resume_text, jd)
        matched = engine.keywords(resume_text, jd)
        verdict = "Shortlist" if score >= 60 else "Review"
        print(f"[DEBUG] Score: {score}, Matched: {len(matched)} keywords")

        # SAVE TO DATABASE
        from .models import MLAnalysis
        ml_record = MLAnalysis.objects.create(
            resume_filename=resume_file.name,
            job_description=jd,
            ml_score=score,
            matched_keywords=matched,
            verdict=verdict,
            method="tfidf_cosine"
        )
        print(f"[DEBUG] Saved to DB with ID: {ml_record.id}")

        return Response({
            "match_score_percent": score,
            "matched_keywords": matched,
            "verdict": verdict,
            "method": "tfidf_cosine",
            "analysis_id": ml_record.id,
            "message": "Analysis saved to database"
        }, status=status.HTTP_200_OK)

    except Exception as e:
        # 🔥 PRINT FULL TRACEBACK FOR DEBUGGING
        print(f"\n{'='*60}")
        print(f"❌ [ML_ANALYZE CRASH] {type(e).__name__}: {str(e)}")
        print(f"{'='*60}")
        print(traceback.format_exc())
        print(f"{'='*60}\n")
        
        return Response({
            "error": "ML analysis failed", 
            "error_type": type(e).__name__,
            "details": str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    finally:
        # Cleanup
        if 'full_path' in locals() and os.path.exists(full_path):
            try:
                os.remove(full_path)
                default_storage.delete(file_path)
                print("[DEBUG] Cleaned up temp file")
            except Exception as cleanup_err:
                print(f"[DEBUG] Cleanup warning: {cleanup_err}")