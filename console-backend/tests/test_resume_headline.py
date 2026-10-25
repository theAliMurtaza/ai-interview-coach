import pytest

from app.services.resume_headline import detect_resume_header
from tests.test_interviews import _auth_headers


@pytest.mark.parametrize(
    ("headline", "role"),
    [
        ("Senior Full-Stack Developer", "fullstack"),
        ("Frontend Developer | Backend Developer", "fullstack"),
        ("React.js Developer", "frontend"),
        ("Back‑End Engineer", "backend"),
        ("Python Developer", "backend"),
        ("React Native Developer", "mobile"),
        ("Machine Learning Engineer", "data-ai"),
        ("Data Analyst", "data-ai"),
        ("DevOps Engineer", "devops"),
        ("QA Automation Engineer", "qa"),
    ],
)
def test_headline_selects_supported_role(headline, role):
    result = detect_resume_header(
        f"Alex Candidate\n{headline}\nSkills\nPython, React", ["Python", "React"]
    )
    assert result["headline"] == headline
    assert result["suggested_role"] == role


@pytest.mark.parametrize(
    "text",
    [
        "Alex Candidate\nExperience\nFrontend Developer",
        "Alex Candidate\nSkills: React, Python\nBackend Developer",
        "Alex Candidate\nSoftware Engineer\nProjects\nMobile App Developer",
        "Alex Candidate\nQA Engineer / Data Analyst",
        "Alex Candidate\nhttps://example.com/frontend\nEducation\nSoftware testing",
        "Alex Candidate\nMobile: +92 123456789\nSoftware Engineer\nSkills: Python",
    ],
)
def test_unclear_header_does_not_guess_from_past_work(text):
    assert detect_resume_header(text, ["React"])["suggested_role"] is None


async def test_uploaded_and_saved_resumes_return_detection(client, monkeypatch, tmp_path):
    from app.core.config import settings

    monkeypatch.setattr(settings, "LOCAL_STORAGE_DIR", str(tmp_path))
    headers = await _auth_headers(client)
    response = await client.post(
        "/api/v1/resumes/upload",
        headers=headers,
        files={
            "file": (
                "resume.txt",
                b"Alex Candidate\nBackend Developer\nSkills: Python, FastAPI, React",
                "text/plain",
            )
        },
    )
    assert response.status_code == 201
    resume = response.json()
    assert resume["headline"] == "Backend Developer"
    assert resume["suggested_role"] == "backend"
    assert resume["suggested_specialties"] == ["Python", "FastAPI"]
    assert "React" in resume["skills"]
    for url in ("/api/v1/resumes", f"/api/v1/resumes/{resume['id']}"):
        saved = (await client.get(url, headers=headers)).json()
        saved = saved[0] if isinstance(saved, list) else saved
        assert saved["suggested_role"] == "backend"
        assert saved["headline"] == resume["headline"]
