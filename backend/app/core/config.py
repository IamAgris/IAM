"""Application configuration using pydantic-settings"""

import os
from pathlib import Path

from pydantic_settings import BaseSettings
from pydantic import Field, model_validator
from typing import List, Optional

# Fields that may be supplied through Docker secret files (<FIELD>_FILE).
SECRET_FIELDS = (
    "app_secret_key",
    "session_secret",
    "encryption_key",
    "postgres_password",
    "litellm_master_key",
    "openai_api_key",
    "anthropic_api_key",
    "google_api_key",
    "dashscope_api_key",
    "nvidia_api_key",
    "brave_api_key",
    "s3_access_key",
    "s3_secret_key",
    "creator_public_key",
    "creator_gateway_secret",
    # Proposed Doc 35 / OD-55 — credentials are Docker secrets, never values in config.
    "thirdweb_secret_key",
    "bitcoin_rpc_cookie",
    "lnd_macaroon",
    "cln_rune",
    "lnd_tls_cert",
    "cln_ca_cert",
    # Separate write-scoped credentials for approval-gated execution.
    "lnd_write_macaroon",
    "cln_write_rune",
)


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
    # Development may create tables from ORM metadata. Production must use
    # Alembic migrations; None resolves to "enabled only outside production".
    db_create_all_on_startup: Optional[bool] = None

    @property
    def create_all_enabled(self) -> bool:
        """Whether startup may create tables from SQLAlchemy metadata."""
        if self.db_create_all_on_startup is not None:
            return self.db_create_all_on_startup
        return self.app_env != "production"

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
    # Optional hardware-backed attestation. Disabled unless a TPM is present
    # and the operator explicitly enables it.
    tpm_measurement_enabled: bool = False
    # Official assistant integration endpoints — never credentials. Opt-in only.
    alexa_skill_endpoint: Optional[str] = None
    siri_intents_endpoint: Optional[str] = None
    bixby_automation_endpoint: Optional[str] = None
    iam_protocol_require_header: bool = False
    # Stable P2P identity. Without an explicit secret the transport generates a
    # random one per process, so peers cannot reconnect after a restart.
    iam_node_id: str = "local-iam"
    iam_p2p_secret: Optional[str] = None
    # Gateway routing alias, not IAM's identity or a permanent model (OD-38).
    # Foundation-model policy: IAM_FOUNDATION_MODEL_AND_INTELLIGENCE_SPEC.md.
    iam_sdk_default_model: str = "nvidia-nemotron-3.5-lightning"
    # Free hosted specialist for background internal reasoning. OD-46 keeps the
    # local primary as IAM's brain; this sub-agent uses the separate hosted
    # pool so it cannot occupy the single OD-39 local residency slot that user
    # chat needs. Never point this at a paid alias without owner approval.
    autonomy_model: str = "nvidia-nemotron-3.5-lightning"
    # Self/independent evaluation deliberately uses the local primary as the
    # judge. Run it on a slower cadence so it cannot occupy the single OD-39
    # residency slot for every 30s autonomy tick and starve user chat.
    autonomy_evaluation_interval_s: int = 900

    # One shared primary model for the whole IAM experience (frontend and
    # backend). Hosted providers remain optional specialists reached only by
    # explicit model id; see IAM_FOUNDATION_MODEL_AND_INTELLIGENCE_SPEC.md.
    # Owner-directed reopening of OD-46 (27 Nov 2026): Qwen2.5-3B is IAM's
    # shared primary local brain. Qwen2.5-Coder 3B remains an optional secondary.
    iam_primary_model: str = "local-qwen-3b"
    iam_primary_local_tag: str = "qwen2.5:3b"  # Ollama tag behind the alias

    # A cache-cold local 3B on the 4 vCPU core can take minutes to load and
    # produce first tokens. Keep these generous; the route still reports a
    # real timeout explicitly (504) instead of hanging or inventing an answer.
    inference_chat_timeout_seconds: float = 300.0
    inference_stream_timeout_seconds: float = 300.0
    # Aegis input inspection runs on every inference request; disable only for
    # explicitly trusted operator diagnostics, never for public traffic.
    inference_aegis_enabled: bool = True
    # OD-06 disaster recovery: real pg_dump backups and isolated restore drills.
    backup_directory: str = "/tmp/iam-backups"
    backup_retention_count: int = 7
    backup_rpo_hours: int = 24
    backup_rto_hours: int = 4
    backup_pg_dump_bin: str = "pg_dump"
    backup_pg_restore_bin: str = "pg_restore"
    backup_psql_bin: str = "psql"
    # When set (e.g. "postgres"), pg_dump/pg_restore/psql and hash/stat run via
    # `docker compose exec -T <service>` so a host without Postgres clients can
    # still execute a real backup and isolated restore drill.
    backup_container_service: str = ""
    backup_container_dsn: str = ""

    # IAM context assembly — injects verified knowledge (and, only when
    # explicitly requested and local, private memories) into chat requests.
    iam_context_enabled: bool = True
    iam_context_include_private_memory: bool = False
    iam_context_share_with_hosted: bool = False

    # Local-only semantic memory embeddings. No paid embedding provider is used;
    # when the local tag is absent, recall degrades to deterministic keyword search.
    memory_embedding_provider: str = "local"  # local | none
    memory_embedding_model: str = "nomic-embed-text"

    # Always-on live-information policy (proposed Doc 32). Automatic retrieval
    # uses free providers only; paid search stays fail-closed under OD-04/OD-25.
    # Model-initiated web search. Only user chat may execute tools; internal
    # workers stay tool-free so they cannot loop or spend search budget.
    iam_tool_search_enabled: bool = True
    iam_tool_search_max_rounds: int = 2
    iam_live_info_enabled: bool = True
    iam_live_info_max_results: int = 3
    iam_live_info_timeout_seconds: float = 20.0
    iam_live_info_use_browser: bool = False
    # Conditional escalation: ordinary chats never start a browser, but a
    # triggered live-information request that gets no suitable evidence (for
    # example the Wikipedia fallback) may escalate to browser retrieval.
    iam_live_info_escalate_to_browser: bool = True

    # Search provider management (proposed Doc 32 §6). Free-first by default;
    # paid providers require signed Creator authorisation before use.
    iam_search_provider_order: str = (
        "duckduckgo,google-news-rss,bing-news-rss,google-html,brave-html,"
        "searxng,wikipedia"
    )
    # Independent free providers are queried in parallel; all results and all
    # failures are retained for ranking and for reporting availability to IAM.
    iam_search_concurrent_providers: int = 3
    # Unhealthy providers are probed again after a cooldown so a transient
    # rate limit cannot permanently remove an engine from the chain.
    iam_search_provider_recovery_s: int = 300
    iam_search_searxng_url: str = ""
    iam_search_tavily_api_key: str = ""

    # API sub-agents are optional specialists, never IAM itself. Delegation is
    # per-request opt-in and requires a signed Creator authorization because
    # task text is sent to an external provider.
    iam_delegation_enabled: bool = True
    iam_delegation_action: str = "model.delegate"
    iam_delegation_max_findings: int = 5
    # OD-51 §4.4: bounded parallel delegation. These are the confirmed starting
    # values; changing them is a decision under change control, not a config tweak.
    iam_delegation_max_parallel: int = 3
    iam_delegation_timeout_seconds: float = 120.0
    iam_delegation_memory_limit_mb: int = 512
    iam_delegation_max_calls_per_request: int = 4

    # Provider API keys
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    google_api_key: Optional[str] = None
    dashscope_api_key: Optional[str] = None
    # NVIDIA NIM / build.nvidia.com
    nvidia_api_key: Optional[str] = None
    nvidia_base_url: str = "https://integrate.api.nvidia.com/v1"
    nvidia_free_only: bool = True  # Never incur charges unless explicitly disabled
    # OD-52 Phase B: metadata catalogue. Models.dev supplies specifications and
    # capabilities; it is not a source of endpoint availability.
    models_dev_api_url: str = "https://models.dev/api.json?type=all"
    models_dev_timeout_seconds: float = 20.0
    # OD-52 confirmed 27 Nov 2026: runtime registration and availability
    # monitoring are enabled for free models only. Paid endpoints stay blocked.
    model_catalog_registration_enabled: bool = True
    litellm_model_management_timeout_seconds: float = 15.0
    endpoint_availability_enabled: bool = True
    availability_probe_timeout_seconds: float = 10.0
    availability_probe_concurrency: int = 2
    # OD-52 Phase F: operational hardening for shared provider accounts.
    provider_retry_max_attempts: int = 3
    provider_retry_backoff_seconds: float = 1.0
    # OD-04: free endpoints only by default. Paid models are refused even with
    # a signed authorization until an operator explicitly disables this switch.
    free_models_only: bool = True

    # Ollama - local models (private / low-resource tasks). Opt-in so IAM never
    # silently starts using a local model the operator did not approve.
    ollama_enabled: bool = False
    ollama_base_url: str = "http://ollama:11434"

    # Adaptive model selection (OD-39 / OD-41) — hardware-aware local model choice.
    adaptive_model_enabled: bool = True
    # Owner-directed reopening of OD-46 (27 Nov 2026): all local tiers map to
    # the approved primary local model qwen2.5:3b.
    adaptive_tiny_model: str = "local-qwen-3b"
    adaptive_small_model: str = "local-qwen-3b"
    adaptive_standard_model: str = "local-qwen-3b"
    adaptive_large_model: str = "local-qwen-3b"
    # Hosted specialist used only as a helper to the local primary brain.
    # OD-51: still requires a signed Creator authorization per task; the local
    # model verifies and accepts findings. Verified free on the NVIDIA key in
    # .env (27 Nov 2026); the previous Dashscope default had no configured key.
    adaptive_delegate_model: str = "mistralai/mistral-large-4-1t-a52b"
    adaptive_delegate_node: Optional[str] = None
    adaptive_reserved_ram_mb: int = 1500  # protected core services (OD-39)
    adaptive_min_ram_mb_standard: int = 2500
    adaptive_min_ram_mb_large: int = 5500

    # IRWM runtime enforcement (OD-39). One resident model, one request.
    irwm_enabled: bool = True
    irwm_hard_ceiling_mb: int = 6000
    irwm_target_loaded_ram_mb: int = 5500
    irwm_keep_alive_seconds: int = 120
    irwm_in_flight_timeout_seconds: int = 120  # expire stuck leases after 2 min
    irwm_max_concurrent: int = 1
    irwm_context_tokens: int = 4096

    # OEDIE free infrastructure provider adapters (Doc 22) — default-disabled.
    # Values are environment-variable NAMES, never literal secrets.
    free_sandboxes_enabled: bool = False
    free_sandbox_quota_safety_margin: float = 0.20  # refuse new work at 80% use
    free_sandbox_discovery_enabled: bool = False
    free_sandbox_discovery_interval_ticks: int = 10
    free_sandbox_max_concurrent_per_provider: int = 1
    free_sandbox_retry_attempts: int = 2
    free_sandbox_circuit_breaker_threshold: int = 3
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

    # Media services (optional, provider-independent)
    voice_tts_url: str = ""
    voice_tts_api_key_env: str = "VOICE_TTS_API_KEY"
    voice_vad_sample_rate: int = 16000
    voice_vad_threshold: float = 0.02
    vision_ffmpeg_path: str = "ffmpeg"
    vision_model: str = "qwen3.5-9b"

    # UWAIE browser automation — one engine at a time, all sessions isolated.
    uwai_browser_engine: str = "chromium"  # chromium | firefox | webkit
    browser_enabled: bool = True
    browser_visible_mode_enabled: bool = False
    browser_isolated_mode_enabled: bool = True
    browser_max_concurrent_sessions: int = 3
    browser_session_ttl_seconds: int = 1800
    browser_profile_root: str = ""  # empty => temp dir
    browser_evidence_dir: str = ""  # empty => temp dir
    browser_task_worker_backend: str = "loop"  # loop | arq
    browser_ocr_enabled: bool = False  # opt-in: local Tesseract OCR on screenshots

    # TIPS (Doc 29 P5) — official Tor Browser only, fail closed without binary.
    tor_enabled: bool = False
    tor_browser_executable: str = ""  # path to official Tor Browser binary/launcher
    tor_control_host: str = "127.0.0.1"
    tor_control_port: int = 9051
    tor_socks_port: int = 9050
    tor_session_ttl_seconds: int = 900
    tor_max_concurrent_sessions: int = 1
    tor_data_root: str = ""  # empty => OS temp/iam-tor-profiles
    tor_onion_access_enabled: bool = False  # Creator-controlled; fail closed
    tor_bandwidth_limit_kbps: int = 0  # 0 => no explicit cap
    tor_bridge_configured: bool = False

    # IICS overlay: allowlisted threat-intel feeds (empty means no polling).
    iics_threat_feeds: str = "https://services.nvd.nist.gov/rest/json/cves/2.0?resultsPerPage=20"
    iics_threat_feed_interval_minutes: int = 360
    iics_site_policy_refresh_minutes: int = 720
    uwai_upload_root: str = ""  # empty => OS temp/iam-web-uploads
    uwai_computer_use_enabled: bool = False
    mobile_agent_enabled: bool = False
    mobile_adb_path: str = "adb"
    mobile_allowed_devices: str = ""  # comma-separated device serials

    # Skill Runtime — execution of approved Skill Forge packages
    skill_runtime_enabled: bool = False
    skill_runtime_adapter: str = "stub"  # stub | docker
    skill_runtime_image: str = "python:3.12-alpine"
    skill_runtime_timeout_seconds: int = 30
    skill_runtime_memory: str = "256m"
    skill_runtime_cpus: float = 0.5
    skill_runtime_per_skill_limit_per_minute: int = 60
    skill_runtime_max_log_chars: int = 200000
    skill_runtime_audit_log_chunk_chars: int = 32000
    # Network-enabled skills require explicit opt-in and a pre-created Docker
    # network with restricted egress. Names 'host', 'bridge' and 'none' are
    # rejected by the adapter (see skillruntime.adapters).
    skill_runtime_network_enabled: bool = False
    skill_runtime_network_name: str = ""

    # Workspace manager (WS-01/WS-02) — default-off, provider-independent.
    workspace_enabled: bool = False
    workspace_adapter: str = "stub"  # stub | docker
    workspace_root: str = ""  # empty => OS temp directory
    workspace_image: str = "python:3.12-alpine"
    workspace_timeout_seconds: int = 60
    workspace_memory: str = "512m"
    workspace_cpus: float = 1.0
    # Provider replacement / continuity (WS-05/WS-06). Online providers are
    # optional resources; 'local' is always the final fallback.
    workspace_providers: str = "local,coder,codespaces"
    workspace_coder_url: str = ""
    workspace_coder_token_env: str = "WORKSPACE_CODER_TOKEN"
    workspace_codespaces_repo: str = ""
    workspace_codespaces_token_env: str = "WORKSPACE_CODESPACES_TOKEN"
    # Per-workspace scoped credentials (WS-03) are short-lived and name-only.
    workspace_credential_ttl_seconds: int = 3600
    # Remote provider execution is opt-in. No external HTTP call is made until
    # this is enabled and the named token environment variable is present.
    workspace_remote_execution_enabled: bool = False
    workspace_remote_timeout_seconds: int = 30
    workspace_coder_template_id: str = ""
    workspace_coder_create_path: str = "/api/v2/users/me/workspaces"
    workspace_coder_start_path: str = "/api/v2/users/me/workspaces/{id}/start"
    workspace_coder_destroy_path: str = "/api/v2/users/me/workspaces/{id}"
    workspace_coder_execute_path: str = ""  # operator-provided command bridge
    workspace_codespaces_api_base: str = "https://api.github.com"
    workspace_codespaces_ref: str = "main"
    workspace_codespaces_create_path: str = "/repos/{repo}/codespaces"
    workspace_codespaces_start_path: str = "/repos/{repo}/codespaces/{id}/start"
    workspace_codespaces_destroy_path: str = "/repos/{repo}/codespaces/{id}"
    workspace_codespaces_execute_path: str = ""  # operator-provided command bridge

    # Model release evidence store (OD-40 self-improvement gates)
    model_release_artifact_root: str = ""
    # Operator-supplied candidate inputs for unattended foundation-model
    # development. All empty by default: IAM never invents a licence, a
    # checkpoint or a served alias, and preparation fails closed without them.
    model_development_candidate_model: str = ""
    model_development_checkpoint_ref: str = ""
    model_development_dataset_licence: str = ""

    # Local Ollama development path. Opt-in: it creates a servable candidate
    # through /api/create (prompt/template adaptation), not weight fine-tuning.
    model_development_local_training: bool = False
    model_development_ollama_candidate: str = ""
    # Owner-declared consent types permitted for training data. Empty fails closed.
    training_consent_types: list[str] = []

    # Independent evaluation evidence lives outside IAM's writable database.
    # The signing key is operator-held and must not be exposed to IAM tools.
    independent_eval_artifact_root: str = ""
    independent_eval_signing_key: str = ""
    # Durable research artifacts: "local" (temp/filesystem) or "s3" (MinIO/S3).
    # Bounded research workflow so a slow free provider cannot hold a request
    # open indefinitely; partial results plus a limitation event are returned.
    research_workflow_timeout_seconds: float = 20.0
    research_artifact_store: str = "local"
    research_artifact_prefix: str = "research"

    # Optional agent-side MCP bridge for real Colab platform drivers. Disabled by
    # default: no runtime is created and no external account is used implicitly.
    colab_mcp_enabled: bool = False
    colab_mcp_bridge_url: str = ""
    colab_mcp_bridge_token_env: str = "COLAB_MCP_BRIDGE_TOKEN"

    # Trusted local evaluator for benchmark evidence. Empty path fails closed.
    lm_eval_dataset_path: str = "app/services/ai_research/eval_sets/basic.jsonl"
    lm_eval_suite_enabled: bool = True
    lm_eval_timeout_seconds: float = 300.0

    # Post-deployment regression monitoring. Auto-rollback still needs a signed
    # authorization, so disabled by default.
    post_deploy_monitor_enabled: bool = False
    post_deploy_regression_threshold: float = 0.05
    post_deploy_auto_rollback_enabled: bool = False

    # OD-04 zero standing budget: configurable caps enforced at the spend path.
    # Per-transaction approvals are capped to the $1–$10 band; deployment config
    # chooses the value, nothing is hard-coded in the enforcement logic.
    finance_monthly_limit_usd: float = 100.0
    finance_transaction_limit_usd: float = 10.0

    # OD-23 free-only blockchain adapter (testnets only, no paid plans).
    blockchain_enabled: bool = False
    blockchain_provider: str = "thirdweb"
    blockchain_rpc_url: str = ""
    blockchain_chain_id: str = "11155111"  # Sepolia testnet
    blockchain_client_id_env: str = "THIRDWEB_CLIENT_ID"
    blockchain_secret_env: str = "THIRDWEB_SECRET_KEY"
    blockchain_allow_mainnet: bool = False

    # Proposed Doc 35 / OD-55 — Web3 and node adapters. All flags default-off.
    # These flags enable READ and PREPARE paths only; none enables execution.
    # Creator approval integration for execution is a separate later work item.
    web3_registry_enabled: bool = False
    web3_audit_enabled: bool = False
    web3_transaction_preparation_enabled: bool = False
    thirdweb_read_enabled: bool = False
    bitcoin_core_read_enabled: bool = False
    lnd_read_enabled: bool = False
    cln_read_enabled: bool = False
    thirdweb_base_url: str = ""       # free-tier RPC/API base, operator reviewed
    bitcoin_core_connector_url: str = ""  # in-Umbrel read-only connector
    bitcoin_core_cookie_env: str = "BITCOIN_RPC_COOKIE"
    lnd_rest_url: str = ""
    lnd_tls_cert_env: str = "LND_TLS_CERT"
    lnd_macaroon_env: str = "LND_MACAROON"
    cln_rest_url: str = ""
    cln_ca_cert_env: str = "CLN_CA_CERT"
    cln_rune_env: str = "CLN_RUNE"
    web3_request_timeout_seconds: float = 10.0
    # Approval-gated execution. Default-off; every call still requires a verified
    # signed Creator authorization. No signing key is ever held by IAM.
    web3_execution_enabled: bool = False
    web3_executor_url: str = ""  # protected signer / Engine endpoint, operator reviewed
    lnd_write_enabled: bool = False
    lnd_write_macaroon_env: str = "LND_WRITE_MACAROON"
    cln_write_enabled: bool = False
    cln_write_rune_env: str = "CLN_WRITE_RUNE"
    # Production gates. The owner-decision flag may be set only after OD-55 is
    # signed; a configuration value is not itself authority.
    web3_owner_decision_confirmed: bool = False
    web3_testnet_evidence_ref: str = ""
    web3_monitoring_enabled: bool = False
    web3_monitoring_stuck_minutes: int = 30
    # Extended Web3 capability modules (proposed Doc 35). Research/prepare only.
    web3_defi_enabled: bool = False
    web3_x402_enabled: bool = False
    web3_nft_enabled: bool = False
    web3_dao_enabled: bool = False
    web3_contract_dev_enabled: bool = False
    web3_cross_chain_enabled: bool = False
    web3_threat_intel_enabled: bool = False
    web3_onchain_analysis_enabled: bool = False

    # OD-24 South African banking adapters — credentials are env-var names only.
    banking_enabled: bool = False
    banking_adapter: str = "stub"  # stub | sa_bank
    banking_base_url: str = ""
    banking_token_env: str = "BANKING_TOKEN"
    banking_country: str = "ZA"

    # Doc 25 paper trading — simulation only, never real orders.
    trading_simulation_enabled: bool = False
    trading_max_order_usd: float = 10.0
    trading_daily_exposure_usd: float = 100.0
    trading_max_loss_usd: float = 20.0
    trading_stop_loss_pct: float = 10.0

    # Doc 25 Amendment A — research-only intelligence departments. These flags
    # enable research and record-keeping only; no execution, wagering or payment
    # path is exposed by them. Default-off like every other external adapter.
    prediction_markets_research_enabled: bool = False
    # Public market-data adapter — default-off, GET-only, no wallet or trading.
    # Base URLs are empty until an operator supplies and reviews them.
    prediction_markets_data_adapter_enabled: bool = False
    prediction_markets_gamma_url: str = ""
    prediction_markets_clob_url: str = ""
    prediction_markets_data_url: str = ""
    prediction_markets_request_timeout_seconds: float = 10.0
    prediction_markets_max_markets: int = 20
    prediction_markets_book_depth: int = 5
    prediction_markets_forecasting_enabled: bool = False
    gaming_intelligence_enabled: bool = False
    investment_intelligence_research_enabled: bool = False
    financial_provider_registry_enabled: bool = False

    # API authentication and rate limiting
    auth_enabled: bool = True
    auth_bootstrap_key_env: str = "IAM_BOOTSTRAP_API_KEY"
    auth_rate_limit_per_minute: int = 120
    rate_limit_backend: str = "memory"  # memory | redis

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
    creator_email_worker_enabled: bool = True
    creator_email_worker_backend: str = "loop"  # loop | arq (OD-08)
    creator_email_retry_interval_seconds: int = 300
    creator_email_max_attempts: int = 5
    creator_alert_webhook_url: str = ""

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

    @model_validator(mode="before")
    @classmethod
    def _load_secret_files(cls, values):
        """Docker secrets override plain environment values for secret fields."""
        if not isinstance(values, dict):
            return values
        for field in SECRET_FIELDS:
            path = os.environ.get(f"{field.upper()}_FILE")
            if not path:
                continue
            try:
                values[field] = Path(path).read_text(encoding="utf-8").strip()
            except OSError:
                # Keep the environment value; startup policy will reject placeholders.
                pass
        return values

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"


settings = Settings()
