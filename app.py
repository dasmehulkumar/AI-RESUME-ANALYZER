from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
from werkzeug.utils import secure_filename
import os
import fitz  # PyMuPDF
from sentence_transformers import SentenceTransformer, util
import re

# ================== SETUP ==================
app = Flask(__name__)
CORS(app)

UPLOAD_FOLDER = 'static/uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Load model (lightweight & fast)
model = SentenceTransformer('all-MiniLM-L6-v2')

# ================== COMPREHENSIVE SKILL LIST ==================
TECH_SKILLS = set([
    "python", "java", "c++", "c#", "html", "css", "javascript", "typescript",
    "react", "node", "node.js", "flask", "django", "sql", "mongodb", "postgresql", "mysql",
    "machine learning", "data analysis", "git", "docker", "kubernetes", "aws", "azure", "gcp",
    "express", "angular", "vue", "spring boot", "ruby on rails", "php", "laravel",
    "data science", "artificial intelligence", "nlp", "computer vision", "tensorflow", "pytorch",
    "pandas", "numpy", "scikit-learn", "keras", "tableau", "power bi", "excel",
    "agile", "scrum", "jira", "ci/cd", "jenkins", "github actions", "gitlab",
    "linux", "bash", "shell scripting", "rest api", "graphql", "redis", "elasticsearch",
    "c", "rust", "go", "golang", "swift", "kotlin", "dart", "flutter", "react native",
    "cybersecurity", "blockchain", "solidity", "web3", "hadoop", "spark", "kafka",
    "microservices", "system design", "devops", "cloud computing", "machine learning operations"
])

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

def clean_text(text):
    # Remove non-alphanumeric characters, convert to lowercase
    text = re.sub(r'[^a-zA-Z0-9\s]', ' ', text)
    return ' '.join(text.lower().split())

def extract_skills(text):
    text = text.lower()
    found_skills = set()
    # Check for multi-word skills first
    for skill in TECH_SKILLS:
        # Use regex to match whole words/phrases to prevent partial matches like 'in' matching 'linux'
        if re.search(r'\b' + re.escape(skill) + r'\b', text):
            found_skills.add(skill)
    return found_skills

# ================== ROUTES ==================

@app.route('/')
def index():
    return jsonify({"message": "AI Resume Analyzer API is running."})

@app.route('/analyze', methods=['POST'])
def analyze():
    if 'resume' not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    resume_file = request.files['resume']
    job_desc = request.form.get('job_description', '')

    if resume_file.filename == '' or not job_desc:
        return jsonify({"error": "Missing resume or job description"}), 400

    # Save file
    filename = secure_filename(resume_file.filename)
    save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    resume_file.save(save_path)

    # Extract text
    resume_text = extract_text_pymupdf(save_path)
    if not resume_text:
        return jsonify({"error": "Could not extract text from the resume"}), 400

    # Clean texts for better comparison
    cleaned_resume = clean_text(resume_text)
    cleaned_jd = clean_text(job_desc)

    # ================== SIMILARITY ==================
    embeddings = model.encode([cleaned_resume, cleaned_jd], convert_to_tensor=True)
    similarity_score = util.pytorch_cos_sim(embeddings[0], embeddings[1]).item()
    # Boost similarity score slightly as pure cosine similarity on long texts tends to be very low.
    # Map the cosine similarity to a more realistic 0-100 scale.
    normalized_similarity = max(0, min(100, (similarity_score - 0.1) * 1.5 * 100))
    match_score = round(normalized_similarity, 2)

    # ================== SKILL MATCH ==================
    resume_skills = extract_skills(cleaned_resume)
    jd_skills = extract_skills(cleaned_jd)
    
    # If the JD has no extractable skills, fall back to matching against all words in JD
    jd_words = set(cleaned_jd.split())
    if len(jd_skills) == 0:
        matched_skills = sorted(list(resume_skills & jd_words))
        missing_skills = [] # Hard to define missing if no standard skills found in JD
    else:
        matched_skills = sorted(list(resume_skills & jd_skills))
        missing_skills = sorted(list(jd_skills - resume_skills))

    # ================== ATS SCORE ==================
    # 1. Keyword Match (40)
    skill_match_ratio = len(matched_skills) / len(jd_skills) if len(jd_skills) > 0 else 0.5
    keyword_score = min(40, skill_match_ratio * 40)
    
    # Give a base score for having ANY relevant skills if jd_skills is empty
    if len(jd_skills) == 0 and len(resume_skills) > 0:
        keyword_score = min(40, len(resume_skills) * 4)

    # 2. Resume Length (20)
    word_count = len(resume_text.split())
    if word_count > 300:
        length_score = 20
    elif word_count > 150:
        length_score = 15
    else:
        length_score = 10

    # 3. Sections (20)
    sections = ["education", "experience", "skills", "projects"]
    section_score = sum([5 for sec in sections if sec in resume_text.lower()])

    # 4. Formatting (20)
    # Penalize if it's just one giant block of text
    lines = resume_text.split('\n')
    format_score = 20 if len(lines) > 20 else 10

    ats_score = round(keyword_score + length_score + section_score + format_score)
    ats_score = min(ats_score, 100)

    # ================== SUGGESTIONS ==================
    suggestions = []

    if skill_match_ratio < 0.5 and len(jd_skills) > 0:
        suggestions.append("Add more relevant skills from the job description.")

    if word_count < 200:
        suggestions.append("Resume is somewhat short. Consider adding more details about your accomplishments.")

    if section_score < 20:
        missing_secs = [s.capitalize() for s in sections if s not in resume_text.lower()]
        suggestions.append(f"Consider explicitly including these sections: {', '.join(missing_secs)}.")

    if len(missing_skills) > 0:
        top_missing = ", ".join(missing_skills[:3])
        suggestions.append(f"Highlight experience with missing key skills like: {top_missing}.")

    # ================== RETURN ==================
    return jsonify({
        "match_score": match_score,
        "ats_score": ats_score,
        "matched_skills": matched_skills,
        "missing_skills": missing_skills,
        "suggestions": suggestions,
        "extracted_resume_skills": list(resume_skills),
        "job_description_skills": list(jd_skills)
    })

# ================== RUN ==================
if __name__ == '__main__':
    app.run(debug=True, use_reloader=False, port=5000)