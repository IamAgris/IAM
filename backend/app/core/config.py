"""Application configuration using pydantic-settings"""

from pathlib import Path

from pydantic_settings import BaseSettings
from pydantic import Field
from typing import List, Optional


class Settings(BaseSettings):
    # Application
    app_name: str = "project-aura"
    app_env: str = "development"
    app_debug: bool = True
    app_secret_key: str = Field(default="change-me-to-a-secure-random-secret")
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    frontend_url: str = "http://localhost:3000"

    # Database
    postgres_user: str = "aura"
    postgres_password: str = "change-me-securely"
    postgres_db: str = "aura_db"
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    database_url: Optional[str] = None

    # Redis
    redis_url: str = "redis://localhost:6379/0"
    redis_host: str = "localhost"
    redis_port: int = 6379

    # LiteLLM
    litellm_host: str = "0.0.0.0"
    litellm_port: int = 4000
    litellm_master_key: str = "change-me-securely"
    litellm_base_url: str = "http://localhost:4000"

    # IAM SDK protocol (OD-29) and node contribution (OD-26)
    iam_protocol_version: str = "1"
    iam_sdk_default_model: str = "nvidia-llama-3.3-70b"

    # Provider API keys
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    google_api_key: Optional[str] = None
    dashscope_api_key: Optional[str] = None
    # NVIDIA NIM / build.nvidia.com
    nvidia_api_key: Optional[str] = None
    nvidia_base_url: str = "https://integrate.api.nvidia.com/v1"
    nvidia_free_only: bool = True  # Never incur charges unless explicitly disabled

    # OEDIE free infrastructure provider adapters (Doc 22) — default-disabled.
    # Values are environment-variable NAMES, never literal secrets.
    free_sandboxes_enabled: bool = False
    free_sandbox_quota_safety_margin: float = 0.20  # refuse new work at 80% use
    free_sandbox_github_owner: str = "IamAgris"
    free_sandbox_github_repo: str = "IAM"
    github_codespaces_token_env: str = "GITHUB_CODESPACES_TOKEN"
    kaggle_token_env: str = "KAGGLE_API_TOKEN"
    huggingface_token_env: str = "HF_TOKEN"
    colab_token_env: str = "COLAB_API_TOKEN"

    brave_api_key: Optional[str] = None
    google_cx: Optional[str] = None

    # Object Storage (S3-compatible)
    s3_endpoint: str = "http://localhost:9000"
    s3_access_key: str = "change-me"
    s3_secret_key: str = "change-me"
    s3_bucket: str = "aura-storage"
    s3_region: str = "us-east-1"

    # Security
    encryption_key: str = "change-me-to-a-32-byte-base64-key"
    session_secret: str = "change-me-session-secret"

    # Skill Runtime — execution of approved Skill Forge packages
    skill_runtime_enabled: bool = False
    skill_runtime_adapter: str = "stub"  # stub | docker
    skill_runtime_image: str = "python:3.12-alpine"
    skill_runtime_timeout_seconds: int = 30
    skill_runtime_memory: str = "256m"
    skill_runtime_cpus: float = 0.5

    # API authentication and rate limiting
    auth_enabled: bool = True
    auth_bootstrap_key_env: str = "IAM_BOOTSTRAP_API_KEY"
    auth_rate_limit_per_minute: int = 120

    # Creator approval by email (OD-18/OD-19) — no Creator UI
    # Email is the carrier; authority comes from a signed challenge.
    creator_email: Optional[str] = None
    creator_email_domain: Optional[str] = None
    creator_public_key: Optional[str] = None  # Ed25519 PEM or base64 raw public key
    creator_signer_id: str = "creator-hardware-signer"
    creator_challenge_ttl_seconds: int = 3600
    creator_authorization_ttl_seconds: int = 3600

    # Delivery of Creator approval requests (OD-18). 'log' is the safe default:
    # the email package is recorded in the outbox but nothing leaves the host.
    creator_email_transport: str = "log"  # log | smtp | http
    creator_email_from: str = ""
    creator_smtp_host: str = ""
    creator_smtp_port: int = 587
    creator_smtp_user: str = ""
    creator_smtp_password_env: str = "CREATOR_SMTP_PASSWORD"
    creator_smtp_use_tls: bool = True
    creator_email_http_url: str = ""
    creator_email_http_token_env: str = "CREATOR_EMAIL_HTTP_TOKEN"

    # HMAC secret for the inbound signer/email gateway. Empty = gateway disabled.
    creator_gateway_secret: str = ""

    # External Security Engines — ARTEX connector (default-disabled, defensive-only)
    artex_enabled: bool = False
    artex_dry_run: bool = True
    artex_base_url: str = "http://127.0.0.1:8787"
    artex_mcp_path: str = "/mcp"
    artex_token_env: str = "ARTEX_MCP_TOKEN"
    # Comma-separated IP/CIDR allowlist checked before the token at ARTEX's /mcp
    artex_source_allowlist: str = "127.0.0.1/32,::1/128"

    # IAM Skill Forge — native skill creation subsystem
    # Default: <repo-root>/iam/skills (config.py -> app/core -> app -> backend -> repo-root)
    skillforge_root: str = str(Path(__file__).resolve().parents[3] / "iam" / "skills")
    skillforge_max_file_bytes: int = 262144  # skip oversized files during inspection

    # Monitoring
    otel_exporter_otlp_endpoint: Optional[str] = None

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"


settings = Settings()
