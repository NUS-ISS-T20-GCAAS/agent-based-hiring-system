import re


SKILL_KEYWORDS = (
    "api design",
    "ci/cd",
    "python",
    "fastapi",
    "django",
    "flask",
    "sql",
    "postgresql",
    "redis",
    "aws",
    "docker",
    "kubernetes",
    "react",
    "javascript",
    "typescript",
    "testing",
    "git",
)


def normalize_years_experience(value) -> int:
    if isinstance(value, (int, float)):
        return max(0, int(value))
    if isinstance(value, str):
        match = re.search(r"\d+", value)
        if match:
            return int(match.group(0))
    return 0


def normalize_skills(value) -> list[str]:
    if not isinstance(value, list):
        return []

    seen: set[str] = set()
    normalized: list[str] = []
    for item in value:
        if not isinstance(item, str):
            continue
        skill = item.strip().lower()
        if not skill or skill in seen:
            continue
        seen.add(skill)
        normalized.append(skill)
    return normalized


def _extract_years_experience(text: str) -> int:
    years_match = re.search(r"(\d{1,2})\s*\+?\s*(?:years|yrs)", text)
    if years_match:
        return int(years_match.group(1))
    return 0


def _extract_email(text: str) -> str | None:
    email_match = re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", text)
    return email_match.group(0) if email_match else None


def _extract_name(text: str) -> str | None:
    for raw_line in text.splitlines():
        line = " ".join(raw_line.strip().split())
        if not line:
            continue
        lower_line = line.lower()
        if "@" in line or "http" in lower_line or "upload://" in lower_line:
            continue
        if re.search(r"\d", line):
            continue
        if len(line.split()) > 6:
            continue
        return line
    return None


def _extract_summary(text: str) -> str | None:
    cleaned = " ".join(text.split())
    if not cleaned:
        return None

    sentences = re.split(r"(?<=[.!?])\s+", cleaned)
    summary_parts: list[str] = []
    for sentence in sentences:
        snippet = sentence.strip()
        if not snippet:
            continue
        summary_parts.append(snippet)
        if len(" ".join(summary_parts)) >= 180 or len(summary_parts) >= 2:
            break

    summary = " ".join(summary_parts).strip()
    if len(summary) > 220:
        summary = summary[:217].rstrip() + "..."
    return summary or None


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
    name = _extract_name(resume_text)
    summary = _extract_summary(resume_text)

    return {
        "name": payload.get("candidate_name") or name or "Unknown Candidate",
        "email": email,
        "skills": skills,
        "years_experience": years_experience,
        "resume_url": resume_url,
        "summary": summary,
    }


def coerce_resume_result(result: dict, *, resume_url: str) -> dict:
    return {
        "name": result.get("name") or "Unknown Candidate",
        "email": result.get("email"),
        "skills": normalize_skills(result.get("skills")),
        "years_experience": normalize_years_experience(result.get("years_experience")),
        "resume_url": resume_url,
        "summary": result.get("summary"),
    }
