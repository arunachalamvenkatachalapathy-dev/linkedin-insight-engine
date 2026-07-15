from __future__ import annotations

from dataclasses import dataclass, field
import os

from dotenv import load_dotenv

load_dotenv()


DEFAULT_RSS_SOURCES = (
    "https://climate.nasa.gov/news/rss",
    "https://e360.yale.edu/feed",
    "https://www.carbonbrief.org/feed",
    "https://www.theguardian.com/environment/rss",
)

POLITICAL_KEYWORDS = (
    "modi", "naidu", "lokesh", "gandhi", "bjp", "congress", "election",
    "political", "parliament", "minister", "government praise", "amit shah",
    "mamata", "kejriwal", "narendra", "appraisal", "mla", "mp", "vote"
)

BUZZWORDS = (
    "game-changing",
    "revolutionary",
    "disruptive",
    "cutting-edge",
    "unlock",
    "seamless",
    "paradigm shift",
    "synergy",
    "leverage",
    "holistic",
)

CTA_OPTIONS = (
    "What's one change you've made to reduce your environmental footprint? Share below.",
    "Which of these solutions do you think has the most potential? Drop your thoughts in the comments.",
    "Have you seen this kind of impact in your community? I'd love to hear your story.",
    "What's the biggest environmental challenge your industry faces? Comment your perspective.",
    "If you could fund one conservation project, what would it be? Share your pick below.",
)

ENVIRONMENT_TOPICS = (
    "climate change", "global warming", "sustainability", "renewable energy",
    "biodiversity", "conservation", "deforestation", "reforestation",
    "ocean health", "marine ecosystem", "wildlife", "pollution",
    "carbon emissions", "greenhouse gas", "clean energy", "solar power",
    "wind energy", "circular economy", "waste reduction", "recycling",
    "endangered species", "ecosystem", "coral reef", "ice cap",
    "drought", "flooding", "wildfire", "air quality", "water scarcity",
)

DEFAULT_NICHE_TOPICS = (
    "Miyawaki urban forestry",
    "Bamboo building material",
    "Solar powered irrigation",
    "Rainwater harvesting",
    "Bioplastics from seaweed",
    "Drip irrigation systems",
    "Mangrove restoration",
    "Solid waste management",
    "Agroforestry farming",
    "Electric vehicle charging grid",
    "Green hydrogen fuel",
    "Composting municipal waste",
    "Geothermal energy potential",
    "Vertical garden structures",
    "Rooftop solar schemes",
    "Zero budget natural farming",
    "E-waste recycling tech",
    "Single use plastic ban",
    "Eco tourism conservation",
    "Greywater recycling systems",
    "Tiger corridor protection",
    "Sacred groves preservation",
    "Khadi sustainable textiles",
    "Organic farming yield",
)

STYLE_PROFILE = """\
- Tone: Extremely human, storytelling, authentic, slightly vulnerable. Never lecturing, academic, or corporate.
- Perspective: First person ("I" or "We"). Grounded in personal observation, memory, or reflection.
- Hook: A captivating first line that opens a loop or shares an emotional reaction. No platitudes.
- Format: Plain text narrative paragraphs separated by double line breaks. Strictly NO bullet points or numbered lists.
- Hashtags: Exactly 3-5 at the bottom.
"""


@dataclass(frozen=True)
class Settings:
    char_limit: int = 3000
    char_limit_min: int = 900
    max_critic_attempts: int = 3
    duplicate_window_days: int = 90
    rss_sources: tuple[str, ...] = DEFAULT_RSS_SOURCES
    approval_base_url: str = field(default_factory=lambda: os.getenv("APPROVAL_BASE_URL", "http://localhost:8080"))
    email_to: str = field(default_factory=lambda: os.getenv("EMAIL_TO", ""))
    linkedin_person_urn: str = field(default_factory=lambda: os.getenv("LINKEDIN_PERSON_URN", ""))
    linkedin_access_token: str = field(default_factory=lambda: os.getenv("LINKEDIN_ACCESS_TOKEN", ""))
    firestore_project: str = field(default_factory=lambda: os.getenv("GOOGLE_CLOUD_PROJECT", ""))
    gemini_api_key: str = field(default_factory=lambda: os.getenv("GEMINI_API_KEY", ""))
    openai_api_key: str = field(default_factory=lambda: os.getenv("OPENAI_API_KEY", ""))
    style_profile: str = STYLE_PROFILE


settings = Settings()
