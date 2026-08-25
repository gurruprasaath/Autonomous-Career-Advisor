"""LangGraph orchestration: the multi-agent pipeline with a revision loop.

    profile → market → gap → plan → verify ──pass──→ END
                               ↑                │
                               └──── revise ────┘   (≤ max_revision_loops)
"""
import logging
from functools import lru_cache
from typing import Optional, TypedDict

from langgraph.graph import END, StateGraph

from ..agents.market_agent import analyse_market
from ..agents.planner_agent import build_path
from ..agents.profile_agent import build_profile
from ..agents.verifier_agent import verify_path
from ..agents.review_agent import review_resume
from ..config import get_settings
from ..schemas import (
    AdviseRequest,
    AdvisorResult,
    FGCRCritique,
    GapReport,
    LearningPath,
    MarketDemandProfile,
    StudentProfile,
    ResumeReviewResult,
)
from .gap_engine import compute_gaps

log = logging.getLogger(__name__)


class AdvisorState(TypedDict, total=False):
    request: AdviseRequest
    profile: StudentProfile
    demand: MarketDemandProfile
    required_levels: dict
    gap_report: GapReport
    path: Optional[LearningPath]
    critique: Optional[FGCRCritique]
    resume_review: Optional[ResumeReviewResult]
    revision_request: str
    revisions: int
    notes: list


def profile_node(state: AdvisorState) -> dict:
    req = state["request"]
    profile, notes = build_profile(req.resume_text, req.target_role,
                                   req.hours_per_week, req.education)
    return {"profile": profile, "notes": state.get("notes", []) + notes}


def review_node(state: AdvisorState) -> dict:
    req = state["request"]
    review, notes = review_resume(req.resume_text, req.target_role)
    return {"resume_review": review, "notes": state.get("notes", []) + notes}


def market_node(state: AdvisorState) -> dict:
    demand, required_levels, notes = analyse_market(state["request"].target_role)
    return {"demand": demand, "required_levels": required_levels,
            "notes": state.get("notes", []) + notes}


def gap_node(state: AdvisorState) -> dict:
    report = compute_gaps(state["profile"], state["demand"], state["required_levels"])
    return {"gap_report": report}


def plan_node(state: AdvisorState) -> dict:
    path, notes = build_path(state["profile"], state["gap_report"],
                             revision_request=state.get("revision_request", ""))
    return {"path": path, "notes": state.get("notes", []) + notes}


def verify_node(state: AdvisorState) -> dict:
    critique, notes = verify_path(state["path"], state["gap_report"], state["profile"])
    update: dict = {"critique": critique, "notes": state.get("notes", []) + notes}
    if not critique.passed:
        update["revision_request"] = critique.revision_request
        update["revisions"] = state.get("revisions", 0) + 1
    return update


def route_after_verify(state: AdvisorState) -> str:
    critique = state["critique"]
    if critique.passed:
        return "pass"
    if state.get("revisions", 0) > get_settings().max_revision_loops:
        log.info("revision budget exhausted; delivering best-effort path")
        return "pass"
    log.info("verifier rejected path (revision %d): %s",
             state.get("revisions", 0), critique.revision_request[:120])
    return "revise"


@lru_cache
def build_graph():
    g = StateGraph(AdvisorState)
    g.add_node("profile", profile_node)
    g.add_node("review", review_node)
    g.add_node("market", market_node)
    g.add_node("gap", gap_node)
    g.add_node("plan", plan_node)
    g.add_node("verify", verify_node)

    g.set_entry_point("profile")
    g.add_edge("profile", "review")
    g.add_edge("review", "market")
    g.add_edge("market", "gap")
    g.add_edge("gap", "plan")
    g.add_edge("plan", "verify")
    g.add_conditional_edges("verify", route_after_verify,
                            {"revise": "plan", "pass": END})
    return g.compile()


def run_advisor(request: AdviseRequest) -> AdvisorResult:
    final = build_graph().invoke({"request": request, "revisions": 0, "notes": []})
    critique: FGCRCritique | None = final.get("critique")
    notes = list(final.get("notes", []))
    if critique and not critique.passed:
        notes.append("Verifier did not fully pass this path within the revision "
                     "budget — issues are listed in the critique.")
    return AdvisorResult(
        profile=final["profile"],
        demand=final["demand"],
        gap_report=final["gap_report"],
        path=final.get("path"),
        critique=critique,
        resume_review=final.get("resume_review"),
        revisions_used=final.get("revisions", 0),
        notes=notes,
    )
