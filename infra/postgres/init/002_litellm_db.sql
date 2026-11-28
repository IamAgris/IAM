-- OD-52: LiteLLM owns a separate database for /model/new registrations,
-- virtual keys and spend records. IAM's own schema stays in ${POSTGRES_DB}.
-- This file runs only when the postgres data volume is first created; the
-- running deployment is created by scripts/init_litellm_db.ps1.
CREATE DATABASE litellm_db;
