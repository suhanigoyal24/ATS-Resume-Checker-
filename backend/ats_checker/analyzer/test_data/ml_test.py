# In views.py
@api_view(['GET'])
def test_ml_engine(request):
    """Health check for ML model"""
    try:
        engine = apps.get_app_config('analyzer').ats_engine
        test_resume = "Python developer with Django experience"
        test_jd = "Looking for Python Django developer"
        score = engine.score(test_resume, test_jd)
        return Response({
            "status": "healthy",
            "test_score": score,
            "model_loaded": True
        })
    except Exception as e:
        return Response({"status": "error", "message": str(e)}, status=500)