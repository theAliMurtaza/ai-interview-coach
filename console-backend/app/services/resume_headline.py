"""Conservative role detection from the resume header, not past employment."""

import re
import unicodedata

ROLE_PATTERNS = {
    "fullstack": r"\b(?:full[ -]*stack|mern|mean)\b",
    "mobile": r"\b(?:mobile|android|ios|flutter|react native|swift|kotlin)\b",
    "frontend": (
        r"\bfront[ -]*end\b|"
        r"\b(?:react(?:\.?js)?|angular|vue(?:\.?js)?|ui)\s+(?:developer|engineer)\b"
    ),
    "backend": (
        r"\bback[ -]*end\b|"
        r"\b(?:python|java|node(?:\.js)?|django|fastapi|golang|php|\.net)\s+"
        r"(?:developer|engineer)\b"
    ),
    "data-ai": (
        r"\b(?:data (?:scientist|engineer|analyst)|machine learning|deep learning|artificial"
        r" intelligence|(?:ai|ml|nlp)\s+(?:engineer|developer|researcher))\b"
    ),
    "devops": r"\b(?:devops|devsecops|site reliability|sre|cloud engineer|platform engineer)\b",
    "qa": (
        r"\b(?:qa|sdet|quality assurance|test automation|automation (?:engineer|tester)|software"
        r" test(?:er|ing)|test engineer)\b"
    ),
}
ROLE_SKILLS = {
    "frontend": {
        "react",
        "javascript",
        "typescript",
        "next.js",
        "vue",
        "angular",
        "html",
        "css",
        "graphql",
        "rest",
        "git",
        "playwright",
        "cypress",
    },
    "backend": {
        "python",
        "fastapi",
        "django",
        "flask",
        "node.js",
        "javascript",
        "typescript",
        "java",
        "c#",
        ".net",
        "go",
        "rust",
        "sql",
        "postgresql",
        "mysql",
        "mongodb",
        "redis",
        "graphql",
        "rest",
        "docker",
        "aws",
        "git",
    },
    "mobile": {
        "swift",
        "kotlin",
        "java",
        "flutter",
        "react native",
        "javascript",
        "typescript",
        "rest",
        "graphql",
        "git",
    },
    "data-ai": {
        "python",
        "sql",
        "postgresql",
        "machine learning",
        "deep learning",
        "nlp",
        "tensorflow",
        "pytorch",
        "pandas",
        "numpy",
        "aws",
        "gcp",
        "git",
    },
    "devops": {
        "docker",
        "kubernetes",
        "aws",
        "azure",
        "gcp",
        "terraform",
        "git",
        "python",
        "go",
        "redis",
        "postgresql",
    },
    "qa": {
        "selenium",
        "playwright",
        "cypress",
        "python",
        "javascript",
        "typescript",
        "java",
        "sql",
        "rest",
        "git",
    },
}
ROLE_SKILLS["fullstack"] = ROLE_SKILLS["frontend"] | ROLE_SKILLS["backend"]
SECTION = re.compile(
    r"^(?:professional summary|summary|profile|about me|objective|skills|technical"
    r" skills|experience|work experience|professional"
    r" experience|employment|projects|education|certifications)\b",
    re.I,
)
GENERIC = re.compile(
    r"\b(?:software (?:engineer|developer)|web developer|computer science student)\b", re.I
)


def detect_resume_header(raw_text: str, skills: list[str]) -> dict:
    generic = None
    lines = [line.strip() for line in raw_text[:3000].splitlines() if line.strip()][:12]
    for original in lines:
        line = unicodedata.normalize("NFKC", original)
        line = re.sub(r"[‐‑–—]", "-", line)
        if SECTION.match(line):
            break
        if re.match(r"^(?:mobile|phone|tel|contact|address|location)\s*(?::|\+|\d)", line, re.I):
            continue
        if len(line) > 160 or len(line.split()) > 20 or re.search(r"https?://|www\.|@", line):
            continue
        matches = {
            role for role, pattern in ROLE_PATTERNS.items() if re.search(pattern, line, re.I)
        }
        if matches == {"frontend", "backend"} or (
            "fullstack" in matches and matches <= {"fullstack", "frontend", "backend"}
        ):
            matches = {"fullstack"}
        if matches:
            role = next(iter(matches)) if len(matches) == 1 else None
            return {
                "headline": original,
                "suggested_role": role,
                "suggested_specialties": (
                    [skill for skill in skills if skill.casefold() in ROLE_SKILLS[role]][:20]
                    if role
                    else skills[:20]
                ),
            }
        if GENERIC.search(line) and generic is None:
            generic = original
    return {"headline": generic, "suggested_role": None, "suggested_specialties": skills[:20]}
