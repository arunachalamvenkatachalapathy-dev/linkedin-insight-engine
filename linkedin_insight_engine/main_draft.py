from __future__ import annotations

from .approval_agent import ApprovalAgent
from .config import settings
from .creator_agent import CreatorAgent
from .critic_agent import CriticAgent
from .linkedin_engine import LinkedInEngine
from .logger import configure_logging, log_event
from .models import PostStatus
from .state_store import get_state_store
from .manager import fetch_context


def run() -> int:
    """Full automated pipeline: fetch → draft → approve → publish."""
    configure_logging()

    print("\n🌿 LinkedIn Environment & Nature Post Pipeline")
    print("=" * 50)

    store = get_state_store()
    critic = CriticAgent(store)
    creator = CreatorAgent()
    approval_agent = ApprovalAgent()
    linkedin = LinkedInEngine()

    # Fetch environment/nature news
    log_event("pipeline", "start")
    contexts = fetch_context(store=store)
    
    import random
    contexts_list = list(contexts)
    random.shuffle(contexts_list)
    contexts = tuple(contexts_list)
    
    log_event("pipeline", "contexts-fetched", count=len(contexts))

    # Get recent keywords for dedup
    recent_keywords = store.get_recent_keywords(settings.duplicate_window_days)
    log_event("pipeline", "recent-posts-loaded", count=len(recent_keywords))

    notes: tuple[str, ...] = ()

    for attempt in range(1, settings.max_critic_attempts + 1):
        print(f"\n📝 Draft attempt {attempt}/{settings.max_critic_attempts}...")

        # Create draft with image
        draft = creator.create(contexts, notes, avoid_ideas=recent_keywords)

        # Critic check (structure, buzzwords, dedup, topic relevance)
        critique = critic.evaluate(draft)
        log_event("critic", "pass" if critique.passed else "fail", attempt=attempt, notes=critique.notes)

        if not critique.passed:
            print(f"   ❌ Critic rejected: {', '.join(critique.notes)}")
            notes = critique.notes
            continue

        print("   ✅ Critic passed!")

        # AI Approval Agent evaluation
        print("\n🔍 Running AI Approval Agent...")
        report = approval_agent.evaluate(draft)
        approval_agent.print_report(report)

        if not report.overall_passed:
            print("   ❌ Approval Agent rejected — revising...")
            # Extract failed check names as revision notes
            failed_notes = tuple(
                f"Fix: {check.name} — {check.reasoning}"
                for check in report.checks
                if not check.passed
            )
            notes = failed_notes
            continue

        # Record and publish
        approval = store.record_pending_approval(draft)
        store.record_decision(approval.token, PostStatus.APPROVED)

        print("\n📤 Publishing to LinkedIn...")
        response_status = linkedin.publish(draft)
        store.record_publish(approval.id, response_status)

        if 200 <= response_status < 300:
            print(f"   ✅ Published successfully! (HTTP {response_status})")
            log_event("pipeline", "published", approval_id=approval.id, response_status=response_status)
        else:
            print(f"   ⚠️  Publish returned HTTP {response_status}")
            log_event("pipeline", "publish-status", approval_id=approval.id, response_status=response_status)

        return 0

    print("\n❌ All draft attempts exhausted. No post published today.")
    log_event("pipeline", "exhausted", notes=notes)
    return 2


if __name__ == "__main__":
    raise SystemExit(run())
