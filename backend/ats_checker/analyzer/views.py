# analyzer/views.py
# ============================================================================
# ATS (Applicant Tracking System) Backend API Endpoints
# ============================================================================
# This file contains all Django REST Framework API endpoints for the 
# AI-powered resume screening system. Each endpoint handles a specific 
# user action: uploading resumes, fetching dashboards, viewing history, etc.
# ============================================================================

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

# ============================================================================
# ML PREDICTOR INITIALIZATION (Run once at server startup)
# ============================================================================

# Try to load the trained ML model for resume scoring.
# If the model file is missing or corrupted, gracefully fallback to traditional scoring.
try:
    from .ml_engine.ml_predictor import ATSMLPredictor
    ml_predictor = ATSMLPredictor()
    print("✅ ML Predictor loaded successfully")
except FileNotFoundError as e:
    ml_predictor = None
    print(f"⚠️ ML model file not found: {e}. Using traditional scoring fallback.")
except Exception as e:
    ml_predictor = None
    print(f"⚠️ ML Predictor initialization failed: {e}. Using traditional scoring fallback.")


# ============================================================================
# HELPER FUNCTION: Keyword Extractor
# ============================================================================

def extract_keywords(text, max_keywords=30):
    """
    Extract meaningful keywords from text for resume-JD matching.
    
    How it works:
    1. Finds all words 3-20 characters long (filters out very short/long noise)
    2. Removes common English stopwords (the, and, for, etc.)
    3. Counts word frequency and returns top N most common words
    
    Args:
        text (str): The resume or job description text to analyze
        max_keywords (int): Maximum number of keywords to return (default: 30)
    
    Returns:
        list: List of top keywords sorted by frequency
    """
    # Extract words: letters only, 3-20 characters, lowercase
    words = re.findall(r'\b[A-Za-z]{3,20}\b', text.lower())
    
    # Common English stopwords to exclude from keyword extraction
    stopwords = {
        'the', 'and', 'for', 'with', 'this', 'that', 'you', 'are', 'will', 'can',
        'have', 'has', 'had', 'was', 'were', 'been', 'being', 'is', 'am',
        'from', 'into', 'through', 'during', 'before', 'after', 'above', 'below',
        'between', 'under', 'again', 'further', 'then', 'once', 'here', 'there',
        'when', 'where', 'why', 'how', 'all', 'each', 'few', 'more', 'most',
        'other', 'some', 'such', 'no', 'nor', 'not', 'only', 'own', 'same', 'so',
        'than', 'too', 'very', 'just', 'also', 'now', 'our', 'your', 'they', 'them',
        'which', 'who', 'what', 'would', 'could', 'should', 'may', 'might', 'must'
    }
    
    # Filter out stopwords
    filtered = [w for w in words if w not in stopwords]
    
    # Count word frequency and return top N
    from collections import Counter
    return [word for word, _ in Counter(filtered).most_common(max_keywords)]


# ============================================================================
# ENDPOINT 1: Upload Resume & Generate Score
# ============================================================================
# POST /api/upload/
# Purpose: Accept a resume file + job description, analyze match, return score
# Returns: Candidate data with blended match score (ML + traditional)
# ============================================================================

