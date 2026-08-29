# from pydantic_settings import BaseSettings
# from functools import lru_cache
# from typing import Optional


# class Settings(BaseSettings):
#     supabase_url: str
#     supabase_key: str
#     supabase_service_key: str
#     encryption_key: str
#     anthropic_api_key: Optional[str] = None
#     resend_api_key: Optional[str] = None
#     from_email: str = "onboarding@resend.dev"
#     google_vision_api_key: Optional[str] = None
#     sentry_dsn: Optional[str] = None
#     app_name: str = "GST Audit AI"
#     app_version: str = "1.0.0"
#     debug: bool = False
#     cors_origins: str = "http://localhost:3000,http://localhost:3001"

#     @property
#     def allowed_origins(self) -> list[str]:
#         return [o.strip() for o in self.cors_origins.split(",")]

#     class Config:
#         env_file = ".env"
#         case_sensitive = False
#         extra = "ignore"


# @lru_cache()
# def get_settings() -> Settings:
#     return Settings()

from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Optional


class Settings(BaseSettings):
    supabase_url: str
    supabase_key: str
    supabase_service_key: str
    encryption_key: str
    anthropic_api_key: Optional[str] = None
    resend_api_key: Optional[str] = None
    from_email: str = "onboarding@resend.dev"
    google_vision_api_key: Optional[str] = None
    sentry_dsn: Optional[str] = None
    app_name: str = "GST Audit AI"
    app_version: str = "1.0.0"
    debug: bool = False
    cors_origins: str = "http://localhost:3000,http://localhost:3001"

    # ── Rule Engine feature flags ──────────────────────────────
    use_db_rules: bool = False
    # False = hardcoded ISSUE_WEIGHTS used (safe default)
    # True  = DB-driven rules, hardcoded as fallback only

    admin_api_enabled: bool = True
    # False = disable /admin/* routes in production

    admin_api_key: Optional[str] = None
    # Set ADMIN_API_KEY in .env to secure admin endpoints

    @property
    def allowed_origins(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",")]

    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    return Settings()