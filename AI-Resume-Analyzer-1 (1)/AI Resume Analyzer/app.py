from flask import Flask, render_template, request
from werkzeug.utils import secure_filename
import os
import fitz  # PyMuPDF
from sentence_transformers import SentenceTransformer, util
import re

# ================== SETUP ==================
app = Flask(__name__)

UPLOAD_FOLDER = 'static/uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Load model (lightweight & fast)
model = SentenceTransformer('all-MiniLM-L6-v2')

# ================== FUNCTIONS ==================

# Extract text from PDF
def extract_text_pymupdf(pdf_path):
    text = ""
    try:
        doc = fitz.open(pdf_path)
        for page in doc:
            text += page.get_text()
        doc.close()
    except Exception as e:
        print("Error reading PDF:", e)
    return text.strip()


# Extract simple skills (basic keyword approach)
def extract_skills(text):
    skills_list = [
        "python", "java", "c++", "html", "css", "javascript",
        "react", "node", "flask", "django", "sql", "mongodb",
        "machine learning", "data analysis", "git"
    ]
    text = text.lower()
    found_skills = [skill for skill in skills_list if skill in text]
    return set(found_skills)


# ================== ROUTES ==================

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/analyze', methods=['POST'])
def analyze():
    if 'resume' not in request.files:
        return "No file uploaded", 400

    resume_file = request.files['resume']
    job_desc = request.form.get('job_description', '')

    if resume_file.filename == '' or not job_desc:
        return "Missing resume or job description", 400

    # Save file
    filename = secure_filename(resume_file.filename)
    save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    resume_file.save(save_path)

    # Extract text
    resume_text = extract_text_pymupdf(save_path)

    # ================== SIMILARITY ==================
    embeddings = model.encode([resume_text, job_desc], convert_to_tensor=True)
    similarity_score = util.pytorch_cos_sim(embeddings[0], embeddings[1]).item()
    match_score = round(similarity_score * 100, 2)

    # ================== SKILL MATCH ==================
    resume_skills = extract_skills(resume_text)
    jd_words = set(re.findall(r'\b\w+\b', job_desc.lower()))

    matched_skills = sorted(resume_skills & jd_words)
    missing_skills = sorted(jd_words - resume_skills)[:10]

    # ================== ATS SCORE ==================
    ats_score = 0

    # 1. Keyword Match (50)
    keyword_score = min(len(matched_skills) * 5, 50)

    # 2. Resume Length (20)
    length_score = 20 if len(resume_text.split()) > 150 else 10

    # 3. Sections (20)
    sections = ["education", "experience", "skills", "projects"]
    section_score = sum([5 for sec in sections if sec in resume_text.lower()])

    # 4. Formatting (10)
    format_score = 10 if "\n" in resume_text else 5

    ats_score = keyword_score + length_score + section_score + format_score
    ats_score = min(ats_score, 100)

    # ================== SUGGESTIONS ==================
    suggestions = []

    if len(matched_skills) < 5:
        suggestions.append("Add more relevant skills from job description.")

    if len(resume_text.split()) < 150:
        suggestions.append("Resume is too short. Add more details.")

    if section_score < 20:
        suggestions.append("Include all sections: Education, Experience, Skills, Projects.")

    if "flask" in jd_words and "flask" not in resume_text.lower():
        suggestions.append("Add Flask experience.")

    if "sql" in jd_words and "sql" not in resume_text.lower():
        suggestions.append("Add SQL experience.")

    # ================== RETURN ==================
    return render_template(
        'result.html',
        match_score=match_score,
        ats_score=ats_score,
        matched_skills=matched_skills,
        missing_skills=missing_skills,
        suggestions=suggestions
    )
    
    print("Keyword:", keyword_score)
    print("Length:", length_score)
    print("Section:", section_score)
    print("Format:", format_score)
    print("ATS:", ats_score)


# ================== RUN ==================
if __name__ == '__main__':
    app.run(debug=True, use_reloader=False)