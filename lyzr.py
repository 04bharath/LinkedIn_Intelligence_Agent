"""
lyzr.py  –  AI Extraction Layer (Lyzr API)

Extracts exactly 18 structured fields from raw LinkedIn job data.
Uses Lyzr API for AI extraction; falls back to smart regex if API fails.
"""

import json
import re
import datetime
import hashlib
import requests

import os

Lyzr_API_KEY = os.getenv("LYZR_API_KEY", "dummy")

_SYSTEM_PROMPT = """
You are an expert LinkedIn job-post parser.
Given raw text from a LinkedIn job posting, extract exactly the following 18 fields and
return ONLY a valid JSON object — no markdown fences, no extra keys, no commentary.

Fields to extract:
  post_id                      (string – first 12 non-space chars of the text, lowercased)
  role                         (string – job title / role being hired for)
  company_name                 (string)
  location                     (string)
  primary_skills               (JSON array of strings – top technical skills required)
  secondary_skills             (JSON array of strings – nice-to-have skills)
  must_to_have                 (JSON array of strings – absolute must-have requirements)
  years_of_experience          (string – e.g. "3-5 years" or "Not specified")
  looking_for_college_students (string – "Yes" or "No")
  intern                       (string – "Yes" or "No")
  salary_package               (string – e.g. "₹12-18 LPA" or "Not specified")
  email                        (string – contact email if present, else "Not specified")
  phone                        (string – contact phone if present, else "Not specified")
  hiring_intent                (string – "Active", "Passive", or "Unknown")
  author_name                  (string – name of the person who posted)
  author_linkedin_url          (string – LinkedIn URL of poster, or "Not specified")
  post_url                     (string – direct URL to the post, or "Not specified")
  date_posted                  (string – date the post was published, or "Not specified")

Rules:
- Every field MUST be present in the response.
- Use "Not specified" when data is absent — never null, never omit the key.
- Arrays must have at least one element; use ["Not specified"] if truly empty.
- Do NOT wrap the JSON in markdown code-blocks.
""".strip()


# ── Main entry point ──────────────────────────────────────────────────────────

def extract_data(raw, keyword: str, idx: int) -> dict:
    today = str(datetime.date.today())

    # Normalise to text + meta dict
    if isinstance(raw, dict):
        text = _dict_to_text(raw)
        meta = raw
    else:
        try:
            meta = json.loads(raw)
            text = _dict_to_text(meta) if isinstance(meta, dict) else str(raw)
        except Exception:
            text = str(raw)
            meta = {}

    text = text[:3000]

    # Try Lyzr API first
    job = None
    if Lyzr_API_KEY and Lyzr_API_KEY != "YOUR_LYZR_API_KEY_HERE":
        job = _call_lyzr(text, keyword)

    # Smart regex fallback
    if not job:
        job = _smart_extract(text, meta, keyword, idx)

    job["keyword_matched"] = keyword
    job["date_processed"]  = today

    if not job.get("post_id") or job["post_id"] in ("Not specified", ""):
        job["post_id"] = _make_id(text, keyword, idx)

    return job


# ── Lyzr API call ─────────────────────────────────────────────────────────────

def _call_lyzr(text: str, keyword: str):
    """
    Call Lyzr AI API to extract structured job fields.
    Lyzr uses OpenAI-compatible /v2/chat/completions endpoint.
    """
    try:
        url = "https://agent.api.lyzr.ai/v2/chat/"

        headers = {
            "x-api-key": Lyzr_API_KEY,
            "Content-Type": "application/json"
        }

        full_prompt = (
            f"Keyword searched: {keyword}\n\n"
            f"Raw post text:\n{text}\n\n"
            f"Return ONLY a JSON object with all 18 fields as specified."
        )

        payload = {
            "user_id":  "linkedin_scraper",
            "agent_id": "linkedin_job_parser",
            "message":  full_prompt,
            "session_id": f"session_{keyword}_{hash(text) % 99999}"
        }

        resp = requests.post(url, headers=headers, json=payload, timeout=20)

        if resp.status_code == 200:
            result = resp.json()
            # Lyzr returns response in different keys depending on version
            raw_text = (
                result.get("response") or
                result.get("message") or
                result.get("output") or
                result.get("text") or ""
            )
            raw_text = raw_text.strip()
            # Strip markdown fences if present
            raw_text = re.sub(r"^```[a-z]*\n?", "", raw_text)
            raw_text = re.sub(r"\n?```$",        "", raw_text)

            job = json.loads(raw_text)
            print(f"[lyzr] ✅ Lyzr extracted: {job.get('role')} @ {job.get('company_name')}")
            return job
        else:
            print(f"[lyzr] ❌ Lyzr API error {resp.status_code}: {resp.text[:200]}")
            return None

    except json.JSONDecodeError as e:
        print(f"[lyzr] ❌ JSON parse error: {e}")
        return None
    except Exception as e:
        print(f"[lyzr] ❌ Lyzr failed: {e}")
        return None


# ── Smart regex fallback ──────────────────────────────────────────────────────

