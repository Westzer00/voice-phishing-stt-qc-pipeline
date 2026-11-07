from src.review_planner import ReviewIssue, build_review_plan


def test_two_far_issues_are_multi_local():
    issues = [
        ReviewIssue("a", 5, 7, (1,), "AUDIO_REQUIRED"),
        ReviewIssue("b", 25, 27, (8,), "AUDIO_REQUIRED"),
    ]
    plan = build_review_plan(issues, duration_sec=60)
    assert plan["audio_scope"] == "MULTI_LOCAL"
    assert len(plan["windows"]) == 2