@api_view(['POST'])
@permission_classes([AllowAny])
def upload_resume(request):
    """
    Handle resume upload: extract text, compute match score, save to database.
    
    Workflow:
    1. Validate file type (PDF/DOCX only) and required fields
    2. Save uploaded file to media storage
    3. Extract text from resume using PyPDF2/python-docx
    4. Extract skills and keywords from both resume and job description
    5. Calculate traditional keyword-based match score
    6. If ML model available: get ML prediction and blend with traditional (85/15)
    7. Generate section scores, recommendations, and match report
    8. Save candidate + match score to database
    9. Return JSON response with final score and analysis details
    
    Args:
        request: Django REST Framework request object containing:
            - resume: Uploaded file (PDF/DOCX)
            - job_description: Text of the job posting
    
    Returns:
        Response: JSON with candidate data, final score, and match report
        Status: 200 OK on success, 400/415/422/500 on errors
    """
    
    # --- Validation: Ensure request method and required fields ---
    if request.method != 'POST':
        return Response({"error": "Method not allowed"}, status=status.HTTP_405_METHOD_NOT_ALLOWED)
    
    resume = request.FILES.get('resume')
    job_description_text = request.data.get('job_description')
    
    if not resume or not job_description_text:
        return Response({"error": "Missing resume or job description"}, status=status.HTTP_400_BAD_REQUEST)
    
    # --- Validation: Check file extension is supported ---
    file_ext = os.path.splitext(resume.name)[1].lower()
    if file_ext not in ['.pdf', '.docx', '.doc']:
        return Response({"error": "Unsupported file type"}, status=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE)
    
    # --- Save uploaded file to Django media storage ---
    file_path = default_storage.save(f"resumes/{resume.name}", resume)
    full_path = os.path.join(settings.MEDIA_ROOT, file_path)
    
    try:
        # --- Step 1: Extract text from resume file ---
        resume_text = extract_text_from_file(full_path, file_ext[1:])
        if not resume_text.strip():
            return Response({"error": "Could not extract text from resume"}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)
        
        # --- Step 2: Extract skills and keywords from both texts ---
        resume_skills = extract_skills(resume_text)
        job_skills = extract_skills(job_description_text)
        resume_keywords = extract_keywords(resume_text)
        job_keywords = extract_keywords(job_description_text)
        
        # --- Step 3: Calculate keyword overlap (matched vs missing) ---
        matched_keywords = list(set(resume_keywords) & set(job_keywords))
        missing_keywords = list(set(job_keywords) - set(resume_keywords))
        
        # --- Step 4: Calculate traditional (rule-based) match score ---
        resume_doc = nlp(resume_text)
        job_doc = nlp(job_description_text)
        base_result = calculate_weighted_score(
            resume_text, job_description_text,
            resume_skills, job_skills,
            resume_doc, job_doc
        )
        
        keyword_match_rate = len(matched_keywords) / max(len(job_keywords), 1)
        skill_match_rate = len(set(resume_skills) & set(job_skills)) / max(len(job_skills), 1)
        
        # --- Step 5: ML Scoring (if model loaded) ---
        # Blend ML prediction (85%) with traditional score (15%) for stability
        if ml_predictor:
            try:
                ml_result = ml_predictor.predict(resume_text, job_description_text)
                ml_score = ml_result['score']
                final_score = round(ml_score * 0.85 + base_result['score'] * 0.15, 1)
            except Exception as ml_error:
                print(f"⚠️ ML prediction failed: {ml_error}. Using traditional score.")
                final_score = base_result['score']  # Fallback to traditional
        else:
            final_score = base_result['score']  # No ML model → use traditional only
        
        # --- Step 6: Generate section scores for UI display ---
        section_scores = {
            "skills": min(100, round(skill_match_rate * 100 + 5)),
            "experience": min(100, round(final_score * 0.9)),
            "education": min(100, round(final_score * 0.85 + 10)),
            "keywords": min(100, round(keyword_match_rate * 100))
        }
        
        # --- Step 7: Generate actionable recommendations for candidate ---
        recommendations = []
        if missing_keywords:
            recommendations.append(f"Add missing keywords: {', '.join(missing_keywords[:3])}")
        if final_score < 70:
            recommendations.append("Quantify achievements with metrics (e.g., 'Increased X by 40%')")
        if len(resume_skills) < len(job_skills) * 0.7:
            recommendations.append("Highlight more technical skills from the job description")
        recommendations.append("Use standard section headings: Experience, Skills, Education")
        
        # --- Step 8: Build API response with single blended score ---
        response_data = {
            "id": None,  # Will be set after DB save
            "name": resume.name.rsplit('.', 1)[0],  # Filename without extension
            "score": final_score,  # ✅ SINGLE FINAL SCORE (blended ML + traditional)
            "skills": list(set(resume_skills)),
            "matched_keywords": matched_keywords[:20],
            "resume_url": f"/media/{file_path}",  # Relative URL for frontend
            "match_report": {
                "matched_keywords": matched_keywords[:15],
                "missing_keywords": missing_keywords[:15],
                "section_scores": section_scores,
                "recommendations": recommendations[:4],
                "scoring_method": "ml_hybrid" if ml_predictor else "traditional"
            }
        }
        
        # --- Step 9: Save candidate to database ---
        candidate = Candidate.objects.create(
            name=response_data['name'],
            resume_file=file_path,
            extracted_text=resume_text[:5000],  # Truncate for storage efficiency
            extracted_skills=resume_skills
        )
        response_data['id'] = candidate.id
        response_data['resume_url'] = f"http://127.0.0.1:8000/media/{file_path}"  # Full URL for frontend
        
        # --- Step 10: Save match score to database for history/analytics ---
        MatchScore.objects.create(
            candidate=candidate,
            score=final_score/100,  # Store as 0.0-1.0 for database consistency
            missing_skills=missing_keywords,
            matched_skills=matched_keywords
        )
        
        return Response(response_data, status=status.HTTP_200_OK)
        
    except Exception as e:
        # --- Error handling: Log and return user-friendly message ---
        print(f"[CRITICAL ERROR in upload_resume] {str(e)}")
        traceback.print_exc()
        return Response({"error": "Processing failed", "details": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    finally:
        # --- IMPORTANT: Do NOT delete uploaded files ---
        # Files must persist so users can view/download them later via "View Resume"
        # Old code deleted files here, causing 404 errors on view attempts
        pass


# ============================================================================
# ENDPOINT 2: List All Candidates (Legacy Endpoint)
# ============================================================================
# GET /api/candidates/
# Purpose: Return all candidates for backward compatibility with old frontend
# Note: New frontend uses /api/dashboard/latest/ or /api/dashboard/history/ instead
# ============================================================================

@api_view(['GET'])
@permission_classes([AllowAny])
def list_candidates(request):
    """
    Return all candidates in database with their match scores (legacy endpoint).
    
    This endpoint exists for backward compatibility. New frontend code should use
    /api/dashboard/latest/ for recent uploads or /api/dashboard/history/ for 
    paginated full history.
    
    Returns:
        Response: List of candidate objects with score, skills, and match report
    """
    try:
        # Fetch all candidates ordered by newest first
        candidates = Candidate.objects.all().order_by('-id')
        results = []
        
        for c in candidates:
            # Get match score for this candidate (if exists)
            match_score = MatchScore.objects.filter(candidate=c).first()
            
            candidate_data = {
                "id": c.id,
                "name": c.name,
                "score": round((match_score.score * 100) if match_score else 0, 1),  # Convert 0.0-1.0 to percentage
                "skills": c.extracted_skills or [],
                "resume_url": f"http://127.0.0.1:8000{c.resume_file}" if c.resume_file else None,
            }
            
            # Add match report if missing skills exist (for recommendations)
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
        print(f"[ERROR in list_candidates] {str(e)}")
        return Response({"error": "Failed to load candidates"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ============================================================================
# ENDPOINT 3: Dashboard Data (All Candidates with Filters)
# ============================================================================
# GET /api/dashboard/?min_score=60
# Purpose: Return all candidates with optional score filtering for main dashboard
# Returns: Candidates list, summary stats, and comparison chart data
# ============================================================================

@api_view(['GET'])
@permission_classes([AllowAny])
def dashboard_data(request):
    """
    Return all candidates with optional minimum score filtering.
    
    Query Parameters:
        min_score (float, optional): Minimum score threshold (0-100). 
                                    Only candidates >= this score are returned.
    
    Returns:
        Response: {
            "summary": { total_resumes, avg_score, pass_rate_percent, last_updated },
            "charts": { "comparison": [ {resume, score, verdict} ] },
            "candidates": [ {id, name, score, verdict, file_url, ...} ],
            "filter_applied": { min_score }
        }
    """
    # Parse optional filter parameter
    min_score = float(request.query_params.get('min_score', 0))
    
    # Fetch all candidates ordered by newest first
    all_candidates = Candidate.objects.all().order_by('-created_at')
    
    candidates_list = []
    for cand in all_candidates:
        # Get match score for this candidate
        match_score = MatchScore.objects.filter(candidate=cand).first()
        score = round((match_score.score * 100) if match_score else 0, 1)
        
        # Apply score filter if specified
        if score >= min_score:
            candidates_list.append({
                "id": cand.id,
                "name": cand.name,
                "score": score,  # ✅ SINGLE SCORE (blended)
                "verdict": "Shortlist" if score >= 60 else "Review",
                "file_url": f"http://127.0.0.1:8000/media/{cand.resume_file}" if cand.resume_file else None,  # ✅ For "View Resume" button
                "skills_count": len(cand.extracted_skills or []),
                "analyzed_at": cand.created_at.isoformat() if cand.created_at else None,
                "matched_keywords": (match_score.matched_skills if match_score else [])[:10]
            })
    
    # Calculate summary statistics for dashboard header cards
    total = Candidate.objects.count()
    avg_score = MatchScore.objects.aggregate(Avg('score'))['score__avg'] or 0
    passed = MatchScore.objects.filter(score__gte=0.6).count()
    
    summary = {
        "total_resumes": total,
        "avg_score": round((avg_score or 0) * 100, 1),  # Convert to percentage
        "pass_rate_percent": round((passed / max(total, 1)) * 100, 1),  # Percentage passing threshold
        "last_updated": timezone.now().isoformat()
    }
    
    # Prepare chart data: top 10 candidates for comparison visualization
    recent = candidates_list[:10]
    comparison = [{
        "resume": c["name"][:25] + ("..." if len(c["name"]) > 25 else ""),  # Truncate long names
        "score": c["score"],
        "verdict": c["verdict"]
    } for c in recent]
    
    return Response({
        "summary": summary,
        "charts": {"comparison": comparison},
        "candidates": candidates_list,
        "filter_applied": {"min_score": min_score}
    }, status=status.HTTP_200_OK)


# ============================================================================
# ENDPOINT 4: Latest Batch Dashboard (Time-Based Grouping)
# ============================================================================
# GET /api/dashboard/latest/
# Purpose: Return only candidates uploaded in last 10 minutes (current session)
# Returns: Recent candidates with charts, summary, and detailed match reports
# ============================================================================

@api_view(['GET'])
@permission_classes([AllowAny])
def dashboard_latest(request):
    """
    Return candidates uploaded in the last 10 minutes (latest user session).
    
    Why time-based grouping?
    - Simpler than batch_id management
    - Automatically groups resumes uploaded in same "session"
    - No need for frontend to track batch IDs
    
    Returns:
        Response: {
            "summary": { total_candidates, avg_score, pass_rate, top_candidate, analyzed_at },
            "candidates": [ {id, name, score, verdict, file_url, skills, matched_keywords, ...} ],
            "charts": { "comparison": [ {name, score, verdict} ] }
        }
    """
    from datetime import timedelta
    
    # Calculate cutoff time: 10 minutes ago from now
    cutoff = timezone.now() - timedelta(minutes=10)
    
    # Fetch candidates uploaded within the time window
    recent_candidates = Candidate.objects.filter(
        created_at__gte=cutoff
    ).order_by('-created_at')
    
    # Handle empty result gracefully
    if not recent_candidates:
        return Response({
            "candidates": [], 
            "summary": {"total_candidates": 0, "avg_score": 0, "pass_rate": 0}, 
            "charts": {"comparison": []}
        }, status=200)
    
    # Build candidate list with all required fields for UI
    candidates_list = []
    for cand in recent_candidates:
        match_score = MatchScore.objects.filter(candidate=cand).first()
        
        candidates_list.append({
            "id": cand.id,
            "name": cand.name,
            "score": round((match_score.score or 0) * 100, 1) if match_score else 0,  # ✅ SINGLE SCORE
            "verdict": "Shortlist" if (match_score.score or 0) >= 0.6 else "Review",
            "file_url": f"http://127.0.0.1:8000/media/{cand.resume_file}" if cand.resume_file else None,  # ✅ CRITICAL: For "View Resume" button
            "skills": cand.extracted_skills or [],
            "matched_keywords": (match_score.matched_skills if match_score else [])[:10],
            "missing_keywords": (match_score.missing_skills if match_score else [])[:10],
            "analyzed_at": cand.created_at.isoformat() if cand.created_at else None
        })
    
    # Calculate summary statistics for this batch
    scores = [c["score"] for c in candidates_list if c["score"] > 0]
    avg_score = sum(scores) / len(scores) if scores else 0
    passed = sum(1 for c in candidates_list if c["score"] >= 60)
    
    summary = {
        "total_candidates": len(candidates_list),
        "avg_score": round(avg_score, 1),  # ✅ SINGLE AVERAGE
        "pass_rate": round((passed / max(len(candidates_list), 1)) * 100, 1),
        "top_candidate": max(candidates_list, key=lambda x: x["score"])["name"] if candidates_list else None,
        "analyzed_at": recent_candidates[0].created_at.isoformat()
    }
    
    # Prepare chart data: all recent candidates for comparison bar chart
    chart_data = [{
        "name": c["name"][:20] + ("..." if len(c["name"]) > 20 else ""),  # Truncate for chart display
        "score": c["score"],  # ✅ SINGLE SCORE for chart bars
        "verdict": c["verdict"]
    } for c in candidates_list]
    
    return Response({
        "summary": summary,
        "candidates": candidates_list,
        "charts": {"comparison": chart_data}
    }, status=200)


# ============================================================================
# ENDPOINT 5: History Dashboard (Paginated Full History)
# ============================================================================
# GET /api/dashboard/history/?page=1&search=python&min_score=70
# Purpose: Return ALL candidates ever uploaded, with pagination and filters
# Returns: Paginated list with search/filter support + metadata
# ============================================================================

@api_view(['GET'])
@permission_classes([AllowAny])
def dashboard_history(request):
    """
    Return all candidates ever uploaded, with pagination and filtering.
    
    Query Parameters:
        page (int, default=1): Page number for pagination
        search (str, optional): Filter candidates by name containing this text
        min_score (float, optional): Minimum score threshold (0-100)
    
    Returns:
        Response: {
            "results": [ {id, name, score, verdict, file_url, batch_id, analyzed_at, skills_count} ],
            "pagination": { page, page_size, total, total_pages },
            "filters_applied": { search, min_score }
        }
    
    Note: Uses related_name 'matches' from MatchScore.candidate ForeignKey
    """
    try:
        # Parse pagination and filter parameters
        page = int(request.query_params.get('page', 1))
        page_size = 20  # Items per page
        search = request.query_params.get('search', '').lower()
        min_score = float(request.query_params.get('min_score', 0))
        
        # Base queryset: all candidates, newest first
        candidates = Candidate.objects.all().order_by('-created_at')
        
        # Apply search filter: match candidate name (case-insensitive)
        if search:
            candidates = candidates.filter(name__icontains=search)
        
        # Apply score filter: use correct related_name 'matches' from MatchScore model
        # Note: MatchScore.candidate has related_name='matches', so we use matches__score
        if min_score > 0:
            candidates = candidates.filter(
                matches__score__gte=min_score/100  # Convert percentage to 0.0-1.0 scale
            ).distinct()  # .distinct() avoids duplicates from JOIN
        
        # Calculate pagination metadata
        total = candidates.count()
        start = (page - 1) * page_size
        end = start + page_size
        paginated = candidates[start:end]
        
        # Build result list with all fields needed for History.tsx table
        results = []
        for cand in paginated:
            # Safely get match score via related_name 'matches'
            match_score = cand.matches.first()  # Equivalent to MatchScore.objects.filter(candidate=cand).first()
            
            results.append({
                "id": cand.id,
                "name": cand.name,
                "score": round((match_score.score or 0) * 100, 1) if match_score else 0,  # ✅ SINGLE SCORE
                "verdict": "Shortlist" if (match_score and match_score.score and match_score.score >= 0.6) else "Review",
                "batch_id": str(getattr(cand, 'batch_id', 'default')),  # Safe fallback if field missing
                "analyzed_at": cand.created_at.isoformat() if cand.created_at else None,
                "skills_count": len(cand.extracted_skills or []),
                # ✅ CRITICAL FIX: Include file_url so "View Resume" button works
                "file_url": f"http://127.0.0.1:8000/media/{cand.resume_file}" if cand.resume_file else None,
            })
        
        return Response({
            "results": results,
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total": total,
                "total_pages": (total + page_size - 1) // page_size  # Ceiling division
            },
            "filters_applied": {
                "search": search,
                "min_score": min_score
            }
        }, status=200)
        
    except Exception as e:
        # Log full traceback for debugging, return safe error to client
        import traceback
        print(f"[❌ ERROR in dashboard_history] {e}")
        print(traceback.format_exc())
        return Response({"error": "Internal server error", "details": str(e)}, status=500)


# ============================================================================
# ENDPOINT 6: Standalone ML Analysis (Optional/Advanced Use)
# ============================================================================
# POST /api/ml-analyze/
# Purpose: Run ML analysis on resume+JD without saving to main candidate table
# Use Case: Testing ML model, A/B scoring, advanced analytics
# ============================================================================

@api_view(['POST'])
@permission_classes([AllowAny])
def ml_analyze(request):
    """
    Standalone ML analysis endpoint for testing or advanced use cases.
    
    Unlike upload_resume, this endpoint:
    - Does NOT save to Candidate table (only to MLAnalysis table)
    - Returns raw ML score without blending with traditional scoring
    - Useful for A/B testing, model validation, or advanced analytics
    
    Args:
        request: Contains 'resume' file and 'job_description' text
    
    Returns:
        Response: {
            "match_score_percent": float,
            "matched_keywords": list,
            "verdict": "Shortlist" or "Review",
            "method": "ml_hybrid" or "fallback",
            "analysis_id": int (MLAnalysis record ID)
        }
    """
    resume_file = request.FILES.get('resume')
    jd = request.data.get('job_description', '').strip()

    # Validate required inputs
    if not resume_file or not jd:
        return Response({"error": "Missing 'resume' file or 'job_description'"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        # Save file temporarily for processing
        file_ext = os.path.splitext(resume_file.name)[1].lower().replace('.', '')
        file_path = default_storage.save(f"temp_ml/{resume_file.name}", resume_file)
        full_path = os.path.join(settings.MEDIA_ROOT, file_path)
        print(f"[DEBUG] Saved temp file: {full_path}")

        # Extract text from resume
        resume_text = extract_text_from_file(full_path, file_ext)
        print(f"[DEBUG] Extracted text length: {len(resume_text) if resume_text else 0}")
        
        if not resume_text or not resume_text.strip():
            return Response({"error": "Could not extract text"}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)

        # Run ML prediction if model is available
        if ml_predictor:
            result = ml_predictor.predict(resume_text, jd)
            score = result['score']
            matched = result['matched_keywords']
        else:
            # Fallback: return neutral score if ML unavailable
            score = 50.0
            matched = []
            
        # Determine hiring verdict based on score threshold
        verdict = "Shortlist" if score >= 60 else "Review"
        print(f"[DEBUG] ML Score: {score}, Matched: {len(matched)} keywords")

        # Save analysis result to MLAnalysis table for audit/history
        ml_record = MLAnalysis.objects.create(
            resume_filename=resume_file.name,
            job_description=jd,
            ml_score=score,
            matched_keywords=matched,
            verdict=verdict,
            method="ml_hybrid" if ml_predictor else "fallback"
        )
        print(f"[DEBUG] Saved to DB with ID: {ml_record.id}")

        return Response({
            "match_score_percent": score,
            "matched_keywords": matched,
            "verdict": verdict,
            "method": "ml_hybrid" if ml_predictor else "fallback",
            "analysis_id": ml_record.id,
            "message": "Analysis saved to database"
        }, status=status.HTTP_200_OK)

    except Exception as e:
        # Log full error details for debugging
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
        # Cleanup: Delete temporary file after processing
        if 'full_path' in locals() and os.path.exists(full_path):
            try:
                os.remove(full_path)
                default_storage.delete(file_path)
                print("[DEBUG] Cleaned up temp file")
            except Exception as cleanup_err:
                print(f"[DEBUG] Cleanup warning: {cleanup_err}")