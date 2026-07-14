from linkedin_insight_engine.critic_agent import CriticAgent
from linkedin_insight_engine.models import Draft
from linkedin_insight_engine.state_store import InMemoryStateStore


def test_critic_accepts_compliant_draft():
    store = InMemoryStateStore()
    draft = Draft(
        text=(
            "One queue removed a 30 minute failure window.\n\n"
            "- The pipeline stores approval state before the job exits.\n\n"
            "- Publishing re-validates the 3,000 character limit before calling LinkedIn.\n\n"
            "What would you measure first? Comment with the metric you would trust."
        ),
        topic_fingerprint="abc",
    )

    critique = CriticAgent(store).evaluate(draft)

    assert critique.passed


def test_critic_rejects_missing_cta_and_fact():
    store = InMemoryStateStore()
    draft = Draft(text="This is an interesting architecture.\n\nWhat do you think?", topic_fingerprint="abc")

    critique = CriticAgent(store).evaluate(draft)

    assert not critique.passed
    assert any("concrete" in note for note in critique.notes)
    assert any("comment" in note for note in critique.notes)


def test_critic_accepts_bare_number_as_concrete_fact():
    store = InMemoryStateStore()
    draft = Draft(
        text=(
            "Approval pipelines are easier to reason about with 3 recoverable steps.\n\n"
            "- Draft, approval, and publish each resume from stored state.\n\n"
            "What would you measure first? Comment with the metric you would trust."
        ),
        topic_fingerprint="abc",
    )

    critique = CriticAgent(store).evaluate(draft)

    assert critique.passed


def test_critic_rejects_recent_duplicate():
    store = InMemoryStateStore()
    draft = Draft(
        text=(
            "A 2 step approval path reduces hidden failures.\n\n"
            "- State is recorded before approval links are sent.\n\n"
            "What would you measure first? Comment with the metric you would trust."
        ),
        topic_fingerprint="repeat",
    )
    store.record_pending_approval(draft)

    critique = CriticAgent(store).evaluate(draft)

    assert not critique.passed
    assert any("fingerprint" in note for note in critique.notes)
