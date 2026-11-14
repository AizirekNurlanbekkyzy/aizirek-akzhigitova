from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str
    jwt_secret: str = Field(min_length=32)
    app_env: str
    cors_origins: str = "http://localhost:3000"
    jwt_exp_minutes: int = 60
    model_config = SettingsConfigDict(extra="ignore")

    @field_validator("app_env")
    @classmethod
    def normalize_environment(cls, value: str) -> str:
        normalized = value.lower().strip()
        if normalized not in {"development", "test", "production"}:
            raise ValueError("APP_ENV must be development, test, or production")
        return normalized

    @field_validator("jwt_secret")
    @classmethod
    def reject_placeholder_secrets(cls, value: str) -> str:
        if value.lower().startswith(("replace-with", "change-me", "your-secret", "generate_")):
            raise ValueError("JWT_SECRET must be replaced with a generated secret")
        if len(set(value)) < 12:
            raise ValueError("JWT_SECRET must contain sufficient randomness")
        return value

    @model_validator(mode="after")
    def secure_production_settings(self) -> "Settings":
        if self.app_env == "production" and self.jwt_secret in {
            "local-development-secret-change-before-production-000000000000",
            "test-secret-for-fixflow-tests-only-000000000000000000",
        }:
            raise ValueError("Demo/test JWT_SECRET cannot be used in production")
        return self


settings = Settings()
