import os


class Config:
    SUPABASE_URL: str = os.environ.get("SUPABASE_URL", "")
    SUPABASE_KEY: str = os.environ.get("SUPABASE_KEY", "")
    GEMINI_API_KEY: str = os.environ.get("GEMINI_API_KEY", "")

    TARGET_URL: str = "https://www.asc.tcu.ac.jp/6509/"
    SYLLABUS_BASE_URL: str = "https://websrv.tcu.ac.jp/tcu_web_v3"

    SCRAPE_DELAY_SEC: float = 3.0
    GEMINI_MODEL: str = "gemini-3.1-flash-lite-preview"
    GEMINI_FALLBACK_MODEL: str = "gemini-3-flash-preview"

    @classmethod
    def validate(cls) -> None:
        missing = [
            name
            for name in ("SUPABASE_URL", "SUPABASE_KEY", "GEMINI_API_KEY")
            if not getattr(cls, name)
        ]
        if missing:
            raise EnvironmentError(
                f"Missing required environment variables: {', '.join(missing)}"
            )
