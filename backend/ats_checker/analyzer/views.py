# analyzer/views.py
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from django.core.files.storage import default_storage
from django.conf import settings
from django.utils import timezone
from django.db.models import Avg
import os, re, traceback
from .models import Candidate, JobDescription, MatchScore, MLAnalysis
from .utils import extract_text_from_file, extract_skills, calculate_weighted_score, nlp
from django.apps import apps

# Optional: Try to import ML predictor (won't crash if missing)
try:
    from .ml_engine.ml_predictor import ATSMLPredictor
    ml_predictor = ATSMLPredictor()
except:
    ml_predictor = None  # Fallback to traditional scoring

# Simple keyword extractor
def extract_keywords(text, max_keywords=30):
    """Extract meaningful keywords from text for matching"""
    words = re.findall(r'\b[A-Za-z]{3,20}\b', text.lower())
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
    from collections import Counter
    filtered = [w for w in words if w not in stopwords]
    return [word for word, _ in Counter(filtered).most_common(max_keywords)]


# =============== ATS UPLOAD ENDPOINT (SINGLE SCORE) ===============
@api_view(['POST'])
@permission_classes([AllowAny])
def upload_resume(request):
    if request.method != 'POST':
        return Response({"error": "Method not allowed"}, status=status.HTTP_405_METHOD_NOT_ALLOWED)
    
    resume = request.FILES.get('resume')
    job_description_text = request.data.get('job_description')
    
    if not resume or not job_description_text:
        return Response({"error": "Missing resume or job description"}, status=status.HTTP_400_BAD_REQUEST)
    
    file_ext = os.path.splitext(resume.name)[1].lower()
    if file_ext not in ['.pdf', '.docx', '.doc']:
        return Response({"error": "Unsupported file type"}, status=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE)
    
    file_path = default_storage.save(f"resumes/{resume.name}", resume)
    full_path = os.path.join(settings.MEDIA_ROOT, file_path)
    
    try:
        resume_text = extract_text_from_file(full_path, file_ext[1:])
        if not resume_text.strip():
            return Response({"error": "Could not extract text from resume"}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)
        
        resume_skills = extract_skills(resume_text)
        job_skills = extract_skills(job_description_text)
        resume_keywords = extract_keywords(resume_text)
        job_keywords = extract_keywords(job_description_text)
        
        matched_keywords = list(set(resume_keywords) & set(job_keywords))
        missing_keywords = list(set(job_keywords) - set(resume_keywords))
        
        # Traditional scoring (baseline)
        resume_doc = nlp(resume_text)
        job_doc = nlp(job_description_text)
        base_result = calculate_weighted_score(
            resume_text, job_description_text,
            resume_skills, job_skills,
            resume_doc, job_doc
        )
        
        keyword_match_rate = len(matched_keywords) / max(len(job_keywords), 1)
        skill_match_rate = len(set(resume_skills) & set(job_skills)) / max(len(job_skills), 1)
        
        # ML Scoring (if available) — Single blended score
        if ml_predictor:
            try:
                ml_result = ml_predictor.predict(resume_text, job_description_text)
                ml_score = ml_result['score']
                # Blend: 85% ML + 15% traditional for stability
                final_score = round(ml_score * 0.85 + base_result['score'] * 0.15, 1)
            except:
                # ML failed → fallback to traditional
                final_score = base_result['score']
        else:
            # No ML → use traditional
            final_score = base_result['score']
        
        # Section scores for UI
        section_scores = {
            "skills": min(100, round(skill_match_rate * 100 + 5)),
            "experience": min(100, round(final_score * 0.9)),
            "education": min(100, round(final_score * 0.85 + 10)),
            "keywords": min(100, round(keyword_match_rate * 100))
        }
        
        # Recommendations
        recommendations = []
        if missing_keywords:
            recommendations.append(f"Add missing keywords: {', '.join(missing_keywords[:3])}")
        if final_score < 70:
            recommendations.append("Quantify achievements with metrics (e.g., 'Increased X by 40%')")
        if len(resume_skills) < len(job_skills) * 0.7:
            recommendations.append("Highlight more technical skills from the job description")
        recommendations.append("Use standard section headings: Experience, Skills, Education")
        
        # Response: ONLY ONE SCORE (no ml_score/traditional_score fields)
        response_data = {
            "id": None,
            "name": resume.name.rsplit('.', 1)[0],
            "score": final_score,  # ONLY ONE FINAL SCORE
            "skills": list(set(resume_skills)),
            "matched_keywords": matched_keywords[:20],
            "resume_url": f"/media/{file_path}",
            "match_report": {
                "matched_keywords": matched_keywords[:15],
                "missing_keywords": missing_keywords[:15],
                "section_scores": section_scores,
                "recommendations": recommendations[:4],
                "scoring_method": "ml_hybrid" if ml_predictor else "traditional"
            }
        }
        
        # Save to database
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
            score=final_score/100,  # Store as 0.0-1.0
            missing_skills=missing_keywords,
            matched_skills=matched_keywords
        )
        
        return Response(response_data, status=status.HTTP_200_OK)
        
    except Exception as e:
        print(f"[CRITICAL ERROR] {str(e)}")
        traceback.print_exc()
        return Response({"error": "Processing failed", "details": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    finally:
        if os.path.exists(full_path):
            try:
                os.remove(full_path)
                default_storage.delete(file_path)
            except:
                pass


# =============== LIST CANDIDATES (Legacy) ===============
@api_view(['GET'])
@permission_classes([AllowAny])
def list_candidates(request):
    """Return all candidates for dashboard display (legacy)"""
    try:
        candidates = Candidate.objects.all().order_by('-id')
        results = []
        for c in candidates:
            match_score = MatchScore.objects.filter(candidate=c).first()
            candidate_data = {
                "id": c.id,
                "name": c.name,
                "score": round((match_score.score * 100) if match_score else 0, 1),  # Single score
                "skills": c.extracted_skills or [],
                "resume_url": f"http://127.0.0.1:8000{c.resume_file}" if c.resume_file else None,
            }
            if match_score and match_score.missing_skills:
                candidate_data["match_report"] = {
                    "matched_keywords": [s for s in (c.extracted_skills or []) if s not in (match_score.missing_skills or [])],
                    "missing_keywords": match_score.missing_skills or [],
                    "section_scores": {"skills": 70, "experience": 65, "education": 75, "keywords": 60},
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


# =============== DASHBOARD ENDPOINT (SINGLE SCORE) ===============
@api_view(['GET'])
@permission_classes([AllowAny])
def dashboard_data(request):
    """Returns ALL candidates with SINGLE final score."""
    min_score = float(request.query_params.get('min_score', 0))
    
    all_candidates = Candidate.objects.all().order_by('-created_at')
    
    candidates_list = []
    for cand in all_candidates:
        # Get score from MatchScore (already blended final score)
        match_score = MatchScore.objects.filter(candidate=cand).first()
        score = round((match_score.score * 100) if match_score else 0, 1)
        
        # Apply filter
        if score >= min_score:
            candidates_list.append({
                "id": cand.id,
                "name": cand.name,
                "score": score,  # ONLY ONE SCORE
                "verdict": "Shortlist" if score >= 60 else "Review",
                "file_url": f"http://127.0.0.1:8000{cand.resume_file}" if cand.resume_file else None,
                "skills_count": len(cand.extracted_skills or []),
                "analyzed_at": cand.created_at.isoformat() if cand.created_at else None,
                "matched_keywords": (match_score.matched_skills if match_score else [])[:10]
            })
    
    # Summary stats
    total = Candidate.objects.count()
    avg_score = MatchScore.objects.aggregate(Avg('score'))['score__avg'] or 0
    passed = MatchScore.objects.filter(score__gte=0.6).count()
    
    summary = {
        "total_resumes": total,
        "avg_score": round((avg_score or 0) * 100, 1),  # Single avg
        "pass_rate_percent": round((passed / max(total, 1)) * 100, 1),
        "last_updated": timezone.now().isoformat()
    }
    
    # Chart data (single score bars)
    recent = candidates_list[:10]
    comparison = [{
        "resume": c["name"][:25] + ("..." if len(c["name"]) > 25 else ""),
        "score": c["score"],  # Single score
        "verdict": c["verdict"]
    } for c in recent]
    
    return Response({
        "summary": summary,
        "charts": {"comparison": comparison},
        "candidates": candidates_list,
        "filter_applied": {"min_score": min_score}
    }, status=status.HTTP_200_OK)


# =============== LATEST BATCH DASHBOARD (Time-Based Grouping) ===============
@api_view(['GET'])
@permission_classes([AllowAny])
def dashboard_latest(request):
    """
    Returns candidates uploaded in the last 10 minutes (latest session).
    Includes charts, comparisons, and detailed match reports.
    Simple, reliable, no batch_id dependency.
    """
    from django.utils import timezone
    from datetime import timedelta
    
    # Get candidates uploaded in last 10 minutes
    cutoff = timezone.now() - timedelta(minutes=10)
    recent_candidates = Candidate.objects.filter(
        created_at__gte=cutoff
    ).order_by('-created_at')
    
    if not recent_candidates:
        return Response({
            "candidates": [], 
            "summary": {"total_candidates": 0, "avg_score": 0, "pass_rate": 0}, 
            "charts": {"comparison": []}
        }, status=200)
    
    candidates_list = []
    for cand in recent_candidates:
        match_score = MatchScore.objects.filter(candidate=cand).first()
        
        candidates_list.append({
            "id": cand.id,
            "name": cand.name,
            "score": round((match_score.score or 0) * 100, 1) if match_score else 0,  # SINGLE SCORE
            "verdict": "Shortlist" if (match_score.score or 0) >= 0.6 else "Review",
            "file_url": f"http://127.0.0.1:8000{cand.resume_file}" if cand.resume_file else None,
            "skills": cand.extracted_skills or [],
            "matched_keywords": (match_score.matched_skills if match_score else [])[:10],
            "missing_keywords": (match_score.missing_skills if match_score else [])[:10],
            "analyzed_at": cand.created_at.isoformat() if cand.created_at else None
        })
    
    # Summary stats
    scores = [c["score"] for c in candidates_list if c["score"] > 0]
    avg_score = sum(scores) / len(scores) if scores else 0
    passed = sum(1 for c in candidates_list if c["score"] >= 60)
    
    summary = {
        "total_candidates": len(candidates_list),
        "avg_score": round(avg_score, 1),  # SINGLE AVERAGE
        "pass_rate": round((passed / max(len(candidates_list), 1)) * 100, 1),
        "top_candidate": max(candidates_list, key=lambda x: x["score"])["name"] if candidates_list else None,
        "analyzed_at": recent_candidates[0].created_at.isoformat()
    }
    
    # Chart  Comparison bars for ALL recent candidates (single score)
    chart_data = [{
        "name": c["name"][:20] + ("..." if len(c["name"]) > 20 else ""),
        "score": c["score"],  # SINGLE SCORE
        "verdict": c["verdict"]
    } for c in candidates_list]
    
    return Response({
        "summary": summary,
        "candidates": candidates_list,
        "charts": {"comparison": chart_data}
    }, status=200)

# =============== ALL HISTORY (PAGINATED) ===============
@api_view(['GET'])
@permission_classes([AllowAny])
def dashboard_history(request):
    """Returns ALL candidates ever uploaded, paginated."""
    try:
        page = int(request.query_params.get('page', 1))
        page_size = 20
        search = request.query_params.get('search', '').lower()
        min_score = float(request.query_params.get('min_score', 0))
        
        # Base queryset
        candidates = Candidate.objects.all().order_by('-created_at')
        
        # Filter by search (simple name match)
        if search:
            candidates = candidates.filter(name__icontains=search)
        
        # Filter by min score — Use correct related_name: 'matches'
        if min_score > 0:
            candidates = candidates.filter(
                matches__score__gte=min_score/100  # 'matches' = related_name in MatchScore model
            ).distinct()
        
        # Pagination
        total = candidates.count()
        start = (page - 1) * page_size
        end = start + page_size
        paginated = candidates[start:end]
        
        results = []
        for cand in paginated:
            # Safe access to MatchScore via related_name 'matches'
            match_score = cand.matches.first()  # or: MatchScore.objects.filter(candidate=cand).first()
            
            results.append({
                "id": cand.id,
                "name": cand.name,
                "score": round((match_score.score or 0) * 100, 1) if match_score else 0,
                "verdict": "Shortlist" if (match_score and match_score.score and match_score.score >= 0.6) else "Review",
                "batch_id": str(getattr(cand, 'batch_id', 'default')),
                "analyzed_at": cand.created_at.isoformat() if cand.created_at else None,
                "skills_count": len(cand.extracted_skills or [])
            })
        
        return Response({
            "results": results,
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total": total,
                "total_pages": (total + page_size - 1) // page_size
            },
            "filters_applied": {
                "search": search,
                "min_score": min_score
            }
        }, status=200)
        
    except Exception as e:
        import traceback
        print(f"[❌ dashboard_history ERROR] {e}")
        print(traceback.format_exc())
        return Response({"error": "Internal server error", "details": str(e)}, status=500)

# =============== ML ANALYSIS ENDPOINT (Optional) ===============
@api_view(['POST'])
@permission_classes([AllowAny])
def ml_analyze(request):
    """Standalone ML analysis endpoint (if needed)"""
    resume_file = request.FILES.get('resume')
    jd = request.data.get('job_description', '').strip()

    if not resume_file or not jd:
        return Response({"error": "Missing 'resume' file or 'job_description'"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        file_ext = os.path.splitext(resume_file.name)[1].lower().replace('.', '')
        file_path = default_storage.save(f"temp_ml/{resume_file.name}", resume_file)
        full_path = os.path.join(settings.MEDIA_ROOT, file_path)

        resume_text = extract_text_from_file(full_path, file_ext)
        if not resume_text or not resume_text.strip():
            return Response({"error": "Could not extract text"}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)

        # Use ML predictor if available
        if ml_predictor:
            result = ml_predictor.predict(resume_text, jd)
            score = result['score']
            matched = result['matched_keywords']
        else:
            # Fallback to simple scoring
            score = 50.0
            matched = []
            
        verdict = "Shortlist" if score >= 60 else "Review"

        ml_record = MLAnalysis.objects.create(
            resume_filename=resume_file.name,
            job_description=jd,
            ml_score=score,
            matched_keywords=matched,
            verdict=verdict,
            method="ml_hybrid" if ml_predictor else "fallback"
        )

        return Response({
            "match_score_percent": score,
            "matched_keywords": matched,
            "verdict": verdict,
            "analysis_id": ml_record.id
        }, status=status.HTTP_200_OK)

    except Exception as e:
        print(f"[ML_ANALYZE ERROR] {e}")
        return Response({"error": "Analysis failed", "details": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    finally:
        if 'full_path' in locals() and os.path.exists(full_path):
            try:
                os.remove(full_path)
                default_storage.delete(file_path)
            except:
                pass


