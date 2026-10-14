"""Deterministic specialty questions and bounded skill detection for offline mode."""

import re

from app.models.interview import DifficultyLevel, InterviewType

# Each entry pairs a concrete discussion topic with concepts used by the evaluator.
TOPICS = {
    "React": ("state updates and component rendering", ["state", "props", "render", "hooks"]),
    "JavaScript": (
        "asynchronous execution and the event loop",
        ["promise", "event loop", "async", "await"],
    ),
    "TypeScript": (
        "type safety at an external API boundary",
        ["type", "validation", "unknown", "narrowing"],
    ),
    "Python": (
        "iterators and memory-efficient data processing",
        ["iterator", "generator", "memory", "yield"],
    ),
    "FastAPI": (
        "request validation and asynchronous endpoints",
        ["validation", "async", "dependency", "pydantic"],
    ),
    "Django": ("database access in a web request", ["queryset", "orm", "query", "transaction"]),
    "Flask": (
        "request handling and application structure",
        ["route", "request", "blueprint", "context"],
    ),
    "Node.js": ("concurrent I/O and blocking work", ["event loop", "async", "worker", "blocking"]),
    "Next.js": ("server rendering and data caching", ["server", "client", "cache", "hydration"]),
    "Vue": ("reactivity and component communication", ["reactivity", "props", "computed", "event"]),
    "Angular": (
        "dependency injection and component data flow",
        ["dependency", "component", "service", "observable"],
    ),
    "HTML": ("accessible form structure", ["semantic", "label", "input", "accessibility"]),
    "CSS": ("responsive layouts across screen sizes", ["flex", "grid", "media", "layout"]),
    "SQL": ("joins and query performance", ["join", "index", "query", "explain"]),
    "PostgreSQL": (
        "transaction isolation and concurrent updates",
        ["transaction", "isolation", "lock", "index"],
    ),
    "MySQL": ("indexes and transaction boundaries", ["index", "transaction", "query", "lock"]),
    "MongoDB": (
        "document modeling and query patterns",
        ["document", "index", "embedding", "reference"],
    ),
    "Redis": ("cache freshness and failure handling", ["cache", "ttl", "invalidation", "fallback"]),
    "GraphQL": (
        "schema design and resolving nested queries",
        ["schema", "resolver", "query", "batching"],
    ),
    "REST": ("HTTP API contracts and retry safety", ["http", "idempotency", "status", "resource"]),
    "Docker": (
        "reproducible images and runtime configuration",
        ["image", "layer", "container", "volume"],
    ),
    "Kubernetes": (
        "healthy deployments and service discovery",
        ["pod", "service", "probe", "deployment"],
    ),
    "AWS": (
        "secure and reliable cloud workloads",
        ["iam", "availability", "monitoring", "scaling"],
    ),
    "Azure": (
        "secure and reliable cloud workloads",
        ["identity", "availability", "monitoring", "scaling"],
    ),
    "GCP": (
        "secure and reliable cloud workloads",
        ["iam", "availability", "monitoring", "scaling"],
    ),
    "Terraform": (
        "safe infrastructure changes and shared state",
        ["state", "plan", "provider", "locking"],
    ),
    "Git": ("collaborative branch and change management", ["commit", "merge", "branch", "rebase"]),
    "Java": (
        "collections and concurrency",
        ["collection", "thread", "synchronization", "exception"],
    ),
    "C++": ("ownership and resource lifetime", ["raii", "ownership", "pointer", "destructor"]),
    "C#": ("asynchronous work and resource management", ["task", "async", "await", "dispose"]),
    ".NET": (
        "dependency injection and API request handling",
        ["dependency", "middleware", "scope", "async"],
    ),
    "Go": ("concurrent work and cancellation", ["goroutine", "channel", "context", "cancellation"]),
    "Rust": ("safe ownership and shared access", ["ownership", "borrow", "lifetime", "reference"]),
    "Swift": (
        "state and asynchronous work in mobile apps",
        ["state", "async", "task", "main actor"],
    ),
    "Kotlin": (
        "structured concurrency in mobile apps",
        ["coroutine", "scope", "cancellation", "dispatcher"],
    ),
    "Flutter": ("widget state and rendering performance", ["widget", "state", "build", "layout"]),
    "React Native": (
        "mobile state and rendering performance",
        ["component", "state", "list", "native"],
    ),
    "Machine Learning": (
        "model evaluation without data leakage",
        ["training", "validation", "leakage", "metric"],
    ),
    "Deep Learning": (
        "training stability and generalization",
        ["gradient", "loss", "regularization", "validation"],
    ),
    "NLP": (
        "text representation and evaluation",
        ["tokenization", "embedding", "evaluation", "dataset"],
    ),
    "TensorFlow": (
        "training pipelines and model validation",
        ["tensor", "batch", "loss", "validation"],
    ),
    "PyTorch": (
        "training loops and gradient management",
        ["tensor", "gradient", "optimizer", "loss"],
    ),
    "Pandas": (
        "cleaning and aggregating tabular data",
        ["dataframe", "groupby", "missing", "vectorization"],
    ),
    "NumPy": (
        "array operations and memory usage",
        ["array", "broadcasting", "shape", "vectorization"],
    ),
    "Selenium": ("reliable browser automation", ["locator", "wait", "assertion", "isolation"]),
    "Playwright": (
        "reliable end-to-end browser tests",
        ["locator", "assertion", "isolation", "fixture"],
    ),
    "Cypress": (
        "reliable end-to-end browser tests",
        ["assertion", "fixture", "intercept", "isolation"],
    ),
}

