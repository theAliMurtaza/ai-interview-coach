"""Extract named projects from readable resume sections, including saved resumes."""

import re

from app.services.specialty_questions import detect_skills

PROJECT_SECTION = re.compile(
    r"^(?:(?:personal|academic|selected|technical|key|relevant)\s+)?projects?"
    r"(?:\s+(?:experience|portfolio))?\s*[:：]?\s*$",
    re.I,
)
NEXT_SECTION = re.compile(
    r"^(?:(?:technical|professional|work|relevant)\s+)?"
    r"(?:skills|experience|education|certifications|achievements|awards|languages|"
    r"interests|summary|references|employment)(?:\s*[:：].*)?\s*$",
    re.I,
)
DESCRIPTION = re.compile(
    r"^(?:built|developed|designed|implemented|created|integrated|used|using|"
    r"deployed|achieved|improved|led|managed|worked|responsible|features|technologies|"
    r"tech stack|stack|description|https?://|www\.)\b",
    re.I,
)


def clean_text(value, limit):
    return " ".join(value.split())[:limit] if isinstance(value, str) else ""


def extract_projects(raw_text: str) -> list[dict]:
    projects = []
    active = False
    current = None
    for raw in raw_text[:100000].splitlines():
        line = raw.strip().strip("#*_ ")
        if PROJECT_SECTION.fullmatch(line):
            active = True
            current = None
            continue
        if not active or not line:
            continue
        if NEXT_SECTION.match(line):
            active = False
            continue
        line = re.sub(r"^(?:[•●▪\-]|\d+[.)])\s+", "", line).strip()
        line = re.sub(r"^project\s*\d*\s*[-:]\s*", "", line, flags=re.I)
        # A title can be followed by its stack/date or an inline description.
        title = re.split(r"\s+[|–—]\s+|\s*:\s*", line, maxsplit=1)[0]
        is_title = (
            2 <= len(title) <= 120
            and len(title.split()) <= 14
            and not DESCRIPTION.match(line)
            and not title.endswith(".")
        )
        if is_title and len(projects) < 6:
            current = {"name": title, "description": line[len(title) :].strip(" :|-–—")}
            projects.append(current)
        elif current:
            current["description"] = clean_text(current["description"] + " " + line, 800)
    for project in projects:
        project["technologies"] = detect_skills(project["name"] + " " + project["description"])[:12]
    return projects


def resume_projects(raw_text: str, parsed: list[dict] | None = None) -> list[dict]:
    """Normalize AI fields and bound context; never invent a missing project name."""
    result = []
    seen = set()
    source = clean_text(raw_text, 100000).casefold()
    for project in list(parsed or []) + extract_projects(raw_text):
        if not isinstance(project, dict):
            continue
        name = clean_text(
            project.get("name") or project.get("title") or project.get("project_name"), 120
        )
        if not name or name.casefold() in seen or name.casefold() not in source:
            continue
        description = clean_text(project.get("description"), 800)
        technologies = project.get("technologies") or project.get("tech_stack") or []
        if isinstance(technologies, list):
            technologies = ", ".join(t for t in technologies if isinstance(t, str))
        technologies = detect_skills(f"{name} {description} {clean_text(technologies, 300)}")[:12]
        result.append({"name": name, "description": description, "technologies": technologies})
        seen.add(name.casefold())
        if len(result) == 6:
            break
    return result


def include_project_questions(seeds, projects, interview_type, difficulty, start_index=0):
    """Alternate resume projects with role/specialty questions using stable positions."""
    if not projects:
        return seeds
    output = list(seeds)
    for offset in range(len(output)):
        position = start_index + offset
        if position % 2:
            continue
        number = position // 2
        project = projects[number % len(projects)]
        name = project["name"]
        stack = ", ".join(project.get("technologies", [])[:4])
        context = f" Your resume mentions {stack}." if stack else ""
        kind = interview_type.value
        variant = number // len(projects)
        if kind == "behavioral" or (kind == "mixed" and variant % 3 == 1):
            prompt = (
                "Describe a challenge you faced, your personal responsibility, the action "
                "you took, and the outcome. What would you do differently?"
            )
            concepts = ["challenge", "responsibility", "action", "outcome"]
        elif kind == "system-design" or difficulty.value == "mid":
            prompt = (
                "Walk through the architecture and data flow. Which design trade-offs did "
                "you make, and how would you handle increased load or a component failure?"
                if variant % 2 == 0
                else "How would you monitor this project in production, test its failure modes, "
                "and roll out a change safely? Explain a concrete trade-off."
            )
            concepts = ["architecture", "data", "trade-off", "failure"]
        else:
            prompt = (
                "What problem does it solve, what did you personally implement, and how "
                "did you test that it worked? Explain one technical decision and its result."
                if variant % 2 == 0
                else "Describe a bug you encountered, how you found its cause, the fix you "
                "implemented, and how you tested against a regression."
            )
            concepts = ["problem", "implemented", "test", "result"]
        output[offset] = {
            "text": f'In your resume project "{name}": {prompt}{context}',
            "expected_concepts": concepts,
            "follow_up_hint": f'For "{name}", give a specific example of your contribution.',
        }
    return output
