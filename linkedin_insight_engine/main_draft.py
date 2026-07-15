from __future__ import annotations

import random
from .approval_agent import ApprovalAgent
from .config import settings
from .creator_agent import CreatorAgent
from .critic_agent import CriticAgent
from .prompt_engineer_agent import PromptEngineerAgent
from .image_agent import generate_image
from .linkedin_engine import LinkedInEngine
from .logger import configure_logging, log_event
from .models import PostStatus, Draft
from .state_store import get_state_store
from .manager import fetch_context


def run() -> int:
    """Full automated pipeline: fetch → draft → prompt → image → audit → publish."""
    configure_logging()

    print("\n🌿 LinkedIn Environment & Nature Post Pipeline (v5 — Multi-Agent)")
    print("=" * 60)

    store = get_state_store()
    critic = CriticAgent(store)
    creator = CreatorAgent()
    prompt_engineer = PromptEngineerAgent()
    approval_agent = ApprovalAgent()
    linkedin = LinkedInEngine()

    # Fetch environment/nature news
    log_event("pipeline", "start")
    contexts = fetch_context(store=store)
    
    contexts_list = list(contexts)
    random.shuffle(contexts_list)
    contexts = tuple(contexts_list)
    
    log_event("pipeline", "contexts-fetched", count=len(contexts))

    # Get recent keywords for dedup
    recent_keywords = store.get_recent_keywords(settings.duplicate_window_days)
    log_event("pipeline", "recent-posts-loaded", count=len(recent_keywords))

    draft = None
    image_prompt = ""
    image_type = "photo-preferred"
    image_path = ""
    notes: tuple[str, ...] = ()
    image_notes: tuple[str, ...] = ()
    last_fail_type = "text"

    for attempt in range(1, settings.max_critic_attempts + 1):
        print(f"\n📝 Draft/Prompt Attempt {attempt}/{settings.max_critic_attempts}...")

        # 1. Text Generation stage
        if draft is None or last_fail_type == "text":
            print("   👉 Running Creator Agent (Text Drafting)...")
            draft = creator.create(contexts, notes, avoid_ideas=recent_keywords)
            image_notes = () # Reset image notes on new text draft

        # 2. Prompt Engineering stage
        print("   👉 Running Prompt Engineer Agent...")
        # Incorporate image critique notes into prompt engineering if relevant
        eng_prompt_input = f"{draft.text}\n\nRevision notes: " + "; ".join(image_notes) if image_notes else draft.text
        image_prompt, image_type = prompt_engineer.engineer_prompt(eng_prompt_input, draft.entities)

        # 3. Image Generation stage
        print(f"   👉 Running Image Agent ({image_type})...")
        image_path = generate_image(image_prompt, image_type, api_key=settings.gemini_api_key)

        # Re-assemble draft with prompt and path details
        assembled_draft = Draft(
            text=draft.text,
            topic_fingerprint=draft.topic_fingerprint,
            sources=draft.sources,
            image_path=image_path,
            keywords=draft.keywords,
            idea_summary=draft.idea_summary,
            entities=draft.entities,
            image_prompt=image_prompt,
            image_type=image_type,
        )

        # 4. Audit / Critic Stage
        critique = critic.evaluate(assembled_draft)
        log_event("critic", "pass" if critique.passed else "fail", attempt=attempt, notes=critique.notes, fail_type=critique.fail_type)

        if not critique.passed:
            print(f"   ❌ Critic rejected: {', '.join(critique.notes)}")
            last_fail_type = critique.fail_type
            if last_fail_type == "image":
                image_notes = critique.notes
                notes = ()
            else:
                notes = critique.notes
                image_notes = ()
            continue

        print("   ✅ Critic passed!")

        # 5. AI Approval Agent evaluation (Pass 2 / Final Check)
        print("\n🔍 Running AI Approval Agent...")
        report = approval_agent.evaluate(assembled_draft)
        approval_agent.print_report(report)

        if not report.overall_passed:
            print("   ❌ Approval Agent rejected — revising...")
            failed_notes = tuple(
                f"Fix: {check.name} — {check.reasoning}"
                for check in report.checks
                if not check.passed
            )
            notes = failed_notes
            last_fail_type = "text"
            continue

        # Record and publish
        approval = store.record_pending_approval(assembled_draft)
        store.record_decision(approval.token, PostStatus.APPROVED)

        # Dry run check
        dry_run = settings.linkedin_access_token == "" or settings.linkedin_person_urn == "" or (os.getenv("ECOPULSE_DRY_RUN", "false").lower() == "true")
        if dry_run:
            print("\n⚠️ DRY RUN — Simulation only.")
            print(f"Post Commentary:\n{assembled_draft.text}\n")
            print(f"Image Type: {image_type}")
            print(f"Image Prompt: {image_prompt}")
            print(f"Image Asset Path: {image_path}")
            return 0

        print("\n📤 Publishing to LinkedIn...")
        response_status = linkedin.publish(assembled_draft)
        store.record_publish(approval.id, response_status)

        if 200 <= response_status < 300:
            print(f"   ✅ Published successfully! (HTTP {response_status})")
            log_event("pipeline", "published", approval_id=approval.id, response_status=response_status)
        else:
            print(f"   ⚠️  Publish returned HTTP {response_status}")
            log_event("pipeline", "publish-status", approval_id=approval.id, response_status=response_status)

        return 0

    print("\n❌ All draft attempts exhausted. No post published today.")
    log_event("pipeline", "exhausted", notes=notes, image_notes=image_notes)
    return 2


if __name__ == "__main__":
    raise SystemExit(run())
