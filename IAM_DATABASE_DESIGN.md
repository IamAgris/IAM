# IAM — Canonical Database Design

**Version:** 1.0 · 24 November 2026  
**Status:** Provisional — pending owner decisions OD-01…OD-10  
**Parent:** `IAM_ARCHITECTURE_GAP_ANALYSIS.md` (resolves D-01…D-10, T-01, T-12)  
**Source of truth:** This document + SQLAlchemy ORM models in `backend/app/models/`. Generated migrations are the only path to schema changes.

---

## 1. Design rules

1. **One table per concept.** No parallel registries, no duplicated conversation models.
2. **Every table has an owner scope** — `iam` (private), `visitor` (pseudonymous), `public`, or `system`.
3. **Visitor-owned rows are scoped by `visitor_id` and `session_id`** and enforced in every query.
4. **Secrets are references only** — no credential values in any table.
5. **All knowledge carries provenance** — source, confidence, verification status, timestamps.
6. **All consequential actions are audited** through the append-only `audit_events` stream.
7. **Soft-delete with `deleted_at`** where retention/deletion rights apply; hard delete only via approved deletion workflow.
8. **UUID primary keys** (UUIDv4); the permanent IAM identity uses the od-01 ULID scheme in a dedicated `iam_identity_genesis` record.

---

## 2. Canonical naming map (resolves C-04)

| Document / legacy name | Canonical table |
|------------------------|-----------------|
| `model_providers`, `ai_providers` | `ai_providers` |
| `external_ai_agents`, `external_agents` | `external_agents` |
| `external_api_permissions`, `internet_permissions` | `internet_permissions` |
| `research_sources`, `internet_resources` | `research_sources` |
| `delegated_tasks`, `agent_collaborations` | `agent_collaborations` |
| `approved_reinvestments`, `business_budgets`, `financial_budgets` | `financial_budgets` (scope = system/business/project) |
| `external_services`, `external_integrations`, `integration_registry` | `integration_registry` |
| `incident_records`, `security_incidents` | `incident_records` |
| `resource_metrics`, `provider_usage`, `request_usage` | `usage_records` |
| `skills`, `capability_definitions` | `capability_definitions` |
| `model_comparisons` | `model_evaluations` (evaluation_type = comparison) |
| `conversations` + `conversation_threads` + `visitor_messages` | `conversation_threads` (owner_type = iam/visitor) + `conversation_messages` |

---

## 3. Domain: Identity and constitution

| Table | Key columns | Notes |
|-------|-------------|-------|
| `iam_identity_genesis` | `permanent_id` (ULID, immutable), `created_at`, `origin_config` JSON, `initial_capabilities` JSON | OD-01; never updated after creation |
| `ai_identity` | `id`, `public_name`, `description`, `avatar_url`, `preferences`, `interests`, `goals`, `timestamps` | Current mutable identity |
| `ai_personality` | `id`, `identity_id` FK, `traits`, `tone`, `formality_level` | |
| `identity_history` | `id`, `identity_id` FK, `change_type`, `previous_value`, `new_value`, `reason`, `changed_at` | Append-only |
| `operating_principles` | `id`, `name`, `statement`, `category`, `is_mutable`, `timestamps` | safety/legal/security = immutable (C-01 owner boundary) |
| `authority_boundaries` | `id`, `action_type`, `authority_level` (0–4), `requires_human_approval` | Canonical authority ladder (C-01) |
| `security_boundaries` | `id`, `name`, `type`, `description`, `is_immutable` | Owner-only |
| `owner_authorizations` | `id`, `action_type`, `max_level`, `spending_limit`, `can_*` flags, `granted_by`, `expires_at`, `revoked_at` | Only owner writes; resolves M-01 |
| `approval_policies` | `id`, `category`, `min_level`, `auto_approve_conditions` | |
| `approval_requests` | `id`, `action_type`, `description`, `requested_by`, `status`, `decision`, `decided_by`, `timestamps` | One approval system |

---

## 4. Domain: Conversation (resolves D-01)

**One conversation model with owner scope.**

| Table | Key columns | Notes |
|-------|-------------|-------|
| `conversation_threads` | `id`, `owner_type` (iam/visitor), `owner_id`, `session_id`, `title`, `mode`, `timestamps` | Replaces 3 overlapping models |
| `conversation_messages` | `id`, `thread_id` FK, `role`, `content`, `mode`, `metadata`, `created_at` | |
| `conversation_contexts` | `id`, `thread_id` FK, `summary`, `topics`, `emotional_context`, `updated_at` | |
| `conversation_summaries` | `id`, `thread_id` FK, `summary`, `created_at` | |
| `conversation_attachments` | `id`, `thread_id` FK, `media_asset_id` FK, `created_at` | |
| `conversation_ownership_check` | view | Enforces `session_id` match before any read/write |

**Isolation rule:** every query on these tables MUST include `owner_id = current_session.owner_id`. Enforced in repository layer and (optionally) PostgreSQL RLS.

---

## 5. Domain: Global access (resolves D-01 gap)

