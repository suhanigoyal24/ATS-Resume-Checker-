import PyPDF2
from docx import Document
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


def extract_text_from_pdf(file):
    reader = PyPDF2.PdfReader(file)
    text = ""
    for page in reader.pages:
        if page.extract_text():
            text += page.extract_text()
    return text


def extract_text_from_docx(file):
    doc = Document(file)
    text = ""
    for para in doc.paragraphs:
        text += para.text
    return text


def get_text(file):
    if file.name.endswith('.pdf'):
        return extract_text_from_pdf(file)
    elif file.name.endswith('.docx'):
        return extract_text_from_docx(file)
    return ""


def calculate_similarity(resume_text, job_text):
    tfidf = TfidfVectorizer(stop_words='english')
    vectors = tfidf.fit_transform([resume_text, job_text])

    score = cosine_similarity(vectors[0:1], vectors[1:2])[0][0]
    return round(score * 100, 2)