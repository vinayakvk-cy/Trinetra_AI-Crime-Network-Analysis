"""
TRINETRA Application Configuration
===================================

Central configuration for the backend.

Configuration is loaded from environment variables
and the project's .env file.

Do not place passwords, API keys, or credentials directly
in source code.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import (
    BaseSettings,
    SettingsConfigDict,
)


class Settings(BaseSettings):
    """
    Application settings.

    Values can be supplied through environment variables
    or a .env file.
    """

    # ========================================================
    # APPLICATION
    # ========================================================

    app_name: str = Field(
        default="TRINETRA Intelligence Platform",
        description="Application name",
    )

    app_version: str = Field(
        default="2.0.0",
        description="Backend version",
    )

    environment: str = Field(
        default="development",
        description="development / testing / production",
    )

    debug: bool = Field(
        default=True,
        description="Enable debug mode",
    )

    # ========================================================
    # API
    # ========================================================

    api_prefix: str = Field(
        default="/api/v1",
        description="API route prefix",
    )

    host: str = Field(
        default="127.0.0.1",
        description="Server host",
    )

    port: int = Field(
        default=8000,
        description="Server port",
    )

    # ========================================================
    # CORS
    # ========================================================

    cors_origins: str = Field(
        default="http://localhost:3000,http://localhost:5173",
        description="Allowed frontend origins",
    )

    # ========================================================
    # DATABASE
    # ========================================================

    database_url: str = Field(
        default="sqlite:///./trinetra.db",
        description="Primary application database",
    )

    # ========================================================
    # NEO4J
    # ========================================================

    neo4j_uri: str = Field(
        default="bolt://localhost:7687",
        description="Neo4j connection URI",
    )

    neo4j_username: str = Field(
        default="neo4j",
        description="Neo4j username",
    )

    neo4j_password: str = Field(
        default="",
        description="Neo4j password",
    )

    neo4j_database: str = Field(
        default="neo4j",
        description="Neo4j database name",
    )

    # ========================================================
    # LOCAL AI
    # ========================================================

    local_ai_enabled: bool = Field(
        default=True,
        description="Enable local AI assistant",
    )

    local_ai_model: str = Field(
        default="local-model",
        description="Local AI model identifier",
    )

    local_ai_base_url: str = Field(
        default="http://localhost:11434",
        description="Local AI service URL",
    )

    # ========================================================
    # DATA DIRECTORIES
    # ========================================================

    data_dir: str = Field(
        default="./data",
        description="Root data directory",
    )

    input_data_dir: str = Field(
        default="./data/input",
        description="Input data directory",
    )

    processed_data_dir: str = Field(
        default="./data/processed",
        description="Processed data directory",
    )

    investigation_data_dir: str = Field(
        default="./data/investigations",
        description="Investigation memory directory",
    )

    # ========================================================
    # FILE UPLOAD
    # ========================================================

    max_upload_size_mb: int = Field(
        default=50,
        description="Maximum upload size in MB",
    )

    # ========================================================
    # LOGGING
    # ========================================================

    log_level: str = Field(
        default="INFO",
        description="Application log level",
    )

    # ========================================================
    # SECURITY
    # ========================================================

    secret_key: str = Field(
        default="CHANGE_THIS_IN_PRODUCTION",
        description="Application secret key",
    )

    access_token_expire_minutes: int = Field(
        default=60,
        description="Access token lifetime",
    )

    # ========================================================
    # PYDANTIC SETTINGS
    # ========================================================

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ========================================================
    # CORS HELPER
    # ========================================================

    @property
    def cors_origin_list(
        self,
    ) -> list[str]:
        """
        Convert comma-separated CORS origins into a list.
        """

        return [
            origin.strip()
            for origin in self.cors_origins.split(",")
            if origin.strip()
        ]


# ============================================================
# SETTINGS SINGLETON
# ============================================================

@lru_cache
def get_settings() -> Settings:
    """
    Return a cached application settings instance.

    Using a cached instance prevents repeatedly reading
    environment configuration.
    """

    return Settings()


settings = get_settings()