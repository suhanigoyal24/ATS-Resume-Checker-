import pdfplumber
import re
from sklearn.metrics import precision_score, recall_score, f1_score

# ================= CONFIGURATION =================
# 1. Open 'sample_resume.pdf', read the skills listed there.
# 2. Paste them inside the list below (Ground Truth).
GROUND_TRUTH_SKILLS = ['python', 'django', 'sql', 'git', 'html', 'css'] 
# =================================================

def get_skills_from_pdf(file_path):
    text = ""
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            text += page.extract_text() or ""
    
    # --- YOUR ACTUAL SKILL EXTRACTION LOGIC HERE ---
    # (Example: Simple keyword matching)
    # Replace this with your actual function if you have one!
    keywords = ['python', 'django', 'sql', 'git', 'html', 'css', 'react', 'java', 'aws']
    found_skills = []
    for word in keywords:
        if word in text.lower():
            found_skills.append(word)
    # -----------------------------------------------
    return found_skills

# ================= RUN TEST =================
print("🔍 Analyzing sample_resume.pdf...")
try:
    extracted = get_skills_from_pdf("sample_resume.pdf")
    
    print(f"\n✅ Extracted Skills: {extracted}")
    print(f"📖 Real Skills (You defined): {GROUND_TRUTH_SKILLS}")

    # Calculate F1 Score
    all_skills = list(set(extracted + GROUND_TRUTH_SKILLS))
    y_true = [1 if s in GROUND_TRUTH_SKILLS else 0 for s in all_skills]
    y_pred = [1 if s in extracted else 0 for s in all_skills]

    p = precision_score(y_true, y_pred, zero_division=0)
    r = recall_score(y_true, y_pred, zero_division=0)
    f1 = f1_score(y_true, y_pred, zero_division=0)

    print(f"\n📊 RESULTS:")
    print(f"Precision: {p*100:.1f}%")
    print(f"Recall:    {r*100:.1f}%")
    print(f"F1 Score:  {f1*100:.1f}%")  # <-- PUT THIS NUMBER ON YOUR SLIDE

except Exception as e:
    print(f"❌ Error: {e}")
    print("Note: If text is empty, the PDF might be image-based (scan).")