| Table | Key columns |
|-------|-------------|
| `anonymous_visitors` | `id`, `visitor_token` (secure random), `is_active`, `account_id`, `timestamps` |
| `visitor_sessions` | `id`, `visitor_id` FK, `session_token`, `mode`, `is_active`, `timestamps` |
| `visitor_locations` | `id`, `session_id` FK, `country`, `region`, `city`, `language`, `timezone`, `currency`, `is_estimate`, `user_corrected` |
| `visitor_preferences` | `id`, `visitor_id` FK, `key`, `value`, `updated_at` |
| `visitor_consents` | `id`, `visitor_id` FK, `consent_type`, `granted`, `retention_days`, `recorded_at` |
| `visitor_memory_permissions` | `id`, `visitor_id` FK, `allow_session_memory`, `allow_anonymous_memory`, `allow_shared_knowledge` |
| `visitor_rate_limits` | `id`, `scope_key`, `window_start`, `request_count`, `is_blocked` |
| `data_retention_policies` | `id`, `scope`, `retention_days`, `basis` |
| `deletion_requests` | `id`, `visitor_id`, `status`, `requested_at`, `completed_at` |

---

## 6. Domain: Memory and knowledge (resolves D-08)

**One base table with typed views.**

| Table | Key columns |
|-------|-------------|
| `memory_items` | `id`, `owner_type`, `owner_id`, `memory_type` (episodic/semantic/procedural/relationship/working/self), `content`, `source`, `confidence`, `verification_status`, `topic`, `provenance`, `access_permissions`, `timestamps` |
| `memory_embeddings` | `id`, `memory_item_id` FK, `embedding_model`, `embedding` (see dimension strategy), `created_at` |
| `memory_relationships` | `id`, `source_id`, `target_id`, `relationship_type`, `strength` |
| `knowledge_items` | `id`, `title`, `content`, `source`, `confidence`, `verification_status`, `topic`, `metadata` — knowledge is a *view* over semantic memory with higher verification bar |
| `knowledge_sources` | `id`, `knowledge_item_id` FK, `url`, `title`, `credibility`, `access_date` |
| `experiences` | `id`, `title`, `description`, `outcome`, `success`, `lessons`, `timestamps` — episodic memory view |
| `skills` → `capability_definitions` | consolidated capability registry |

### pgvector dimension strategy (resolves T-01)

Single fixed dimension is **not viable** — OpenAI `text-embedding-3-small` = 1536; NVIDIA `nv-embedqa-e5-v5` and Ollama models differ.

**Chosen design:** dimension-specific embedding tables:
- `memory_embeddings_1536` (vector(1536))
- `memory_embeddings_1024` (vector(1024))
- `memory_embeddings_768` (vector(768))
- `embedding_model_registry` maps model → dimension → table name

Search joins across enabled tables and normalises scores. A default dimension is chosen at deployment from the configured embedding provider.

---

## 7. Domain: Intelligence and models (resolves D-03)

| Table | Key columns |
|-------|-------------|
| `ai_providers` | `id`, `name`, `type` (hosted/local/nvidia/openweight), `base_url`, `is_active`, `free_only`, `config` |
| `discovered_models` | `id`, `provider_id` FK, `model_id`, `capabilities`, `context_length`, `is_free`, `availability`, `cost`, `last_checked` |
| `model_evaluations` | `id`, `model_id`, `evaluation_type` (benchmark/comparison/ablation), `task_type`, `score`, `details` |
| `routing_decisions` | `id`, `task_type`, `required_capabilities`, `selected_provider`, `selected_model`, `reason`, `fallback_used` |
| `usage_records` | `id`, `scope`, `scope_id`, `provider_id`, `model`, `tokens_in`, `tokens_out`, `cost_usd`, `period` |
| `experiments` | `id`, `name`, `hypothesis`, `status`, `results` |
| `software_projects` | `id`, `name`, `status`, `repository_url`, `timestamps` |
| `code_changes` | `id`, `project_id` FK, `file_path`, `change_type`, `status` |
| `deployment_records` | `id`, `project_id` FK, `version`, `environment`, `status` |
| `upgrade_history` | `id`, `component`, `previous_version`, `new_version`, `status` |

---

## 8. Domain: Autonomy, reflection, life

`goals`, `goal_lifecycles`, `plans`, `tasks`, `task_executions`, `decision_records`, `scheduled_activities`, `workflow_checkpoints`, `reflection_entries`, `life_history`, `daily_routines`.

Unified scheduler: `scheduled_activities` carries `trigger_type` (cron/event/threshold) and replaces separate monitoring schedules.

---

## 9. Domain: Internet and external AI (resolves D-04, D-09, D-10)

