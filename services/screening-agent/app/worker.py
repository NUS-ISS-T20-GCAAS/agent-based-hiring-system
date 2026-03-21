"""
Worker utility functions for screening
Provides heuristic fallback and result normalization
"""


def heuristic_screen_candidate(
    *, 
    parsed_resume: dict, 
    job_description: str,
    job_requirements: dict = None
) -> dict:
    """
    Rule-based screening fallback when LLM is unavailable
    
    Algorithm:
    1. Extract candidate skills and normalize to lowercase
    2. Extract required skills from job description and requirements
    3. Calculate skill match ratio
    4. Factor in years of experience
    5. Compute weighted qualification score (70% skills, 30% experience)
    """
    # Extract and normalize candidate data
    candidate_skills = [
        skill.lower() 
        for skill in parsed_resume.get("skills", []) 
        if isinstance(skill, str)
    ]
    years_experience = parsed_resume.get("years_experience") or 0
    
    # Build required skills set from multiple sources
    required_skills = set()
    
    # From job description (word extraction)
    if job_description:
        words = job_description.lower().split()
        required_skills.update(word for word in words if len(word) > 2)
    
    # From structured requirements (if provided)
    if job_requirements:
        if "required_skills" in job_requirements:
            required_skills.update(
                skill.lower() 
                for skill in job_requirements["required_skills"]
            )
        if "preferred_skills" in job_requirements:
            required_skills.update(
                skill.lower() 
                for skill in job_requirements["preferred_skills"]
            )
    
    required_skills = sorted(required_skills)
    required_skill_set = set(required_skills)
    
    # Calculate matches and misses
    matched_skills = [
        skill 
        for skill in candidate_skills 
        if skill in required_skill_set
    ]
    
    missing_skills = [
        skill 
        for skill in required_skills 
        if skill in required_skill_set - set(matched_skills)
    ]
    
    # Calculate component scores
    if required_skills:
        skill_score = len(matched_skills) / len(required_skills)
    else:
        skill_score = 1.0  # No requirements = automatic pass on skills
    
    # Experience score (normalized to 8 years as "expert" level)
    if isinstance(years_experience, (int, float)):
        experience_score = min(1.0, years_experience / 8)
    else:
        experience_score = 0.0
    
    # Weighted qualification score: 70% skills + 30% experience
    qualification_score = round((skill_score * 0.7) + (experience_score * 0.3), 3)
    
    # Pass threshold is 0.6 (60%)
    meets_threshold = qualification_score >= 0.6
    
    # Confidence based on data quality
    # Base confidence 0.65, up to 0.90 with more skills
    confidence = round(0.65 + min(0.25, 0.05 * len(candidate_skills)), 2)
    
    # Build explanation
    explanation = (
        f"Heuristic screening: score={qualification_score:.1%} "
        f"(skills={skill_score:.1%}, experience={experience_score:.1%}); "
        f"matched={len(matched_skills)}/{len(required_skills)} skills; "
        f"years={years_experience}"
    )
    
    return {
        "qualification_score": qualification_score,
        "meets_threshold": meets_threshold,
        "matched_skills": matched_skills,
        "missing_skills": missing_skills[:10],  # Limit output
        "years_experience": years_experience if isinstance(years_experience, (int, float)) else 0,
        "confidence": confidence,
        "explanation": explanation,
    }


def coerce_screening_result(result: dict) -> dict:
    """
    Normalize and validate LLM screening result
    
    Ensures all required fields are present with correct types
    Handles missing or malformed data gracefully
    """
    # Extract and validate matched/missing skills
    matched_skills = result.get("matched_skills")
    if not isinstance(matched_skills, list):
        matched_skills = []
    
    missing_skills = result.get("missing_skills")
    if not isinstance(missing_skills, list):
        missing_skills = []
    
    # Extract and validate numeric scores
    qualification_score = result.get("qualification_score")
    try:
        qualification_score = float(qualification_score or 0.0)
        qualification_score = max(0.0, min(1.0, qualification_score))  # Clamp to [0, 1]
    except (TypeError, ValueError):
        qualification_score = 0.0
    
    # Extract and validate confidence
    confidence = result.get("confidence")
    try:
        confidence = float(confidence or 0.0)
        confidence = max(0.0, min(1.0, confidence))  # Clamp to [0, 1]
    except (TypeError, ValueError):
        confidence = 0.5  # Default medium confidence
    
    # Extract years of experience
    years_experience = result.get("years_experience")
    try:
        years_experience = int(float(years_experience or 0))
        years_experience = max(0, years_experience)  # No negative years
    except (TypeError, ValueError):
        years_experience = 0
    
    # Extract or compute meets_threshold
    meets_threshold = result.get("meets_threshold")
    if meets_threshold is None:
        meets_threshold = qualification_score >= 0.6
    else:
        meets_threshold = bool(meets_threshold)
    
    # Extract explanation
    explanation = result.get("explanation")
    if not explanation or not isinstance(explanation, str):
        explanation = f"Qualification screening completed with score {qualification_score:.1%}"
    
    return {
        "qualification_score": qualification_score,
        "meets_threshold": meets_threshold,
        "matched_skills": matched_skills,
        "missing_skills": missing_skills,
        "years_experience": years_experience,
        "confidence": confidence,
        "explanation": explanation,
    }