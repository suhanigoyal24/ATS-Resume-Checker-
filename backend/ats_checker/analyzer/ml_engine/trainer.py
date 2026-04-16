import os
import pandas as pd
import joblib
from sklearn.feature_extraction.text import TfidfVectorizer

# Mock dataset for immediate testing (replace with real CSV later)
MOCK_DATA = [
    {"resume": "Experienced python developer skilled in django, rest api, and machine learning. Built scalable web apps.", "jd": "Senior Python Developer with Django and REST API experience"},
    {"resume": "Java developer with spring boot, microservices, and AWS deployment experience.", "jd": "Senior Python Developer with Django and REST API experience"},
    {"resume": "Data scientist proficient in python, scikit-learn, tensorflow, and data analysis.", "jd": "Senior Python Developer with Django and REST API experience"},
    {"resume": "Full stack engineer with react, node.js, python, and django experience.", "jd": "Senior Python Developer with Django and REST API experience"},
]

def train_and_save():
    print("📦 Preparing training data...")
    df = pd.DataFrame(MOCK_DATA)
    
    # Combine resume & JD texts for vocabulary building
    texts = df['resume'].tolist() + df['jd'].tolist()
    
    print("🔧 Training TF-IDF Vectorizer...")
    vectorizer = TfidfVectorizer(stop_words='english', ngram_range=(1, 2), max_features=3000)
    vectorizer.fit(texts)
    
    # Save model to this same folder
    model_path = os.path.join(os.path.dirname(__file__), "ats_model.pkl")
    print(f"💾 Saving model to {model_path}")
    joblib.dump({"vectorizer": vectorizer}, model_path)
    print("✅ Model saved! Ready for Django.")

if __name__ == "__main__":
    train_and_save()