| Table | Key columns |
|-------|-------------|
| `integration_registry` | `id`, `name`, `provider`, `type`, `config`, `is_active`, `owner_authorized`, `timestamps` — one registry |
| `integration_permissions` | `id`, `integration_id` FK, `scope`, `granted_at`, `expires_at`, `revoked_at` |
| `credential_references` | `id`, `integration_id` FK, `secret_name`, `secret_store`, `secret_path` |
| `internet_permissions` | `id`, `action_type`, `category`, `is_autonomous`, `requires_owner_authorization` |
| `internet_sessions` | `id`, `session_token`, `purpose`, `context` (public/private/isolated), `timestamps` |
| `browser_actions` | `id`, `session_id` FK, `action_type`, `target`, `value`, `result`, `authorized` |
| `research_sources` | `id`, `url`, `title`, `summary`, `credibility`, `accessed_at` |
| `research_documents` | `id`, `source_id` FK, `content`, `findings`, `query` |
| `monitored_targets` | `id`, `url`, `type`, `interval`, `last_checked`, `status` |
| `monitoring_events` | `id`, `target_id` FK, `event_type`, `details`, `created_at` |
| `retrieved_files` | `id`, `source_url`, `storage_path`, `scan_status`, `size_bytes` |
| `published_content` | `id`, `title`, `type`, `target_platform`, `url`, `authorized_by`, `published_at` |
| `online_accounts` | `id`, `platform`, `identifier`, `type`, `authorized_by`, `credential_reference` |
| `external_agents` | `id`, `name`, `endpoint`, `protocol`, `capabilities`, `status`, `trust_score` |
| `agent_interactions` | `id`, `agent_id` FK, `direction`, `request`, `response`, `risk`, `validated` |
| `agent_trust_records` | `id`, `agent_id` FK, `assessment`, `delta`, `evidence` |
| `agent_collaborations` | `id`, `agent_id` FK, `task`, `status`, `result`, `authorized` — merges delegated_tasks |
| `internet_events` | append-only audit of internet activity |

---

## 10. Domain: Economy, assets, ecosystem, resilience

| Group | Tables |
|-------|--------|
| Business | `business_opportunities`, `business_projects`, `business_performance`, `customers`, `sales_records`, `business_reports`, `project_portfolios` |
| Finance | `financial_transactions`, `financial_ledger` (double-entry), `financial_budgets`, `operating_expenses`, `crypto_activities` |
| Digital assets | `digital_assets`, `asset_licences`, `domain_registrations`, `ip_records` |
| Ecosystem | `ecosystem_projects`, `project_resources`, `project_performance` |
| Resilience | `health_checks`, `recovery_logs`, `backup_verifications`, `incident_records`, `credential_rotations` |
| Security | `tool_registry`, `tool_permissions`, `audit_events` (append-only), `security_boundaries` |
| World model | `world_entities`, `entity_relationships`, `cause_effect_chains`, `world_events`, `capability_limitations` |
| Evaluation | `evaluation_runs`, `evaluation_results`, `benchmarks` |

---

## 11. Indexes and constraints

- GIN indexes on JSONB config/capabilities/metadata columns used in filters.
- IVFFLAT/HNSW indexes on each `memory_embeddings_*` table.
- B-tree indexes on: all FK columns, `owner_id`/`session_id`, `status`, `created_at`, `visitor_token`, `session_token`.
- Unique constraints: `iam_identity_genesis.permanent_id`, identity tokens, integration name+provider, domain name.
- Check constraints mirroring current enums (authority level 0–4, memory type, visibility, risk, status).
- Foreign keys with explicit `ON DELETE` behaviour matching the current ORM.

---

## 12. Migration strategy (resolves T-12)

1. Freeze the ORM models as the single schema definition.
2. Generate an initial Alembic revision from `Base.metadata` (`alembic revision --autogenerate`).
3. Retire `001_initial_schema.sql` as a hand-maintained source; keep it only as a reference snapshot.
4. Each subsequent schema change = one Alembic revision with `upgrade()`/`downgrade()`.
5. CI check: `alembic check` fails if models diverge from migrations.
6. All migrations run in a transaction; backups taken before any destructive migration.

---

## 13. Owner decisions — LOCKED (24 November 2026)

All ten decisions are resolved in `IAM_OWNER_DECISIONS.md`. Impacts on this schema:

| Decision | Schema impact |
|----------|---------------|
| OD-01 | `iam_identity_genesis.permanent_id` = ULID, immutable |
| OD-02 | `digital_assets.owner_entity`, `business_projects.legal_entity` = designated entity |
| OD-03 | `owner_authorizations` and `approval_requests` carry `signer_ref` (hardware key/signer) and `signature` |
| OD-04 | `financial_budgets.amount` default 0; every spend requires an approved `approval_requests` record — no standing spend |
| OD-05 | `visitor_memory_permissions.allow_anonymous_memory` default **true** (opt-out model); `deletion_requests` and retention policies required |
| OD-06 | backup/verification cadence: daily (RPO 24h), restore procedure documented for RTO 4h |
| OD-07 | no secret values in tables; `credential_references` points to SOPS/Docker secrets only |
| OD-08 | `request_jobs` and `worker_executions` designed for ARQ workers |
| OD-09 | `data_retention_policies` and `privacy_audit_events` cover global regimes (GDPR, POPIA, CCPA, ...) |
| OD-10 | development and production data strictly separated; no production credentials in dev tables/config |

No provisional values remain.
