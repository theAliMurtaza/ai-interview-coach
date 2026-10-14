"""Versioned application routes."""

from fastapi import APIRouter

from app.api.v1 import (
    answers,
    auth,
    dashboard,
    evaluations,
    files,
    interviews,
    jobs,
    knowledge_base,
    learning_plans,
    matching,
    questions,
    reports,
    resumes,
    subscriptions,
    users,
    voice,
    webhooks,
)

api_router = APIRouter()

# Implemented end-to-end:
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(interviews.router)
api_router.include_router(questions.router)
api_router.include_router(answers.router)
api_router.include_router(evaluations.router)

# Stubbed — routers exist and mount cleanly, but have no real endpoints
# yet. See each module's docstring for the implementation plan.
api_router.include_router(resumes.router)
api_router.include_router(jobs.router)
api_router.include_router(matching.router)
api_router.include_router(knowledge_base.router)
api_router.include_router(reports.router)
api_router.include_router(dashboard.router)
api_router.include_router(learning_plans.router)
api_router.include_router(subscriptions.router)
api_router.include_router(webhooks.router)
api_router.include_router(voice.router)

api_router.include_router(files.router)
