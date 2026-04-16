import joblib
import os
import re
from sklearn.metrics.pairwise import cosine_similarity

class ATSInference:
    def __init__(self):
        model_path = os.path.join(os.path.dirname(__file__), "ats_model.pkl")
        if not os.path.exists(model_path):
            raise FileNotFoundError("Run trainer.py first to generate ats_model.pkl inside ml_engine/")
        
        self.model_data = joblib.load(model_path)
        self.vectorizer = self.model_data["vectorizer"]

    def clean(self, text: str) -> str:
        return re.sub(r"[^\w\s]", "", text.lower()).strip()

    def score(self, resume: str, jd: str) -> float:
        r, j = self.clean(resume), self.clean(jd)
        tfidf = self.vectorizer.transform([r, j])
        return round(cosine_similarity(tfidf[0:1], tfidf[1:2])[0][0] * 100, 2)

    def keywords(self, resume: str, jd: str, top_n=10) -> list:
        r_words = set(self.clean(resume).split())
        j_words = set(self.clean(jd).split())
        return sorted(list(r_words & j_words))[:top_n]