# EcoPulse

Autonomous 6-agent pipeline that researches environmental-engineering news, writes a
LinkedIn post, generates an accompanying image, and publishes it — on a GitHub Actions
schedule.

## Pipeline

```
Scout (research, web search)
  → Curator (recency/relevance filter, dedup against history)
    → Lateral Thinker (non-obvious engineering insight)
      → Copywriter (dynamic format + tone + length, grounded in supplied facts)
        → Fact Checker (grounding gate — blocks unsupported claims)
          → Visualizer (image prompt + render)
            → Publisher (LinkedIn Posts API)
```

## Dynamic post generation

There is no single fixed post template. Each run, the orchestrator randomly assigns:

- **A structural format** from `config/post_formats.json` (contrarian hook, data-led, mini
  case study, myth vs. reality, question-led, before/after, field note, numbered takeaways,
  trend forecast, cost trade-off) — 10 genuinely different structures, not just reworded
  hook/body/CTA variants.
- **A tone** from `config/tones.json` (analytical, blunt, curious, skeptical, matter-of-fact,
  cautiously optimistic).
- **A length band** (short/medium/long).

The orchestrator avoids repeating the same format or tone used in the last 3 posts (tracked
in `state/posted_log.json`), so consecutive posts don't fall into a visible pattern.

**Unpredictable ≠ unreliable.** Every post still has to pass the Fact Checker subagent, which
compares every specific claim in the finished post against the Curator's source facts and
blocks publishing if anything is unsupported. Variety is in structure, tone, and framing —
never in the facts.

## Setup

### 1. Repo secrets

Go to **Settings → Secrets and variables → Actions** and add:

| Secret | Description |
|---|---|
| `ANTHROPIC_API_KEY` | From console.anthropic.com |
| `LINKEDIN_ACCESS_TOKEN` | OAuth2 token with `w_member_social` scope, from your LinkedIn Developer App |
| `LINKEDIN_PERSON_URN` | Your member URN, format `urn:li:person:XXXXXXXX` |
| `OPENAI_API_KEY` **or** `STABILITY_API_KEY` | For image generation (pick one) |

### 2. LinkedIn token refresh — the one manual piece

LinkedIn OAuth2 access tokens expire (commonly 60 days). GitHub Actions can't complete an
interactive OAuth consent screen on its own, so token refresh needs a plan:

- **Simplest:** re-run your OAuth flow locally every ~60 days and update the
  `LINKEDIN_ACCESS_TOKEN` secret manually (2-minute task, put a calendar reminder).
- **More automated:** if your LinkedIn app has a stored refresh token, add a small script
  that exchanges it for a new access token and updates the secret via the GitHub API
  (`gh secret set`) — happy to build this out if you want it fully hands-off.

### 3. Test in dry-run first

Before letting it post live, trigger it manually with dry-run on:

**Actions tab → EcoPulse Autonomous LinkedIn Poster → Run workflow → dry_run: true**

This runs the full pipeline and prints the final post text + saves the image as a
workflow artifact-equivalent (check `state/latest_image.png` in the run, or add an
`actions/upload-artifact` step if you want to download it from the UI), without hitting
the LinkedIn API. Do this for ~2 weeks of runs before trusting full autonomy.

### 4. Adjust the schedule

Edit the `cron` line in `.github/workflows/ecopulse.yml`. Current default: Mon/Wed/Fri at
08:30 IST. Cron is in UTC — GitHub Actions schedules can also be delayed a few minutes
during high load, that's normal.

### 5. Tune the niche

Edit `config/niche_topics.json` to add/remove topics. `state/posted_log.json` is your
dedup memory — the Curator agent reads it to avoid repeating recent angles.

## Local testing

```bash
pip install -r requirements.txt
export ANTHROPIC_API_KEY=...
export OPENAI_API_KEY=...
export ECOPULSE_DRY_RUN=true
python scripts/orchestrator.py
```

## Notes on the LinkedIn API implementation

`scripts/agents/publisher.py` uses LinkedIn's versioned Posts API and Images API. LinkedIn
occasionally changes endpoint/header details — if publishing starts failing with a 4xx,
check the response body logged in the workflow output first (it's captured in
`publish_result["output"]["response_body"]`), and cross-check against LinkedIn's current
API docs before assuming the agent logic is at fault.
