"""Offline tests: taxonomy matching + gap engine. No API key required."""
from app.core.gap_engine import MIN_DEMAND_SHARE, compute_gaps
from app.core.taxonomy import load_taxonomy, match_mention, prerequisite_order
from app.schemas import MarketDemandProfile, SkillDemand, StudentProfile, StudentSkill


def demand(entries, role="Data Scientist", n=20):
    return MarketDemandProfile(
        target_role=role,
        postings_analysed=n,
        skills=[SkillDemand(skill_id=sid, name=sid, frequency=int(share * n),
                            share=share, posting_ids=[]) for sid, share in entries],
    )


class TestTaxonomyMatching:
    def test_exact_name(self):
        assert match_mention("Python")[0] == "python"

    def test_alias(self):
        assert match_mention("sklearn")[0] == "scikit-learn"
        assert match_mention("k8s")[0] == "kubernetes"

    def test_case_insensitive(self):
        assert match_mention("PYTORCH")[0] == "pytorch"

    def test_semantic_fallback(self):
        hit = match_mention("building neural networks")
        assert hit is not None
        assert hit[0] in ("deep-learning", "ml-fundamentals", "pytorch", "tensorflow")

    def test_garbage_rejected(self):
        assert match_mention("underwater basket weaving") is None

    def test_empty(self):
        assert match_mention("") is None


class TestPrerequisiteOrder:
    def test_prereq_comes_first(self):
        order = prerequisite_order(["react", "javascript", "typescript"])
        assert order.index("javascript") < order.index("react")
        assert order.index("javascript") < order.index("typescript")

    def test_chain(self):
        order = prerequisite_order(["rag", "llms", "nlp", "deep-learning"])
        assert order.index("deep-learning") < order.index("nlp")
        assert order.index("nlp") < order.index("llms")
        assert order.index("llms") < order.index("rag")

    def test_external_prereqs_ignored(self):
        # pytorch requires deep-learning, which is not in the set
        assert prerequisite_order(["pytorch"]) == ["pytorch"]

    def test_taxonomy_is_dag(self):
        taxonomy = load_taxonomy()
        order = prerequisite_order(list(taxonomy.keys()))
        assert len(order) == len(taxonomy)


class TestGapEngine:
    def test_missing_skill_is_gap(self):
        profile = StudentProfile(skills=[])
        report = compute_gaps(profile, demand([("python", 0.9)]),
                              {"python": "advanced"})
        assert len(report.gaps) == 1
        gap = report.gaps[0]
        assert gap.skill_id == "python"
        assert gap.current_level == "none"
        assert gap.gap_size == 3.0
        assert gap.priority == round(0.9 * 3.0, 4)

    def test_partial_mastery_shrinks_gap(self):
        profile = StudentProfile(skills=[
            StudentSkill(skill_id="python", name="Python", level="beginner")])
        report = compute_gaps(profile, demand([("python", 0.9)]),
                              {"python": "advanced"})
        assert report.gaps[0].gap_size == 2.0

    def test_met_requirement_is_strength(self):
        profile = StudentProfile(skills=[
            StudentSkill(skill_id="sql", name="SQL", level="advanced")])
        report = compute_gaps(profile, demand([("sql", 0.8)]), {"sql": "intermediate"})
        assert report.gaps == []
        assert report.strengths == ["SQL"]

    def test_low_demand_noise_filtered(self):
        profile = StudentProfile(skills=[])
        report = compute_gaps(profile, demand([("go", MIN_DEMAND_SHARE / 2)]))
        assert report.gaps == []

    def test_sorted_by_priority(self):
        profile = StudentProfile(skills=[])
        report = compute_gaps(
            profile,
            demand([("go", 0.3), ("python", 0.9), ("sql", 0.6)]),
            {sid: "advanced" for sid in ("go", "python", "sql")},
        )
        priorities = [g.priority for g in report.gaps]
        assert priorities == sorted(priorities, reverse=True)
        assert report.gaps[0].skill_id == "python"

    def test_unknown_skill_ids_skipped(self):
        report = compute_gaps(StudentProfile(skills=[]),
                              demand([("not-a-skill", 0.9)]))
        assert report.gaps == []
