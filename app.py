from flask import Flask, request, jsonify
from flask_cors import CORS
import pdfplumber, docx, os, json, re
from datetime import datetime
import spacy

# ================= SETUP =================
nlp = spacy.load("en_core_web_sm")

app = Flask(__name__, static_folder="static")
CORS(app)

UPLOAD_FOLDER = "uploads"
HISTORY_FILE = "history.json"
ALLOWED_EXTENSIONS = [".pdf", ".docx"]

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ================= HELPERS =================
def allowed_file(filename):
    return os.path.splitext(filename)[1].lower() in ALLOWED_EXTENSIONS

def load_history():
    if not os.path.exists(HISTORY_FILE):
        return []
    try:
        with open(HISTORY_FILE, "r") as f:
            return json.load(f)
    except:
        return []

def save_history(data):
    with open(HISTORY_FILE, "w") as f:
        json.dump(data, f, indent=2)

# ================= DOMAIN KEYWORDS =================
DOMAIN_KEYWORDS = {
    "cyber_forensics": [
        "cyber forensics","digital forensics","malware","incident response",
        "network forensics","log analysis","siem","security investigation"
    ],
    "technology": [
        "software","developer","programming","python","java","api","cloud",
        "database","web","backend","frontend"
    ],
    "business": [
        "management","marketing","operations","strategy","sales",
        "leadership","communication","planning"
    ],
    "finance": [
        "accounting","finance","audit","tax","investment","tally",
        "compliance","budget","costing"
    ],
    "science": [
        "research","laboratory","experiment","analysis","methodology",
        "biology","chemistry","physics","statistics"
    ]
}

DOMAIN_SKILL_HINTS = {
    "cyber_forensics": [
        "forensics","malware","security","incident","network",
        "wireshark","autopsy","ftk","encase","siem","logs","linux"
    ],
    "technology": [
        "python","java","sql","javascript","react","angular","node",
        "django","flask","aws","azure","docker","linux","api","cloud","devops"
    ],
    "business": [
        "marketing","operations","strategy","sales","management",
        "crm","communication","leadership","analysis"
    ],
    "finance": [
        "accounting","tax","audit","investment","finance",
        "tally","budgeting","compliance","costing"
    ],
    "science": [
        "research","analysis","laboratory","experiment",
        "statistics","methodology","data"
    ]
}

SKILL_EQUIVALENTS = {
    "python": ["python", "django", "flask"],
    "java": ["java", "spring", "backend"],
    "javascript": ["javascript", "react", "angular", "node"],
    "sql": ["sql", "database", "mysql", "postgres"],
    "aws": ["aws", "cloud", "ec2", "s3"],
    "azure": ["azure", "cloud"],
    "devops": ["devops", "docker", "ci", "cd"],
    "cyber security": ["security", "forensics", "malware", "incident"],
    "ruby": ["ruby", "rails"]
}

# ================= CORE LOGIC =================
def detect_domain(text):
    scores = {d: 0 for d in DOMAIN_KEYWORDS}
    for domain, words in DOMAIN_KEYWORDS.items():
        for w in words:
            if w in text:
                scores[domain] += 1
    return max(scores, key=scores.get)

def extract_text(path, ext):
    text = ""
    if ext == ".pdf":
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages:
                text += page.extract_text() or ""
    elif ext == ".docx":
        d = docx.Document(path)
        for p in d.paragraphs:
            text += p.text + " "
    return text.lower()

def extract_skills_nlp(text, domain):
    doc = nlp(text)
    skills = set()
    hints = DOMAIN_SKILL_HINTS.get(domain, [])
    blacklist = [
        "experience","project","months","years","users","team","company",
        "solution","role","responsibility","salary","award","effort","work"
    ]

    for chunk in doc.noun_chunks:
        try:
            phrase = re.sub(r"[^a-zA-Z ]", "", chunk.text.lower()).strip()
            if not phrase or len(phrase.split()) > 3:
                continue
            if any(b in phrase for b in blacklist):
                continue
            if hints and not any(h in phrase for h in hints):
                continue
            skills.add(phrase)
        except:
            continue

    return sorted(skills)

def score_resume(text, required_skills, experience):
    domain = detect_domain(text)
    resume_skills = extract_skills_nlp(text, domain)

    matched = []
    for req in required_skills:
        equivalents = SKILL_EQUIVALENTS.get(req, [req])
        for eq in equivalents:
            if any(eq in r for r in resume_skills):
                matched.append(req)
                break

    skill_match = int(len(matched) / len(required_skills) * 100) if required_skills else 0
    score = min(100, int(skill_match * 0.6 + experience * 10))

    decision = (
        "SUITABLE" if skill_match >= 70 and experience >= 2 else
        "CONDITIONAL" if skill_match >= 40 else
        "NOT SUITABLE"
    )

    return domain, score, decision, matched, resume_skills

# ================= ROUTES =================
@app.route("/")
def home():
    return app.send_static_file("index.html")

@app.route("/admin")
def admin():
    return app.send_static_file("admin.html")

@app.route("/history")
def history():
    return jsonify(load_history())

@app.route("/analyze", methods=["POST"])
def analyze():
    files = request.files.getlist("resumes")
    if not files:
        return jsonify({"error": "No resume uploaded"}), 400

    resume = files[0]
    if not allowed_file(resume.filename):
        return jsonify({"error": "Only PDF or DOCX allowed"}), 400

    required_skills = [
        s.strip().lower()
        for s in request.form.get("skills", "").split(",")
        if s.strip()
    ]

    try:
        experience = int(request.form.get("experience", 0))
    except:
        experience = 0

    ext = os.path.splitext(resume.filename)[1].lower()
    path = os.path.join(UPLOAD_FOLDER, resume.filename)
    resume.save(path)

    text = extract_text(path, ext)
    domain, score, decision, matched, detected = score_resume(
        text, required_skills, experience
    )

    os.remove(path)

    history = load_history()
    history.append({
        "resume": resume.filename,
        "domain": domain,
        "score": score,
        "decision": decision,
        "date": datetime.now().strftime("%d-%m-%Y %H:%M")
    })
    save_history(history)

    return jsonify({
        "domain": domain,
        "score": score,
        "decision": decision,
        "matchedSkills": matched,
        "detectedSkills": detected
    })

@app.route("/rank", methods=["POST"])
def rank():
    resumes = request.files.getlist("resumes")
    required_skills = [
        s.strip().lower()
        for s in request.form.get("skills", "").split(",")
        if s.strip()
    ]

    try:
        experience = int(request.form.get("experience", 0))
    except:
        experience = 0

    results = []

    for resume in resumes:
        if not allowed_file(resume.filename):
            continue

        ext = os.path.splitext(resume.filename)[1].lower()
        path = os.path.join(UPLOAD_FOLDER, resume.filename)
        resume.save(path)

        text = extract_text(path, ext)
        domain, score, decision, _, _ = score_resume(
            text, required_skills, experience
        )

        os.remove(path)

        results.append({
            "resume": resume.filename,
            "domain": domain,
            "score": score,
            "decision": decision
        })

    ranked = sorted(results, key=lambda x: x["score"], reverse=True)
    for i, r in enumerate(ranked, start=1):
        r["rank"] = i

    return jsonify(ranked)

# ================= RUN =================
if __name__ == "__main__":
    print("✅ Resume Scanner FINAL VERSION running...")
    import os

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)