ALIASES = {
    "React": ["react", "react.js", "reactjs"],
    "Node.js": ["node.js", "nodejs"],
    "Next.js": ["next.js", "nextjs"],
    "Vue": ["vue", "vue.js", "vuejs"],
    "PostgreSQL": ["postgresql", "postgres"],
    "Go": ["golang", "go language", "go programming"],
    "Machine Learning": ["machine learning", "scikit-learn"],
    "AWS": ["aws", "amazon web services"],
    "GCP": ["gcp", "google cloud"],
    "NLP": ["nlp", "natural language processing"],
}


def detect_skills(text: str) -> list[str]:
    return [
        skill
        for skill in TOPICS
        if any(
            re.search(r"(?<![\w+#])" + re.escape(alias) + r"(?![\w+#])", text, re.I)
            for alias in ALIASES.get(skill, [skill])
        )
    ]


def specialty_question_set(*, specialties, interview_type, difficulty, count, start_index=0):
    result = []
    guidance = {
        DifficultyLevel.INTERNSHIP: "Explain the fundamentals with a small example.",
        DifficultyLevel.JUNIOR: (
            "Walk through a practical implementation and how you would test it."
        ),
        DifficultyLevel.MID: (
            "Compare alternatives, explain trade-offs, and cover production failure modes."
        ),
    }[difficulty]
    lookup = {
        alias.casefold(): value
        for name, value in TOPICS.items()
        for alias in [name, *ALIASES.get(name, [])]
    }
    for index in range(start_index, start_index + count):
        specialty = specialties[index % len(specialties)]
        variant = index // len(specialties)
        kind = interview_type
        if kind == InterviewType.MIXED:
            # Rotate each specialty through all styles, even with three specialties.
            kind = [InterviewType.TECHNICAL, InterviewType.BEHAVIORAL, InterviewType.SYSTEM_DESIGN][
                (variant + index % len(specialties)) % 3
            ]
        topic, concepts = lookup.get(
            specialty.casefold(),
            (
                "a feature in your area of expertise",
                ["requirements", "implementation", "testing", "trade-off"],
            ),
        )
        if kind == InterviewType.BEHAVIORAL:
            prompts = [
                (
                    f"Describe a challenging project involving {specialty}. What was your"
                    " contribution and the outcome?"
                ),
                f"Tell me about a disagreement on a {specialty} project. How did you resolve it?",
                f"Describe a mistake or failed approach involving {specialty}. What did you learn?",
                (
                    f"How did you explain a {specialty} decision to a teammate unfamiliar with it?"
                    " Give a specific example."
                ),
            ]
            concepts = ["situation", "task", "action", "result"]
            suffix = (
                "Use a work, course, or personal project and explain the situation, task, action,"
                " and result."
            )
        elif kind == InterviewType.SYSTEM_DESIGN:
            prompts = [
                (
                    f"Design a service or application using {specialty}. Where does it fit, and how"
                    f" would you handle {topic}?"
                ),
                (
                    f"A system using {specialty} must handle ten times more traffic or data. How"
                    " would you find and address its bottlenecks?"
                ),
                (
                    f"Design a recovery strategy for a system that depends on {specialty}. How"
                    " would you detect failures and restore service?"
                ),
                (
                    f"How would you evolve a production system using {specialty} without disrupting"
                    " its users?"
                ),
            ]
            concepts = ["requirements", "trade-off", "monitoring", "scaling"]
            suffix = guidance
        else:
            prompts = [
                f"In {specialty}, how would you approach {topic}?",
                (
                    f"Show how you would test {topic} in a {specialty} project. Which edge cases"
                    " matter?"
                ),
                (
                    f"A {specialty} feature involving {topic} behaves incorrectly. How would you"
                    " investigate and fix it?"
                ),
                (
                    f"What mistakes should a team avoid when implementing {topic} with {specialty},"
                    " and why?"
                ),
                f"How would you measure and improve the performance of {topic} in {specialty}?",
                (
                    f"Review an implementation of {topic} in {specialty}. What would you check"
                    " before releasing it?"
                ),
            ]
            suffix = guidance
        result.append(
            {
                "text": f"{prompts[variant % len(prompts)]} {suffix}",
                "expected_concepts": list(concepts),
                "follow_up_hint": (
                    f"Give a concrete {specialty} example and explain one trade-off or lesson."
                ),
            }
        )
    return result
