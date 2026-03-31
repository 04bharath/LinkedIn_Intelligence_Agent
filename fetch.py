"""
fetch.py  –  LinkedIn Job Fetching Layer
Uses linkedin-jobs-api2.p.rapidapi.com (active 2025)
"""

import http.client
import json
from config import RAPIDAPI_KEY


def fetch_jobs(keyword: str, location: str = "India", limit: int = 10) -> list:
    """Fetch LinkedIn jobs. Falls back to mock data if API fails. Max `limit` results."""

    result = _try_api(keyword, location)
    if result:
        print(f"[fetch] ✅ Got {len(result)} jobs, returning top {limit}.")
        return result[:limit]

    print("[fetch] ⚠️  API failed — using mock data for demo.")
    return _mock_jobs(keyword, location)[:limit]


def _try_api(keyword: str, location: str) -> list:
    try:
        conn = http.client.HTTPSConnection(
            "linkedin-jobs-api2.p.rapidapi.com", timeout=15
        )
        headers = {
            "x-rapidapi-key":  RAPIDAPI_KEY,
            "x-rapidapi-host": "linkedin-jobs-api2.p.rapidapi.com",
            "Content-Type":    "application/json"
        }

        # Try active jobs endpoint first
        conn.request("GET", "/active-jb-1h", headers=headers)
        res  = conn.getresponse()
        body = res.read().decode("utf-8")
        print(f"[fetch] linkedin-jobs-api2 /active-jb-1h → {res.status}")

        if res.status == 200:
            data = json.loads(body)
            jobs = _unwrap(data)
            if jobs:
                # Filter by keyword if possible
                filtered = [
                    j for j in jobs
                    if keyword.lower() in str(j).lower()
                ]
                return filtered if filtered else jobs

        # Fallback to 7-day endpoint
        conn2 = http.client.HTTPSConnection(
            "linkedin-jobs-api2.p.rapidapi.com", timeout=15
        )
        conn2.request("GET", "/active-jb-7d", headers=headers)
        res2  = conn2.getresponse()
        body2 = res2.read().decode("utf-8")
        print(f"[fetch] linkedin-jobs-api2 /active-jb-7d → {res2.status}")

        if res2.status == 200:
            data2 = json.loads(body2)
            return _unwrap(data2)

        print(f"[fetch] API error: {body[:200]}")
        return []

    except Exception as e:
        print(f"[fetch] Request failed: {e}")
        return []


def _unwrap(data) -> list:
    if isinstance(data, list) and len(data) > 0:
        return data
    if isinstance(data, dict):
        for key in ("data", "jobs", "results", "items", "response"):
            if key in data and isinstance(data[key], list) and len(data[key]) > 0:
                return data[key]
    return []


def _mock_jobs(keyword: str, location: str) -> list:
    companies = [
        "Google", "Microsoft", "Amazon", "Flipkart", "Infosys",
        "TCS", "Wipro", "Razorpay", "Zepto", "PhonePe"
    ]
    skills_map = {
        "data scientist":  ["Python", "R", "Statistics", "Pandas", "Scikit-learn", "SQL"],
        "ml engineer":     ["PyTorch", "TensorFlow", "MLOps", "Kubernetes", "Python"],
        "backend":         ["Java", "Spring Boot", "Microservices", "PostgreSQL", "Redis"],
        "frontend":        ["React", "TypeScript", "CSS", "Next.js", "GraphQL"],
        "devops":          ["Kubernetes", "Terraform", "AWS", "CI/CD", "Docker"],
        "data engineer":   ["Python", "Spark", "Airflow", "SQL", "dbt", "Kafka"],
        "default":         ["Python", "SQL", "Machine Learning", "TensorFlow", "Docker"],
    }
    key    = keyword.lower()
    skills = next((v for k, v in skills_map.items() if k in key), skills_map["default"])

    mock = []
    for i, company in enumerate(companies):
        mock.append({
            "title":       f"Senior {keyword}",
            "company":     company,
            "location":    f"{location}",
            "description": (
                f"We are hiring a Senior {keyword} at {company} in {location}. "
                f"Required skills: {', '.join(skills[:3])}. "
                f"Experience: {2 + i % 4}+ years. "
                f"Salary: ₹{10 + i*2}-{18 + i*2} LPA. "
                f"Contact: hr@{company.lower().replace(' ','')}.com. "
                f"Apply: https://linkedin.com/jobs/view/{1000000 + i}"
            ),
            "job_id":  f"mock_{keyword.replace(' ','_')}_{i}",
            "posted":  "2025-03-29",
            "url":     f"https://linkedin.com/jobs/view/{1000000 + i}",
        })
    return mock


if __name__ == "__main__":
    jobs = fetch_jobs("Data Scientist", "India")
    print(f"\nFetched {len(jobs)} jobs")
    if jobs:
        print("Sample:", str(jobs[0])[:300])