def _smart_extract(text: str, meta: dict, keyword: str, idx: int) -> dict:

    def get(*keys, default="Not specified"):
        for k in keys:
            v = meta.get(k)
            if v and str(v).strip() and str(v).strip().lower() != "none":
                return str(v).strip()
        return default

    role    = get("title", "job_title", "position", "role", default=keyword)
    company = get("company", "company_name", "companyName", "organization")
    if company == "Not specified":
        m = re.search(r"at\s+([A-Z][A-Za-z0-9\s&]{2,30}?)(?:\s+in|\s+–|\.|,)", text)
        if m: company = m.group(1).strip()

    location = get("location", "city", "place", "region")
    if location == "Not specified":
        m = re.search(r"in\s+([A-Z][A-Za-z\s,]{3,30}?)(?:\.|,|\n|Required)", text)
        if m: location = m.group(1).strip()

    COMMON_SKILLS = [
        "Python","Java","JavaScript","TypeScript","SQL","R","Scala","Go","C++","C#",
        "TensorFlow","PyTorch","Keras","Scikit-learn","Pandas","NumPy","Spark",
        "Machine Learning","Deep Learning","NLP","MLOps","LLM","GenAI",
        "Docker","Kubernetes","AWS","GCP","Azure","Terraform","CI/CD",
        "React","Node.js","Spring Boot","FastAPI","Flask","Django",
        "PostgreSQL","MongoDB","Redis","Kafka","Airflow","dbt",
        "Power BI","Tableau","Excel","Statistics","Data Science",
    ]
    found_skills = [s for s in COMMON_SKILLS if re.search(rf"\b{re.escape(s)}\b", text, re.IGNORECASE)]
    raw_skills   = meta.get("skills") or meta.get("required_skills") or meta.get("qualifications") or []
    if isinstance(raw_skills, list):
        found_skills = list(dict.fromkeys(raw_skills + found_skills))

    primary_skills   = found_skills[:5]  if found_skills else ["Not specified"]
    secondary_skills = found_skills[5:9] if len(found_skills) > 5 else ["Not specified"]
    must_to_have     = found_skills[:3]  if found_skills else ["Not specified"]

    exp = get("experience", "years_of_experience", "experienceLevel")
    if exp == "Not specified":
        m = re.search(r"(\d+\+?\s*(?:to|-)\s*\d+\s*years?|\d+\+\s*years?)", text, re.IGNORECASE)
        if m: exp = m.group(1)

    salary = get("salary", "salary_package", "compensation", "ctc")
    if salary == "Not specified":
        m = re.search(r"(₹[\d,\.\s]+(?:LPA|lpa|L|lakhs?)|[\$£€][\d,]+(?:k|K)?(?:\s*-\s*[\d,]+(?:k|K)?)?)", text)
        if m: salary = m.group(1)

    email = get("email", "contact_email")
    if email == "Not specified":
        m = re.search(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}", text)
        if m: email = m.group(0)

    phone = get("phone", "contact_phone", "mobile")
    if phone == "Not specified":
        m = re.search(r"(\+?\d[\d\s\-]{8,14}\d)", text)
        if m: phone = m.group(1).strip()

    post_url    = get("url", "post_url", "job_url", "link", "applyUrl")
    date_posted = get("posted", "date_posted", "postedAt", "publishedAt", "posted_date")
    author_name = get("author", "author_name", "poster", "recruiter", "hiringManager")
    author_url  = get("author_linkedin_url", "authorUrl", "profileUrl")
    is_intern   = "Yes" if re.search(r"\b(intern|internship|trainee)\b", text, re.IGNORECASE) else "No"
    is_student  = "Yes" if re.search(r"\b(fresher|college|campus|graduate|0\s*years?)\b", text, re.IGNORECASE) else "No"

    return {
        "post_id":                      _make_id(text, keyword, idx),
        "role":                         role,
        "company_name":                 company,
        "location":                     location,
        "primary_skills":               primary_skills,
        "secondary_skills":             secondary_skills,
        "must_to_have":                 must_to_have,
        "years_of_experience":          exp,
        "looking_for_college_students": is_student,
        "intern":                       is_intern,
        "salary_package":               salary,
        "email":                        email,
        "phone":                        phone,
        "hiring_intent":                "Active",
        "author_name":                  author_name,
        "author_linkedin_url":          author_url,
        "post_url":                     post_url,
        "date_posted":                  date_posted,
        "keyword_matched":              keyword,
        "date_processed":               str(datetime.date.today()),
    }


# ── Utilities ─────────────────────────────────────────────────────────────────

def _dict_to_text(d: dict) -> str:
    parts    = []
    priority = ["title","job_title","company","company_name","location","description",
                "skills","required_skills","experience","salary","email","url","posted"]
    for k in priority:
        if k in d and d[k]:
            parts.append(f"{k}: {d[k]}")
    for k, v in d.items():
        if k not in priority and v:
            parts.append(f"{k}: {v}")
    return "\n".join(str(p) for p in parts)


def _make_id(text: str, keyword: str, idx: int) -> str:
    digest = hashlib.md5(f"{keyword}_{idx}_{text[:80]}".encode()).hexdigest()[:10]
    return f"{keyword[:8].lower().replace(' ','_')}_{digest}"


# ── smoke-test ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    sample = {
        "title":       "Senior Data Scientist",
        "company":     "Google",
        "location":    "Bangalore, India",
        "description": "We need Python, TensorFlow, SQL. 3+ years. Salary ₹20-30 LPA. hr@google.com",
        "url":         "https://linkedin.com/jobs/view/123456",
        "posted":      "2025-03-29",
    }
    result = extract_data(sample, "Data Scientist", 0)
    print(json.dumps(result, indent=2))
