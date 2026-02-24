import re


SKILL_KEYWORDS = (
    "python",
    "fastapi",
    "django",
    "sql",
    "postgresql",
    "aws",
    "docker",
    "kubernetes",
    "react",
    "javascript",
    "typescript",
)


def _extract_years_experience(text: str) -> int:
    years_match = re.search(r"(\d{1,2})\s*\+?\s*(?:years|yrs)", text)
    if years_match:
        return int(years_match.group(1))
    return 0


def _extract_email(text: str) -> str | None:
    email_match = re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", text)
    return email_match.group(0) if email_match else None


def _extract_skills(text: str) -> list[str]:
    lower_text = text.lower()
    return [skill for skill in SKILL_KEYWORDS if skill in lower_text]


def process_resume(payload: dict) -> dict:
    resume_text = payload.get("resume_text") or ""
    resume_url = payload.get("resume_url") or ""

    combined_text = f"{resume_text}\n{resume_url}"
    skills = _extract_skills(combined_text)
    years_experience = _extract_years_experience(combined_text)
    email = _extract_email(combined_text)

    return {
        "name": payload.get("candidate_name", "Unknown Candidate"),
        "email": email,
        "skills": skills,
        "years_experience": years_experience,
        "resume_url": resume_url,
    }
