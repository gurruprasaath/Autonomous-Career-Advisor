"""Deterministic skill-gap computation.

gap = demanded skills (from market evidence) − student skills (from profile),
compared at mastery level over taxonomy nodes.

    priority = demand_share × gap_size

No LLM involved: every number in the gap report is reproducible and
traceable to specific job postings — the key differentiator from
prompt-based gap guessing (cf. GenMentor).
"""
from ..schemas import (
    MASTERY_SCORE,
    GapReport,
    MarketDemandProfile,
    SkillGap,
    StudentProfile,
)
from .taxonomy import load_taxonomy

# A skill demanded by fewer than this share of postings is noise, not a gap.
MIN_DEMAND_SHARE = 0.15

_LEVEL_BY_SCORE = {v: k for k, v in MASTERY_SCORE.items()}


def compute_gaps(
    profile: StudentProfile,
    demand: MarketDemandProfile,
    required_levels: dict[str, str] | None = None,
) -> GapReport:
    """required_levels: skill_id -> level the market asks for (defaults to
    'intermediate' when the provider carries no level annotations)."""
    taxonomy = load_taxonomy()
    have = {s.skill_id: MASTERY_SCORE[s.level] for s in profile.skills}
    required_levels = required_levels or {}

    gaps: list[SkillGap] = []
    strengths: list[str] = []

    for sd in demand.skills:
        if sd.share < MIN_DEMAND_SHARE or sd.skill_id not in taxonomy:
            continue
        required_level = required_levels.get(sd.skill_id, "intermediate")
        required = MASTERY_SCORE[required_level]
        current = have.get(sd.skill_id, 0.0)
        gap_size = required - current
        if gap_size <= 0:
            strengths.append(taxonomy[sd.skill_id].name)
            continue
        gaps.append(SkillGap(
            skill_id=sd.skill_id,
            name=taxonomy[sd.skill_id].name,
            demand_share=round(sd.share, 3),
            current_level=_LEVEL_BY_SCORE[current],
            required_level=required_level,  # type: ignore[arg-type]
            gap_size=round(gap_size, 2),
            priority=round(sd.share * gap_size, 4),
        ))

    gaps.sort(key=lambda g: g.priority, reverse=True)
    return GapReport(target_role=demand.target_role, gaps=gaps, strengths=strengths)
