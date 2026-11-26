-- =============================================================================
-- Project AURA - Initial Database Schema (Phase 0)
-- Generated from ORM metadata by app.db.migrations.generate_initial_schema.
-- Tables are emitted in foreign-key dependency order.
-- =============================================================================

CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE ai_identity (
	id UUID NOT NULL, 
	name TEXT NOT NULL, 
	description TEXT, 
	avatar_url TEXT, 
	communication_preferences JSON NOT NULL, 
	interests JSON NOT NULL, 
	personal_goals JSON NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id)
);

CREATE TABLE ai_providers (
	id UUID NOT NULL, 
	name TEXT NOT NULL, 
	provider_type TEXT NOT NULL, 
	base_url TEXT, 
	is_active BOOLEAN NOT NULL, 
	free_only BOOLEAN NOT NULL, 
	config JSON NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT ck_ai_provider_type CHECK (provider_type IN ('hosted', 'local', 'nvidia', 'openweight')), 
	UNIQUE (name)
);

CREATE TABLE anonymous_visitors (
	id UUID NOT NULL, 
	visitor_token VARCHAR(64) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	last_activity_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	is_active BOOLEAN NOT NULL, 
	account_id UUID, 
	PRIMARY KEY (id)
);

CREATE UNIQUE INDEX ix_anonymous_visitors_visitor_token ON anonymous_visitors (visitor_token);

CREATE TABLE api_credentials (
	id UUID NOT NULL, 
	name TEXT NOT NULL, 
	key_hash TEXT NOT NULL, 
	scope TEXT NOT NULL, 
	is_active BOOLEAN NOT NULL, 
	created_by TEXT NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	last_used_at TIMESTAMP WITH TIME ZONE, 
	revoked_at TIMESTAMP WITH TIME ZONE, 
	PRIMARY KEY (id), 
	CONSTRAINT ck_api_credential_scope CHECK (scope IN ('user', 'service', 'operator', 'admin')), 
	UNIQUE (name)
);

CREATE UNIQUE INDEX ix_api_credentials_key_hash ON api_credentials (key_hash);

CREATE TABLE approval_policies (
	id UUID NOT NULL, 
	action_category TEXT NOT NULL, 
	min_authority_level TEXT NOT NULL, 
	auto_approve_conditions JSON NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT ck_approval_policy_level CHECK (min_authority_level IN ('1', '2', '3', '4'))
);

CREATE TABLE assistant_systems (
	id UUID NOT NULL, 
	name TEXT NOT NULL, 
	vendor TEXT NOT NULL, 
	official_docs_url TEXT NOT NULL, 
	integration_method TEXT NOT NULL, 
	public_capabilities JSON NOT NULL, 
	terms_url TEXT, 
	status TEXT NOT NULL, 
	verified_at TIMESTAMP WITH TIME ZONE, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT ck_assistant_system_status CHECK (status IN ('studied', 'integration_available', 'replicated')), 
	UNIQUE (name)
);

CREATE TABLE audit_events (
	id UUID NOT NULL, 
	event_type TEXT NOT NULL, 
	actor TEXT NOT NULL, 
	target TEXT, 
	details JSON NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id)
);

CREATE TABLE authority_boundaries (
	id UUID NOT NULL, 
	action_type TEXT NOT NULL, 
	authority_level TEXT NOT NULL, 
	description TEXT, 
	requires_human_approval BOOLEAN NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT ck_authority_level CHECK (authority_level IN ('1', '2', '3', '4'))
);

CREATE TABLE backup_verifications (
	id UUID NOT NULL, 
	backup_id TEXT NOT NULL, 
	verification_type TEXT NOT NULL, 
	success BOOLEAN NOT NULL, 
	restored_items INTEGER, 
	verified_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id)
);

CREATE TABLE business_opportunities (
	id UUID NOT NULL, 
	title TEXT NOT NULL, 
	description TEXT, 
	estimated_revenue NUMERIC(15, 4), 
	confidence NUMERIC(3, 2) NOT NULL, 
	status TEXT NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT ck_opportunity_confidence CHECK (confidence BETWEEN 0 AND 1), 
	CONSTRAINT ck_opportunity_status CHECK (status IN ('identified', 'evaluating', 'pursuing', 'rejected', 'completed'))
);

CREATE TABLE capability_definitions (
	id UUID NOT NULL, 
	name TEXT NOT NULL, 
	category TEXT NOT NULL, 
	description TEXT, 
	target_proficiency INTEGER NOT NULL, 
	is_learnable BOOLEAN NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT ck_capability_category CHECK (category IN ('programming', 'languages', 'mathematics', 'business', 'science', 'communication', 'cybersecurity', 'finance', 'robotics')), 
	CONSTRAINT ck_capability_target_proficiency CHECK (target_proficiency BETWEEN 0 AND 100)
);

CREATE TABLE capability_limitations (
	id UUID NOT NULL, 
	capability_name TEXT NOT NULL, 
	proficiency_level INTEGER NOT NULL, 
	limitation_description TEXT, 
	last_assessed_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	assessment_method TEXT, 
	PRIMARY KEY (id), 
	CONSTRAINT ck_capability_limitation_level CHECK (proficiency_level BETWEEN 0 AND 100)
);

CREATE TABLE cause_effect_chains (
	id UUID NOT NULL, 
	cause_description TEXT NOT NULL, 
	effect_description TEXT NOT NULL, 
	confidence NUMERIC(3, 2) NOT NULL, 
	evidence JSON NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT ck_cause_effect_confidence CHECK (confidence BETWEEN 0 AND 1)
);

CREATE TABLE cloud_workloads (
	id UUID NOT NULL, 
	name TEXT NOT NULL, 
	workload_type TEXT NOT NULL, 
	provider TEXT, 
	endpoint_url TEXT, 
	status TEXT NOT NULL, 
	config JSON NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT ck_cloud_workload_status CHECK (status IN ('running', 'stopped', 'failed'))
);

CREATE TABLE communication_audit (
	id UUID NOT NULL, 
	channel TEXT NOT NULL, 
	direction TEXT NOT NULL, 
	actor TEXT NOT NULL, 
	purpose TEXT NOT NULL, 
	request_id TEXT, 
	details JSON NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT ck_communication_channel CHECK (channel IN ('creator_email', 'operational_email', 'private_user')), 
	CONSTRAINT ck_communication_direction CHECK (direction IN ('outbound', 'inbound'))
);

CREATE TABLE conversation_contexts (
	id UUID NOT NULL, 
	conversation_id TEXT NOT NULL, 
	participant_id TEXT, 
	context_summary TEXT, 
	topics_discussed JSON NOT NULL, 
	emotional_context TEXT, 
	last_updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id)
);

CREATE TABLE conversations (
	id UUID NOT NULL, 
	title TEXT, 
	started_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	ended_at TIMESTAMP WITH TIME ZONE, 
	metadata JSON NOT NULL, 
	PRIMARY KEY (id)
);

CREATE TABLE creator_email_dead_letters (
	id UUID NOT NULL, 
	request_id TEXT NOT NULL, 
	recipient TEXT NOT NULL, 
	attempts INTEGER NOT NULL, 
	last_error TEXT, 
	failed_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	resolved_at TIMESTAMP WITH TIME ZONE, 
	PRIMARY KEY (id)
);

CREATE UNIQUE INDEX ix_creator_email_dead_letters_request_id ON creator_email_dead_letters (request_id);

CREATE TABLE creator_email_outbox (
	id UUID NOT NULL, 
	request_id TEXT NOT NULL, 
	recipient TEXT NOT NULL, 
	subject TEXT NOT NULL, 
	body TEXT NOT NULL, 
	transport TEXT NOT NULL, 
	status TEXT NOT NULL, 
	attempts INTEGER NOT NULL, 
	last_error TEXT, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	sent_at TIMESTAMP WITH TIME ZONE, 
	PRIMARY KEY (id), 
	CONSTRAINT ck_creator_outbox_status CHECK (status IN ('pending', 'sent', 'failed', 'skipped'))
);

CREATE UNIQUE INDEX ix_creator_email_outbox_request_id ON creator_email_outbox (request_id);

CREATE TABLE creator_messages (
	id UUID NOT NULL, 
	message_id TEXT NOT NULL, 
	direction TEXT NOT NULL, 
	purpose TEXT NOT NULL, 
	subject TEXT NOT NULL, 
	body TEXT NOT NULL, 
	status TEXT NOT NULL, 
	authority_bearing BOOLEAN NOT NULL, 
	request_id TEXT, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT ck_creator_message_direction CHECK (direction IN ('outbound', 'inbound')), 
	CONSTRAINT ck_creator_message_purpose CHECK (purpose IN ('question', 'status_update', 'reply')), 
	CONSTRAINT ck_creator_message_no_authority CHECK (authority_bearing = false)
);

CREATE UNIQUE INDEX ix_creator_messages_message_id ON creator_messages (message_id);

CREATE TABLE creator_requests (
	id UUID NOT NULL, 
	request_id TEXT NOT NULL, 
	action_type TEXT NOT NULL, 
	target_ref TEXT, 
	risk_level TEXT NOT NULL, 
	summary TEXT NOT NULL, 
	reason TEXT, 
	consequences JSON NOT NULL, 
	status TEXT NOT NULL, 
	requester TEXT NOT NULL, 
	creator_email TEXT, 
	channel TEXT NOT NULL, 
	requested_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	expires_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	resolved_at TIMESTAMP WITH TIME ZONE, 
	metadata JSON NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT ck_creator_request_risk CHECK (risk_level IN ('1', '2', '3', '4')), 
	CONSTRAINT ck_creator_request_status CHECK (status IN ('pending', 'approved', 'rejected', 'expired', 'cancelled'))
);

CREATE INDEX ix_creator_requests_action_type ON creator_requests (action_type);

CREATE UNIQUE INDEX ix_creator_requests_request_id ON creator_requests (request_id);

CREATE TABLE daily_routines (
	id UUID NOT NULL, 
	name TEXT NOT NULL, 
	description TEXT, 
	time_of_day TEXT NOT NULL, 
	activity_type TEXT NOT NULL, 
	duration_minutes INTEGER, 
	is_active BOOLEAN NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id)
);

CREATE TABLE decision_records (
	id UUID NOT NULL, 
	decision TEXT NOT NULL, 
	reasoning TEXT, 
	confidence NUMERIC(3, 2) NOT NULL, 
	outcome TEXT, 
	made_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	reviewed_at TIMESTAMP WITH TIME ZONE, 
	PRIMARY KEY (id), 
	CONSTRAINT ck_decision_confidence CHECK (confidence BETWEEN 0 AND 1)
);

CREATE TABLE digital_assets (
	id UUID NOT NULL, 
	name TEXT NOT NULL, 
	asset_type TEXT NOT NULL, 
	description TEXT, 
	source_code_location TEXT, 
	licence_type TEXT, 
	owner_entity TEXT NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	revenue_generated NUMERIC(15, 4) NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT ck_digital_asset_revenue CHECK (revenue_generated >= 0)
);

CREATE TABLE discovered_models (
	id UUID NOT NULL, 
	provider_id UUID NOT NULL, 
	model_id TEXT NOT NULL, 
	display_name TEXT, 
	capabilities JSON NOT NULL, 
	context_length INTEGER, 
	is_free BOOLEAN NOT NULL, 
	is_available BOOLEAN NOT NULL, 
	cost_input_per_1m NUMERIC(12, 6), 
	cost_output_per_1m NUMERIC(12, 6), 
	quality_score NUMERIC(5, 4), 
	discovered_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	last_checked_at TIMESTAMP WITH TIME ZONE, 
	PRIMARY KEY (id)
);

CREATE TABLE domain_registrations (
	id UUID NOT NULL, 
	domain_name TEXT NOT NULL, 
	registrar TEXT, 
	registered_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	expires_at TIMESTAMP WITH TIME ZONE, 
	owner_entity TEXT NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (domain_name)
);

CREATE TABLE experiences (
	id UUID NOT NULL, 
	title TEXT NOT NULL, 
	description TEXT, 
	outcome TEXT, 
	success BOOLEAN, 
	lessons_learned TEXT, 
	occurred_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	recorded_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id)
);

CREATE TABLE experiments (
	id UUID NOT NULL, 
	name TEXT NOT NULL, 
	description TEXT, 
	hypothesis TEXT, 
	status TEXT NOT NULL, 
	results JSON NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	completed_at TIMESTAMP WITH TIME ZONE, 
	PRIMARY KEY (id), 
	CONSTRAINT ck_experiment_status CHECK (status IN ('pending', 'running', 'completed', 'failed'))
);

CREATE TABLE external_agents (
	id UUID NOT NULL, 
	name TEXT NOT NULL, 
	endpoint_url TEXT, 
	protocol TEXT NOT NULL, 
	capabilities JSON NOT NULL, 
	description TEXT, 
	discovery_source TEXT, 
	status TEXT NOT NULL, 
	trust_score NUMERIC(3, 2) NOT NULL, 
	is_active BOOLEAN NOT NULL, 
	discovered_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	last_contacted_at TIMESTAMP WITH TIME ZONE, 
	claimed_identity TEXT, 
	creator TEXT, 
	operator TEXT, 
	stated_purpose TEXT, 
	identity_verification TEXT NOT NULL, 
	verification_evidence JSON NOT NULL, 
	verified_at TIMESTAMP WITH TIME ZONE, 
	expertise JSON NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT ck_agent_protocol CHECK (protocol IN ('rest', 'mcp', 'a2a', 'websocket', 'webhook')), 
	CONSTRAINT ck_agent_status CHECK (status IN ('discovered', 'contacted', 'trusted', 'blocked')), 
	CONSTRAINT ck_agent_trust_score CHECK (trust_score BETWEEN 0 AND 1), 
	CONSTRAINT ck_agent_identity_verification CHECK (identity_verification IN ('self-reported', 'verified'))
);

CREATE TABLE external_integrations (
	id UUID NOT NULL, 
	name TEXT NOT NULL, 
	service_type TEXT NOT NULL, 
	endpoint_url TEXT, 
	auth_method TEXT, 
	config JSON NOT NULL, 
	is_active BOOLEAN NOT NULL, 
	requires_authorization BOOLEAN NOT NULL, 
	owner_authorized BOOLEAN NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT ck_external_integration_type CHECK (service_type IN ('api', 'webhook', 'mcp', 'cloud'))
);

CREATE TABLE fallback_configs (
	id UUID NOT NULL, 
	primary_model TEXT NOT NULL, 
	fallback_model TEXT NOT NULL, 
	fallback_provider TEXT NOT NULL, 
	is_active BOOLEAN NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id)
);

CREATE TABLE financial_budgets (
	id UUID NOT NULL, 
	category TEXT NOT NULL, 
	amount NUMERIC(15, 4) NOT NULL, 
	period TEXT NOT NULL, 
	is_approved BOOLEAN NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id)
);

CREATE TABLE financial_transactions (
	id UUID NOT NULL, 
	amount NUMERIC(15, 4) NOT NULL, 
	currency TEXT NOT NULL, 
	type TEXT NOT NULL, 
	description TEXT, 
	reference_id TEXT, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT ck_transaction_type CHECK (type IN ('income', 'expense', 'transfer'))
);

CREATE TABLE free_sandbox_providers (
	id UUID NOT NULL, 
	name TEXT NOT NULL, 
	provider_type TEXT NOT NULL, 
	capabilities JSON NOT NULL, 
	terms_url TEXT NOT NULL, 
	docs_verified_at TIMESTAMP WITH TIME ZONE, 
	headless BOOLEAN NOT NULL, 
	registration_status TEXT NOT NULL, 
	is_active BOOLEAN NOT NULL, 
	credential_env TEXT, 
	config JSON NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT ck_free_sandbox_registration_status CHECK (registration_status IN ('candidate', 'registered', 'pending_creator_approval', 'unavailable')), 
	UNIQUE (name)
);

CREATE TABLE geo_data_files (
	id UUID NOT NULL, 
	name TEXT NOT NULL, 
	data_format TEXT NOT NULL, 
	content_hash TEXT NOT NULL, 
	data JSON NOT NULL, 
	licence TEXT NOT NULL, 
	source TEXT NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id)
);

CREATE INDEX ix_geo_data_files_content_hash ON geo_data_files (content_hash);

CREATE TABLE geo_places (
	id UUID NOT NULL, 
	name TEXT NOT NULL, 
	place_type TEXT NOT NULL, 
	country_code TEXT, 
	latitude FLOAT NOT NULL, 
	longitude FLOAT NOT NULL, 
	attributes JSON NOT NULL, 
	source TEXT NOT NULL, 
	source_url TEXT, 
	confidence FLOAT NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT ck_geo_place_latitude CHECK (latitude BETWEEN -90 AND 90), 
	CONSTRAINT ck_geo_place_longitude CHECK (longitude BETWEEN -180 AND 180), 
	CONSTRAINT ck_geo_place_confidence CHECK (confidence BETWEEN 0 AND 1)
);

CREATE INDEX ix_geo_places_name ON geo_places (name);

CREATE TABLE geo_providers (
	id UUID NOT NULL, 
	name TEXT NOT NULL, 
	kind TEXT NOT NULL, 
	base_url TEXT NOT NULL, 
	licence TEXT NOT NULL, 
	free_quota TEXT, 
	requires_key BOOLEAN NOT NULL, 
	is_paid BOOLEAN NOT NULL, 
	paid_use_approved BOOLEAN NOT NULL, 
	is_active BOOLEAN NOT NULL, 
	terms_url TEXT, 
	verified_at TIMESTAMP WITH TIME ZONE, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT ck_geo_provider_kind CHECK (kind IN ('tile', 'geocoder', 'routing', 'dataset', 'live_feed')), 
	UNIQUE (name)
);

CREATE TABLE goals (
	id UUID NOT NULL, 
	title TEXT NOT NULL, 
	description TEXT, 
	status TEXT NOT NULL, 
	priority INTEGER NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	target_completion_date TIMESTAMP WITH TIME ZONE, 
	completed_at TIMESTAMP WITH TIME ZONE, 
	PRIMARY KEY (id), 
	CONSTRAINT ck_goal_status CHECK (status IN ('active', 'paused', 'completed', 'abandoned')), 
	CONSTRAINT ck_goal_priority CHECK (priority BETWEEN 1 AND 10)
);

CREATE TABLE health_checks (
	id UUID NOT NULL, 
	service_name TEXT NOT NULL, 
	status TEXT NOT NULL, 
	response_time_ms INTEGER, 
	details JSON NOT NULL, 
	checked_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT ck_health_check_status CHECK (status IN ('healthy', 'degraded', 'down'))
);

CREATE TABLE iam_identity_genesis (
	id UUID NOT NULL, 
	permanent_id TEXT NOT NULL, 
	public_name TEXT NOT NULL, 
	full_name TEXT, 
	origin_config JSON NOT NULL, 
	initial_capabilities JSON NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (permanent_id)
);

CREATE TABLE incident_records (
	id UUID NOT NULL, 
	incident_type TEXT NOT NULL, 
	severity TEXT NOT NULL, 
	title TEXT NOT NULL, 
	description TEXT, 
	detected_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	resolved_at TIMESTAMP WITH TIME ZONE, 
	resolution TEXT, 
	PRIMARY KEY (id), 
	CONSTRAINT ck_incident_severity CHECK (severity IN ('low', 'medium', 'high', 'critical'))
);

CREATE TABLE integration_registry (
	id UUID NOT NULL, 
	name TEXT NOT NULL, 
	provider TEXT NOT NULL, 
	integration_type TEXT NOT NULL, 
	config JSON NOT NULL, 
	is_active BOOLEAN NOT NULL, 
	requires_creator_approval BOOLEAN NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id)
);

CREATE TABLE integrity_manifests (
	id UUID NOT NULL, 
	version TEXT NOT NULL, 
	root_hash TEXT NOT NULL, 
	manifest JSON NOT NULL, 
	signed_by TEXT NOT NULL, 
	is_active BOOLEAN NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id)
);

CREATE INDEX ix_integrity_manifests_root_hash ON integrity_manifests (root_hash);

CREATE TABLE internet_events (
	id UUID NOT NULL, 
	event_type TEXT NOT NULL, 
	target TEXT, 
	details JSON NOT NULL, 
	risk_level TEXT NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT ck_internet_event_risk CHECK (risk_level IN ('low', 'medium', 'high'))
);

CREATE TABLE internet_permissions (
	id UUID NOT NULL, 
	action_type TEXT NOT NULL, 
	category TEXT NOT NULL, 
	is_autonomous BOOLEAN NOT NULL, 
	requires_owner_authorization BOOLEAN NOT NULL, 
	description TEXT, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT ck_internet_permission_category CHECK (category IN ('exploration', 'communication', 'financial', 'publishing', 'account')), 
	UNIQUE (action_type)
);

CREATE TABLE internet_resources (
	id UUID NOT NULL, 
	url TEXT NOT NULL, 
	resource_type TEXT NOT NULL, 
	title TEXT, 
	summary TEXT, 
	credibility_score NUMERIC(3, 2) NOT NULL, 
	accessed_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT ck_internet_resource_credibility CHECK (credibility_score BETWEEN 0 AND 1)
);

CREATE TABLE internet_sessions (
	id UUID NOT NULL, 
	session_token VARCHAR(64) NOT NULL, 
	purpose TEXT, 
	started_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	ended_at TIMESTAMP WITH TIME ZONE, 
	is_active BOOLEAN NOT NULL, 
	PRIMARY KEY (id)
);

CREATE UNIQUE INDEX ix_internet_sessions_session_token ON internet_sessions (session_token);

CREATE TABLE knowledge_items (
	id UUID NOT NULL, 
	title TEXT NOT NULL, 
	content TEXT NOT NULL, 
	source TEXT, 
	confidence_level NUMERIC(3, 2) NOT NULL, 
	verification_status TEXT NOT NULL, 
	topic TEXT, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	last_reviewed_at TIMESTAMP WITH TIME ZONE, 
	metadata JSON NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT ck_knowledge_confidence_level CHECK (confidence_level BETWEEN 0 AND 1), 
	CONSTRAINT ck_knowledge_verification_status CHECK (verification_status IN ('unverified', 'verified', 'disputed', 'retracted'))
);

CREATE TABLE language_profiles (
	id UUID NOT NULL, 
	language_code TEXT NOT NULL, 
	vocabulary_level INTEGER NOT NULL, 
	grammar_level INTEGER NOT NULL, 
	reading_comprehension INTEGER NOT NULL, 
	listening_comprehension INTEGER NOT NULL, 
	writing_ability INTEGER NOT NULL, 
	conversational_ability INTEGER NOT NULL, 
	pronunciation_level INTEGER NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id)
);

CREATE TABLE legal_sources (
	id UUID NOT NULL, 
	name TEXT NOT NULL, 
	jurisdiction TEXT NOT NULL, 
	authority_type TEXT NOT NULL, 
	url TEXT NOT NULL, 
	feed_url TEXT, 
	reliability TEXT NOT NULL, 
	is_active BOOLEAN NOT NULL, 
	last_checked_at TIMESTAMP WITH TIME ZONE, 
	last_content_hash TEXT, 
	terms_url TEXT, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT ck_legal_source_authority_type CHECK (authority_type IN ('government', 'parliament', 'court', 'regulator', 'central_bank', 'tax_authority', 'international', 'security_authority')), 
	UNIQUE (name)
);

CREATE TABLE life_cycles (
	id UUID NOT NULL, 
	cycle_date TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	state TEXT NOT NULL, 
	started_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	ended_at TIMESTAMP WITH TIME ZONE, 
	activities_completed JSON NOT NULL, 
	resources_consumed JSON NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT ck_lifecycle_state CHECK (state IN ('idle', 'working', 'researching', 'learning', 'resting', 'conserving'))
);

CREATE TABLE life_history (
	id UUID NOT NULL, 
	event_type TEXT NOT NULL, 
	title TEXT NOT NULL, 
	description TEXT, 
	significance INTEGER NOT NULL, 
	occurred_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	recorded_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	related_memory_ids JSON NOT NULL, 
	related_goal_ids JSON NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT ck_life_history_significance CHECK (significance BETWEEN 1 AND 10)
);

CREATE TABLE live_geo_feeds (
	id UUID NOT NULL, 
	name TEXT NOT NULL, 
	category TEXT NOT NULL, 
	source TEXT NOT NULL, 
	source_url TEXT NOT NULL, 
	refresh_seconds INTEGER NOT NULL, 
	last_fetched_at TIMESTAMP WITH TIME ZONE, 
	last_data_hash TEXT, 
	is_active BOOLEAN NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT ck_live_geo_feed_category CHECK (category IN ('traffic', 'weather', 'transit', 'aviation', 'maritime', 'disaster', 'environment', 'satellite', 'infrastructure')), 
	UNIQUE (name)
);

CREATE TABLE location_permissions (
	id UUID NOT NULL, 
	subject TEXT NOT NULL, 
	precision TEXT NOT NULL, 
	purpose TEXT NOT NULL, 
	granted_by TEXT NOT NULL, 
	granted_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	revoked_at TIMESTAMP WITH TIME ZONE, 
	PRIMARY KEY (id), 
	CONSTRAINT ck_location_permission_precision CHECK (precision IN ('approximate', 'precise'))
);

CREATE INDEX ix_location_permissions_subject ON location_permissions (subject);

CREATE TABLE memory_items (
	id UUID NOT NULL, 
	content TEXT NOT NULL, 
	memory_type TEXT NOT NULL, 
	source TEXT, 
	confidence_level NUMERIC(3, 2) NOT NULL, 
	topic TEXT, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	last_reviewed_at TIMESTAMP WITH TIME ZONE, 
	expires_at TIMESTAMP WITH TIME ZONE, 
	metadata JSON NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT ck_memory_type CHECK (memory_type IN ('fact', 'opinion', 'hypothesis', 'preference', 'creative', 'experience')), 
	CONSTRAINT ck_memory_confidence_level CHECK (confidence_level BETWEEN 0 AND 1)
);

CREATE TABLE model_comparisons (
	id UUID NOT NULL, 
	model_name TEXT NOT NULL, 
	provider TEXT NOT NULL, 
	model_id TEXT NOT NULL, 
	capabilities_tested JSON NOT NULL, 
	scores JSON NOT NULL, 
	overall_score NUMERIC(5, 4), 
	tested_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	is_adopted BOOLEAN NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT ck_model_comparison_score CHECK (overall_score BETWEEN 0 AND 1)
);

CREATE TABLE model_portability_exports (
	id UUID NOT NULL, 
	export_format TEXT NOT NULL, 
	export_scope JSON NOT NULL, 
	exported_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	export_location TEXT, 
	PRIMARY KEY (id)
);

CREATE TABLE model_registry (
	id UUID NOT NULL, 
	name TEXT NOT NULL, 
	provider TEXT NOT NULL, 
	model_id TEXT NOT NULL, 
	capabilities JSON NOT NULL, 
	cost_per_token_input NUMERIC(10, 6), 
	cost_per_token_output NUMERIC(10, 6), 
	is_active BOOLEAN NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id)
);

CREATE TABLE monitored_targets (
	id UUID NOT NULL, 
	target_url TEXT NOT NULL, 
	target_type TEXT NOT NULL, 
	check_interval_minutes INTEGER NOT NULL, 
	last_checked_at TIMESTAMP WITH TIME ZONE, 
	last_status TEXT, 
	is_active BOOLEAN NOT NULL, 
	config JSON NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT ck_monitored_target_type CHECK (target_type IN ('website', 'service', 'news', 'competitor'))
);

CREATE TABLE online_accounts (
	id UUID NOT NULL, 
	platform TEXT NOT NULL, 
	account_identifier TEXT, 
	account_type TEXT NOT NULL, 
	is_authorised BOOLEAN NOT NULL, 
	authorised_by TEXT, 
	credential_reference TEXT, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT ck_online_account_type CHECK (account_type IN ('service', 'community', 'social', 'business'))
);

CREATE TABLE operating_expenses (
	id UUID NOT NULL, 
	category TEXT NOT NULL, 
	amount NUMERIC(15, 4) NOT NULL, 
	description TEXT, 
	incurred_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id)
);

CREATE TABLE operating_principles (
	id UUID NOT NULL, 
	principle_name TEXT NOT NULL, 
	principle_statement TEXT NOT NULL, 
	category TEXT NOT NULL, 
	is_mutable BOOLEAN NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT ck_operating_principle_category CHECK (category IN ('safety', 'legal', 'security', 'operational', 'personal'))
);

CREATE TABLE owner_authorizations (
	id UUID NOT NULL, 
	action_type TEXT NOT NULL, 
	max_authority_level VARCHAR(1) NOT NULL, 
	spending_limit_usd NUMERIC(15, 4), 
	can_create_accounts BOOLEAN NOT NULL, 
	can_publish_externally BOOLEAN NOT NULL, 
	can_modify_own_security BOOLEAN NOT NULL, 
	scope JSON NOT NULL, 
	is_active BOOLEAN NOT NULL, 
	granted_by TEXT NOT NULL, 
	granted_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	expires_at TIMESTAMP WITH TIME ZONE, 
	revoked_at TIMESTAMP WITH TIME ZONE, 
	PRIMARY KEY (id), 
	CONSTRAINT ck_owner_auth_level CHECK (max_authority_level IN ('1', '2', '3', '4'))
);

CREATE INDEX ix_owner_authorizations_action_type ON owner_authorizations (action_type);

CREATE TABLE project_portfolios (
	id UUID NOT NULL, 
	name TEXT NOT NULL, 
	description TEXT, 
	total_projects INTEGER NOT NULL, 
	active_projects INTEGER NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id)
);

CREATE TABLE provider_usage (
	id UUID NOT NULL, 
	provider_id UUID NOT NULL, 
	model_id TEXT, 
	tokens_input INTEGER NOT NULL, 
	tokens_output INTEGER NOT NULL, 
	estimated_cost_usd NUMERIC(12, 6) NOT NULL, 
	period TEXT NOT NULL, 
	recorded_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id)
);

CREATE TABLE public_people (
	id UUID NOT NULL, 
	canonical_name TEXT NOT NULL, 
	internal_public_id TEXT NOT NULL, 
	notes TEXT, 
	deanonymized BOOLEAN NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT ck_public_person_no_deanonymization CHECK (deanonymized = FALSE), 
	UNIQUE (internal_public_id)
);

CREATE INDEX ix_public_people_canonical_name ON public_people (canonical_name);

CREATE TABLE public_sources (
	id UUID NOT NULL, 
	name TEXT NOT NULL, 
	jurisdiction TEXT NOT NULL, 
	category TEXT NOT NULL, 
	url TEXT NOT NULL, 
	access_condition TEXT NOT NULL, 
	reliability TEXT NOT NULL, 
	terms_url TEXT, 
	last_verified_at TIMESTAMP WITH TIME ZONE, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT ck_public_source_access_condition CHECK (access_condition IN ('public', 'requires_authority', 'restricted', 'paid', 'unknown')), 
	CONSTRAINT ck_public_source_reliability CHECK (reliability IN ('official', 'independent', 'self_reported', 'unverified')), 
	UNIQUE (name)
);

CREATE TABLE published_content (
	id UUID NOT NULL, 
	title TEXT NOT NULL, 
	content_type TEXT NOT NULL, 
	target_platform TEXT, 
	url TEXT, 
	is_authorised BOOLEAN NOT NULL, 
	authorised_by TEXT, 
	published_at TIMESTAMP WITH TIME ZONE, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT ck_published_content_type CHECK (content_type IN ('article', 'post', 'website', 'product', 'code'))
);

CREATE TABLE recovery_logs (
	id UUID NOT NULL, 
	service_name TEXT NOT NULL, 
	action TEXT NOT NULL, 
	success BOOLEAN NOT NULL, 
	details JSON NOT NULL, 
	performed_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id)
);

CREATE TABLE reflection_entries (
	id UUID NOT NULL, 
	reflection_type TEXT NOT NULL, 
	title TEXT NOT NULL, 
	content TEXT NOT NULL, 
	lesson_learned TEXT, 
	confidence NUMERIC(3, 2) NOT NULL, 
	related_decision_ids JSON NOT NULL, 
	related_memory_ids JSON NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT ck_reflection_confidence CHECK (confidence BETWEEN 0 AND 1)
);

CREATE TABLE regional_settings (
	id UUID NOT NULL, 
	country_code TEXT NOT NULL, 
	language TEXT, 
	currency TEXT, 
	timezone TEXT, 
	defaults JSON NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (country_code)
);

CREATE TABLE registered_nodes (
	id UUID NOT NULL, 
	name TEXT NOT NULL, 
	architecture TEXT NOT NULL, 
	resources JSON NOT NULL, 
	capabilities JSON NOT NULL, 
	trust_level TEXT NOT NULL, 
	is_active BOOLEAN NOT NULL, 
	contribution_percent FLOAT NOT NULL, 
	status TEXT NOT NULL, 
	registered_by_token_id UUID, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	last_seen_at TIMESTAMP WITH TIME ZONE, 
	PRIMARY KEY (id), 
	CONSTRAINT ck_registered_node_trust_level CHECK (trust_level IN ('candidate', 'restricted', 'trusted', 'revoked')), 
	CONSTRAINT ck_registered_node_contribution_ceiling CHECK (contribution_percent >= 0 AND contribution_percent <= 1)
);

CREATE TABLE replication_experiments (
	id UUID NOT NULL, 
	capability TEXT NOT NULL, 
	hypothesis TEXT NOT NULL, 
	method TEXT NOT NULL, 
	evidence JSON NOT NULL, 
	result TEXT NOT NULL, 
	isolated BOOLEAN NOT NULL, 
	production_adopted BOOLEAN NOT NULL, 
	creator_approval_reference TEXT, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT ck_replication_experiment_result CHECK (result IN ('planned', 'running', 'succeeded', 'failed'))
);

CREATE TABLE request_usage (
	id UUID NOT NULL, 
	session_id UUID, 
	tokens_input INTEGER NOT NULL, 
	tokens_output INTEGER NOT NULL, 
	provider TEXT, 
	model TEXT, 
	cost_usd NUMERIC(12, 6), 
	recorded_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id)
);

CREATE TABLE research_hypotheses (
	id UUID NOT NULL, 
	title TEXT NOT NULL, 
	description TEXT, 
	hypothesis_statement TEXT NOT NULL, 
	status TEXT NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	tested_at TIMESTAMP WITH TIME ZONE, 
	PRIMARY KEY (id), 
	CONSTRAINT ck_hypothesis_status CHECK (status IN ('proposed', 'testing', 'confirmed', 'refuted', 'inconclusive'))
);

CREATE TABLE research_publications (
	id UUID NOT NULL, 
	title TEXT NOT NULL, 
	description TEXT, 
	publication_type TEXT NOT NULL, 
	published_at TIMESTAMP WITH TIME ZONE, 
	is_authorised BOOLEAN NOT NULL, 
	authorisation_by TEXT, 
	PRIMARY KEY (id), 
	CONSTRAINT ck_publication_type CHECK (publication_type IN ('paper', 'article', 'report', 'software', 'dataset'))
);

CREATE TABLE resource_metrics (
	id UUID NOT NULL, 
	metric_name TEXT NOT NULL, 
	value NUMERIC(15, 4) NOT NULL, 
	unit TEXT, 
	recorded_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id)
);

CREATE TABLE retrieved_files (
	id UUID NOT NULL, 
	source_url TEXT NOT NULL, 
	filename TEXT, 
	content_type TEXT, 
	storage_path TEXT, 
	size_bytes INTEGER, 
	scan_status TEXT NOT NULL, 
	retrieved_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT ck_retrieved_file_scan CHECK (scan_status IN ('pending', 'clean', 'suspicious'))
);

CREATE TABLE routing_decisions (
	id UUID NOT NULL, 
	task_type TEXT NOT NULL, 
	required_capabilities JSON NOT NULL, 
	selected_provider TEXT NOT NULL, 
	selected_model TEXT NOT NULL, 
	reason TEXT, 
	fallback_used BOOLEAN NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id)
);

CREATE TABLE scam_detection_log (
	id UUID NOT NULL, 
	source TEXT NOT NULL, 
	content_summary TEXT NOT NULL, 
	risk_level TEXT NOT NULL, 
	indicators JSON NOT NULL, 
	action_taken TEXT, 
	detected_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT ck_scam_risk_level CHECK (risk_level IN ('low', 'medium', 'high', 'critical'))
);

CREATE TABLE scheduled_activities (
	id UUID NOT NULL, 
	name TEXT NOT NULL, 
	cron_expression TEXT, 
	next_run_at TIMESTAMP WITH TIME ZONE, 
	is_active BOOLEAN NOT NULL, 
	last_run_at TIMESTAMP WITH TIME ZONE, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id)
);

CREATE TABLE security_boundaries (
	id UUID NOT NULL, 
	boundary_name TEXT NOT NULL, 
	boundary_type TEXT NOT NULL, 
	description TEXT NOT NULL, 
	is_immutable BOOLEAN NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id)
);

CREATE TABLE security_engines (
	id UUID NOT NULL, 
	name TEXT NOT NULL, 
	provider TEXT NOT NULL, 
	transport TEXT NOT NULL, 
	base_url TEXT NOT NULL, 
	token_env_var TEXT NOT NULL, 
	enabled BOOLEAN NOT NULL, 
	dry_run BOOLEAN NOT NULL, 
	allow_private_network BOOLEAN NOT NULL, 
	allow_execution BOOLEAN NOT NULL, 
	allowed_scopes JSON NOT NULL, 
	created_by TEXT NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT ck_security_engine_provider CHECK (provider IN ('artex', 'generic')), 
	CONSTRAINT ck_security_engine_transport CHECK (transport IN ('mcp_streamable_http', 'http_api', 'stub')), 
	UNIQUE (name)
);

CREATE TABLE security_incidents (
	id UUID NOT NULL, 
	title TEXT NOT NULL, 
	description TEXT, 
	severity TEXT NOT NULL, 
	status TEXT NOT NULL, 
	reported_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	resolved_at TIMESTAMP WITH TIME ZONE, 
	PRIMARY KEY (id), 
	CONSTRAINT ck_incident_severity CHECK (severity IN ('low', 'medium', 'high', 'critical')), 
	CONSTRAINT ck_incident_status CHECK (status IN ('open', 'investigating', 'resolved', 'closed'))
);

CREATE TABLE skill_runtime_executions (
	id UUID NOT NULL, 
	skill_id TEXT NOT NULL, 
	permission TEXT NOT NULL, 
	script TEXT, 
	caller TEXT NOT NULL, 
	adapter TEXT NOT NULL, 
	status TEXT NOT NULL, 
	dry_run BOOLEAN NOT NULL, 
	result JSON NOT NULL, 
	error TEXT, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	completed_at TIMESTAMP WITH TIME ZONE, 
	PRIMARY KEY (id), 
	CONSTRAINT ck_skill_runtime_status CHECK (status IN ('completed', 'denied', 'failed'))
);

CREATE INDEX ix_skill_runtime_executions_skill_id ON skill_runtime_executions (skill_id);

CREATE TABLE skillforge_packages (
	id UUID NOT NULL, 
	skill_id TEXT NOT NULL, 
	name TEXT NOT NULL, 
	description TEXT, 
	origin TEXT NOT NULL, 
	provider TEXT, 
	category TEXT, 
	classification TEXT NOT NULL, 
	status TEXT NOT NULL, 
	version TEXT NOT NULL, 
	manifest JSON NOT NULL, 
	permissions JSON NOT NULL, 
	network_access BOOLEAN NOT NULL, 
	filesystem_access TEXT NOT NULL, 
	requires_creator_approval BOOLEAN NOT NULL, 
	path TEXT, 
	checksum TEXT, 
	created_by TEXT NOT NULL, 
	approved_by TEXT, 
	approved_at TIMESTAMP WITH TIME ZONE, 
	published_at TIMESTAMP WITH TIME ZONE, 
	activated_at TIMESTAMP WITH TIME ZONE, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT ck_skillforge_origin CHECK (origin IN ('native', 'imported')), 
	CONSTRAINT ck_skillforge_classification CHECK (classification IN ('personal', 'operational', 'sensitive', 'protected_core')), 
	CONSTRAINT ck_skillforge_status CHECK (status IN ('draft', 'testing', 'pending_approval', 'published', 'active', 'quarantined', 'archived')), 
	CONSTRAINT ck_skillforge_filesystem_access CHECK (filesystem_access IN ('none', 'scoped', 'full')), 
	CONSTRAINT ck_skillforge_provider CHECK (provider IS NULL OR provider IN ('openai', 'nvidia', 'google', 'anthropic', 'microsoft', 'community'))
);

CREATE UNIQUE INDEX ix_skillforge_packages_skill_id ON skillforge_packages (skill_id);

CREATE TABLE skills (
	id UUID NOT NULL, 
	name TEXT NOT NULL, 
	category TEXT, 
	proficiency_level INTEGER NOT NULL, 
	description TEXT, 
	acquired_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	last_practiced_at TIMESTAMP WITH TIME ZONE, 
	metadata JSON NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT ck_skill_proficiency_level CHECK (proficiency_level BETWEEN 0 AND 100)
);

CREATE TABLE social_profiles (
	id UUID NOT NULL, 
	entity_name TEXT NOT NULL, 
	entity_type TEXT NOT NULL, 
	relationship_type TEXT, 
	interaction_count INTEGER NOT NULL, 
	last_interaction_at TIMESTAMP WITH TIME ZONE, 
	preferences JSON NOT NULL, 
	notes TEXT, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id)
);

CREATE TABLE software_projects (
	id UUID NOT NULL, 
	name TEXT NOT NULL, 
	description TEXT, 
	status TEXT NOT NULL, 
	repository_url TEXT, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT ck_software_project_status CHECK (status IN ('planning', 'in_development', 'testing', 'deployed', 'archived'))
);

CREATE TABLE stored_objects (
	id UUID NOT NULL, 
	name TEXT NOT NULL, 
	s3_key TEXT NOT NULL, 
	bucket TEXT NOT NULL, 
	content_type TEXT NOT NULL, 
	size_bytes INTEGER NOT NULL, 
	sha256 TEXT NOT NULL, 
	owner TEXT NOT NULL, 
	is_approved_for_sharing BOOLEAN NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT ck_stored_object_size CHECK (size_bytes >= 0), 
	UNIQUE (s3_key)
);

CREATE TABLE tone_analyses (
	id UUID NOT NULL, 
	source_type TEXT NOT NULL, 
	content_summary TEXT NOT NULL, 
	tone TEXT NOT NULL, 
	register TEXT NOT NULL, 
	sentiment NUMERIC(3, 2) NOT NULL, 
	confidence NUMERIC(3, 2) NOT NULL, 
	signals JSON NOT NULL, 
	manipulation_indicators JSON NOT NULL, 
	interpretations JSON NOT NULL, 
	caveat TEXT NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT ck_tone_source_type CHECK (source_type IN ('message', 'article', 'post', 'comment', 'discussion', 'text')), 
	CONSTRAINT ck_tone_confidence CHECK (confidence BETWEEN 0 AND 1), 
	CONSTRAINT ck_tone_sentiment CHECK (sentiment BETWEEN -1 AND 1)
);

CREATE TABLE tool_registry (
	id UUID NOT NULL, 
	name TEXT NOT NULL, 
	description TEXT, 
	category TEXT, 
	parameters JSON NOT NULL, 
	is_active BOOLEAN NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (name)
);

CREATE TABLE upgrade_history (
	id UUID NOT NULL, 
	component TEXT NOT NULL, 
	previous_version TEXT, 
	new_version TEXT, 
	reason TEXT, 
	status TEXT NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT ck_upgrade_status CHECK (status IN ('pending', 'completed', 'rolled_back'))
);

CREATE TABLE visitor_rate_limits (
	id UUID NOT NULL, 
	visitor_id UUID, 
	scope_key TEXT NOT NULL, 
	window_start TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	request_count INTEGER NOT NULL, 
	is_blocked BOOLEAN NOT NULL, 
	PRIMARY KEY (id)
);

CREATE TABLE website_workflows (
	id UUID NOT NULL, 
	name TEXT NOT NULL, 
	url_pattern TEXT NOT NULL, 
	steps JSON NOT NULL, 
	verification JSON NOT NULL, 
	source_actor TEXT NOT NULL, 
	is_approved BOOLEAN NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id)
);

CREATE TABLE workflow_checkpoints (
	id UUID NOT NULL, 
	workflow_id TEXT NOT NULL, 
	step_name TEXT NOT NULL, 
	state JSON NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id)
);

CREATE TABLE world_entities (
	id UUID NOT NULL, 
	name TEXT NOT NULL, 
	entity_type TEXT NOT NULL, 
	description TEXT, 
	properties JSON NOT NULL, 
	confidence_level NUMERIC(3, 2) NOT NULL, 
	last_updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT ck_world_entity_confidence CHECK (confidence_level BETWEEN 0 AND 1), 
	CONSTRAINT ck_world_entity_type CHECK (entity_type IN ('person', 'organisation', 'country', 'technology', 'concept', 'event'))
);

CREATE TABLE world_events (
	id UUID NOT NULL, 
	event_type TEXT NOT NULL, 
	title TEXT NOT NULL, 
	description TEXT, 
	occurred_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	relevance_to_iam NUMERIC(3, 2) NOT NULL, 
	related_entity_ids JSON NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT ck_world_event_relevance CHECK (relevance_to_iam BETWEEN 0 AND 1)
);

CREATE TABLE agent_collaborations (
	id UUID NOT NULL, 
	agent_id UUID NOT NULL, 
	task_description TEXT NOT NULL, 
	task_type TEXT, 
	status TEXT NOT NULL, 
	result_summary TEXT, 
	requires_authorization BOOLEAN NOT NULL, 
	owner_authorized BOOLEAN NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	completed_at TIMESTAMP WITH TIME ZONE, 
	PRIMARY KEY (id), 
	CONSTRAINT ck_collaboration_status CHECK (status IN ('proposed', 'active', 'completed', 'failed', 'cancelled')), 
	FOREIGN KEY(agent_id) REFERENCES external_agents (id) ON DELETE CASCADE
);

CREATE TABLE agent_interactions (
	id UUID NOT NULL, 
	agent_id UUID NOT NULL, 
	direction TEXT NOT NULL, 
	request_summary TEXT NOT NULL, 
	response_summary TEXT, 
	success BOOLEAN, 
	risk_level TEXT NOT NULL, 
	validated BOOLEAN NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT ck_interaction_direction CHECK (direction IN ('outbound', 'inbound')), 
	CONSTRAINT ck_interaction_risk CHECK (risk_level IN ('low', 'medium', 'high')), 
	FOREIGN KEY(agent_id) REFERENCES external_agents (id) ON DELETE CASCADE
);

CREATE TABLE agent_interviews (
	id UUID NOT NULL, 
	agent_id UUID NOT NULL, 
	question TEXT NOT NULL, 
	answer TEXT, 
	provenance TEXT, 
	risk_level TEXT NOT NULL, 
	validated BOOLEAN NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT ck_interview_risk CHECK (risk_level IN ('low', 'medium', 'high')), 
	FOREIGN KEY(agent_id) REFERENCES external_agents (id) ON DELETE CASCADE
);

CREATE TABLE agent_trust_records (
	id UUID NOT NULL, 
	agent_id UUID NOT NULL, 
	assessment TEXT NOT NULL, 
	trust_delta NUMERIC(3, 2) NOT NULL, 
	evidence JSON NOT NULL, 
	recorded_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(agent_id) REFERENCES external_agents (id) ON DELETE CASCADE
);

CREATE TABLE ai_personality (
	id UUID NOT NULL, 
	identity_id UUID NOT NULL, 
	traits JSON NOT NULL, 
	tone TEXT, 
	formality_level INTEGER NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT ck_personality_formality_level CHECK (formality_level BETWEEN 1 AND 10), 
	FOREIGN KEY(identity_id) REFERENCES ai_identity (id) ON DELETE CASCADE
);

CREATE TABLE asset_licences (
	id UUID NOT NULL, 
	asset_id UUID NOT NULL, 
	licence_text TEXT, 
	licence_url TEXT, 
	granted_to TEXT, 
	granted_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(asset_id) REFERENCES digital_assets (id) ON DELETE CASCADE
);

CREATE TABLE assistant_adapters (
	id UUID NOT NULL, 
	assistant_id UUID NOT NULL, 
	name TEXT NOT NULL, 
	interface_type TEXT NOT NULL, 
	endpoint_template TEXT, 
	auth_method TEXT NOT NULL, 
	requires_credential BOOLEAN NOT NULL, 
	is_active BOOLEAN NOT NULL, 
	notes TEXT, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT ck_assistant_adapter_interface CHECK (interface_type IN ('official_skill', 'app_intents', 'shortcuts', 'automation_studio', 'official_api', 'documentation_only')), 
	FOREIGN KEY(assistant_id) REFERENCES assistant_systems (id) ON DELETE CASCADE
);

CREATE TABLE assistant_research_notes (
	id UUID NOT NULL, 
	assistant_id UUID NOT NULL, 
	topic TEXT NOT NULL, 
	observation TEXT NOT NULL, 
	source_url TEXT NOT NULL, 
	source_date TIMESTAMP WITH TIME ZONE, 
	confidence FLOAT NOT NULL, 
	status TEXT NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT ck_assistant_note_status CHECK (status IN ('observation', 'verified', 'uncertain')), 
	FOREIGN KEY(assistant_id) REFERENCES assistant_systems (id) ON DELETE CASCADE
);

CREATE INDEX ix_assistant_research_notes_assistant_id ON assistant_research_notes (assistant_id);

CREATE TABLE browser_actions (
	id UUID NOT NULL, 
	session_id UUID NOT NULL, 
	action_type TEXT NOT NULL, 
	target TEXT, 
	value TEXT, 
	result TEXT, 
	permission_required BOOLEAN NOT NULL, 
	authorized BOOLEAN NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT ck_browser_action_type CHECK (action_type IN ('navigate', 'click', 'type', 'submit', 'screenshot', 'scroll', 'text', 'links')), 
	FOREIGN KEY(session_id) REFERENCES internet_sessions (id) ON DELETE CASCADE
);

CREATE TABLE business_projects (
	id UUID NOT NULL, 
	name TEXT NOT NULL, 
	description TEXT, 
	opportunity_id UUID, 
	status TEXT NOT NULL, 
	revenue NUMERIC(15, 4) NOT NULL, 
	expenses NUMERIC(15, 4) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT ck_business_project_status CHECK (status IN ('planning', 'active', 'completed', 'paused', 'cancelled')), 
	FOREIGN KEY(opportunity_id) REFERENCES business_opportunities (id) ON DELETE SET NULL
);

CREATE TABLE capability_assessments (
	id UUID NOT NULL, 
	capability_id UUID NOT NULL, 
	proficiency_level INTEGER NOT NULL, 
	assessment_method TEXT NOT NULL, 
	evidence JSON NOT NULL, 
	assessed_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	assessor TEXT, 
	PRIMARY KEY (id), 
	CONSTRAINT ck_capability_assessment_level CHECK (proficiency_level BETWEEN 0 AND 100), 
	CONSTRAINT ck_capability_assessment_method CHECK (assessment_method IN ('test', 'project', 'simulation', 'review')), 
	FOREIGN KEY(capability_id) REFERENCES capability_definitions (id) ON DELETE CASCADE
);

CREATE TABLE capability_comparisons (
	id UUID NOT NULL, 
	assistant_id UUID NOT NULL, 
	capability TEXT NOT NULL, 
	rating INTEGER NOT NULL, 
	evidence_note TEXT NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT ck_capability_comparison_rating CHECK (rating BETWEEN 0 AND 5), 
	FOREIGN KEY(assistant_id) REFERENCES assistant_systems (id) ON DELETE CASCADE
);

CREATE TABLE code_changes (
	id UUID NOT NULL, 
	project_id UUID NOT NULL, 
	description TEXT, 
	file_path TEXT, 
	change_type TEXT, 
	status TEXT NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT ck_code_change_type CHECK (change_type IN ('add', 'modify', 'delete')), 
	CONSTRAINT ck_code_change_status CHECK (status IN ('proposed', 'reviewed', 'tested', 'deployed', 'rejected')), 
	FOREIGN KEY(project_id) REFERENCES software_projects (id) ON DELETE CASCADE
);

CREATE TABLE conversation_messages (
	id UUID NOT NULL, 
	conversation_id UUID NOT NULL, 
	role TEXT NOT NULL, 
	content TEXT NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	metadata JSON NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT ck_message_role CHECK (role IN ('user', 'assistant', 'system', 'tool')), 
	FOREIGN KEY(conversation_id) REFERENCES conversations (id) ON DELETE CASCADE
);

CREATE TABLE creator_approvals (
	id UUID NOT NULL, 
	request_id UUID NOT NULL, 
	decision TEXT NOT NULL, 
	signature TEXT NOT NULL, 
	signer_id TEXT NOT NULL, 
	verified_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT ck_creator_approval_decision CHECK (decision IN ('approved', 'rejected')), 
	FOREIGN KEY(request_id) REFERENCES creator_requests (id) ON DELETE CASCADE
);

CREATE TABLE creator_authorizations (
	id UUID NOT NULL, 
	action_type TEXT NOT NULL, 
	max_authority_level TEXT NOT NULL, 
	target_ref TEXT, 
	source_request_id UUID, 
	signer_id TEXT NOT NULL, 
	scope JSON NOT NULL, 
	is_active BOOLEAN NOT NULL, 
	granted_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	expires_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	revoked_at TIMESTAMP WITH TIME ZONE, 
	PRIMARY KEY (id), 
	CONSTRAINT ck_creator_auth_level CHECK (max_authority_level IN ('1', '2', '3', '4')), 
	FOREIGN KEY(source_request_id) REFERENCES creator_requests (id) ON DELETE SET NULL
);

CREATE INDEX ix_creator_authorizations_action_type ON creator_authorizations (action_type);

CREATE TABLE credential_references (
	id UUID NOT NULL, 
	integration_id UUID NOT NULL, 
	secret_name TEXT NOT NULL, 
	secret_store TEXT NOT NULL, 
	secret_path TEXT NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(integration_id) REFERENCES integration_registry (id) ON DELETE CASCADE
);

CREATE TABLE credential_rotations (
	id UUID NOT NULL, 
	integration_id UUID, 
	secret_name TEXT NOT NULL, 
	rotated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	next_rotation_due TIMESTAMP WITH TIME ZONE, 
	PRIMARY KEY (id), 
	FOREIGN KEY(integration_id) REFERENCES integration_registry (id) ON DELETE SET NULL
);

CREATE TABLE crypto_activities (
	id UUID NOT NULL, 
	transaction_id UUID, 
	blockchain TEXT, 
	asset TEXT, 
	amount NUMERIC(20, 8), 
	address TEXT, 
	tx_hash TEXT, 
	status TEXT NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(transaction_id) REFERENCES financial_transactions (id) ON DELETE SET NULL
);

CREATE TABLE deployment_records (
	id UUID NOT NULL, 
	project_id UUID NOT NULL, 
	version TEXT, 
	environment TEXT NOT NULL, 
	status TEXT NOT NULL, 
	deployed_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT ck_deployment_status CHECK (status IN ('pending', 'success', 'failed', 'rolled_back')), 
	FOREIGN KEY(project_id) REFERENCES software_projects (id) ON DELETE CASCADE
);

CREATE TABLE entity_relationships (
	id UUID NOT NULL, 
	source_entity_id UUID NOT NULL, 
	target_entity_id UUID NOT NULL, 
	relationship_type TEXT NOT NULL, 
	strength NUMERIC(3, 2) NOT NULL, 
	description TEXT, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT ck_entity_relationship_strength CHECK (strength BETWEEN 0 AND 1), 
	FOREIGN KEY(source_entity_id) REFERENCES world_entities (id) ON DELETE CASCADE, 
	FOREIGN KEY(target_entity_id) REFERENCES world_entities (id) ON DELETE CASCADE
);

CREATE TABLE financial_ledger (
	id UUID NOT NULL, 
	transaction_id UUID NOT NULL, 
	account TEXT NOT NULL, 
	debit_amount NUMERIC(15, 4) NOT NULL, 
	credit_amount NUMERIC(15, 4) NOT NULL, 
	recorded_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(transaction_id) REFERENCES financial_transactions (id) ON DELETE CASCADE
);

CREATE TABLE free_sandbox_environments (
	id UUID NOT NULL, 
	provider_id UUID NOT NULL, 
	external_id TEXT NOT NULL, 
	task_id TEXT NOT NULL, 
	capability TEXT NOT NULL, 
	state TEXT NOT NULL, 
	metadata JSON NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT ck_free_sandbox_environment_state CHECK (state IN ('discovered','registered','provisioning','running','stopped','completed','failed','deleted')), 
	FOREIGN KEY(provider_id) REFERENCES free_sandbox_providers (id) ON DELETE CASCADE
);

CREATE INDEX ix_free_sandbox_environments_task_id ON free_sandbox_environments (task_id);

CREATE INDEX ix_free_sandbox_environments_provider_id ON free_sandbox_environments (provider_id);

CREATE TABLE free_sandbox_quota_snapshots (
	id UUID NOT NULL, 
	provider_id UUID NOT NULL, 
	used_percent NUMERIC(5, 2), 
	remaining NUMERIC, 
	unit TEXT NOT NULL, 
	resets_at TIMESTAMP WITH TIME ZONE, 
	source_url TEXT, 
	verified_at TIMESTAMP WITH TIME ZONE, 
	captured_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(provider_id) REFERENCES free_sandbox_providers (id) ON DELETE CASCADE
);

CREATE INDEX ix_free_sandbox_quota_snapshots_provider_id ON free_sandbox_quota_snapshots (provider_id);

CREATE TABLE goal_lifecycles (
	id UUID NOT NULL, 
	goal_id UUID NOT NULL, 
	phase TEXT NOT NULL, 
	priority INTEGER NOT NULL, 
	last_reviewed_at TIMESTAMP WITH TIME ZONE, 
	next_review_at TIMESTAMP WITH TIME ZONE, 
	progress_percentage NUMERIC(5, 2) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT ck_goal_lifecycle_phase CHECK (phase IN ('planning', 'active', 'paused', 'completed', 'abandoned')), 
	CONSTRAINT ck_goal_lifecycle_priority CHECK (priority BETWEEN 1 AND 10), 
	CONSTRAINT ck_goal_lifecycle_progress CHECK (progress_percentage BETWEEN 0 AND 100), 
	FOREIGN KEY(goal_id) REFERENCES goals (id) ON DELETE CASCADE
);

CREATE TABLE identity_history (
	id UUID NOT NULL, 
	identity_id UUID NOT NULL, 
	change_type TEXT NOT NULL, 
	previous_value JSON, 
	new_value JSON, 
	changed_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	reason TEXT, 
	PRIMARY KEY (id), 
	FOREIGN KEY(identity_id) REFERENCES ai_identity (id) ON DELETE CASCADE
);

CREATE TABLE identity_matches (
	id UUID NOT NULL, 
	person_id UUID NOT NULL, 
	other_person_id UUID NOT NULL, 
	evidence JSON NOT NULL, 
	confidence FLOAT NOT NULL, 
	result TEXT NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT ck_identity_match_result CHECK (result IN ('same', 'uncertain', 'rejected')), 
	FOREIGN KEY(person_id) REFERENCES public_people (id) ON DELETE CASCADE, 
	FOREIGN KEY(other_person_id) REFERENCES public_people (id) ON DELETE CASCADE
);

CREATE TABLE integration_permissions (
	id UUID NOT NULL, 
	integration_id UUID NOT NULL, 
	permission_scope TEXT NOT NULL, 
	granted_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	expires_at TIMESTAMP WITH TIME ZONE, 
	revoked_at TIMESTAMP WITH TIME ZONE, 
	PRIMARY KEY (id), 
	FOREIGN KEY(integration_id) REFERENCES integration_registry (id) ON DELETE CASCADE
);

CREATE TABLE interaction_preferences (
	id UUID NOT NULL, 
	social_profile_id UUID NOT NULL, 
	preferred_channel TEXT, 
	preferred_time_of_day TEXT, 
	formality_level INTEGER NOT NULL, 
	communication_style TEXT, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(social_profile_id) REFERENCES social_profiles (id) ON DELETE CASCADE
);

CREATE TABLE ip_records (
	id UUID NOT NULL, 
	asset_id UUID NOT NULL, 
	ip_type TEXT NOT NULL, 
	registration_number TEXT, 
	registered_at TIMESTAMP WITH TIME ZONE, 
	owner_entity TEXT NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT ck_ip_type CHECK (ip_type IN ('copyright', 'trademark', 'patent', 'trade_secret')), 
	FOREIGN KEY(asset_id) REFERENCES digital_assets (id) ON DELETE CASCADE
);

CREATE TABLE knowledge_sources (
	id UUID NOT NULL, 
	knowledge_item_id UUID NOT NULL, 
	url TEXT, 
	title TEXT, 
	access_date TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	credibility_score NUMERIC(3, 2) NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT ck_source_credibility_score CHECK (credibility_score BETWEEN 0 AND 1), 
	FOREIGN KEY(knowledge_item_id) REFERENCES knowledge_items (id) ON DELETE CASCADE
);

CREATE TABLE learning_paths (
	id UUID NOT NULL, 
	capability_id UUID NOT NULL, 
	current_step INTEGER NOT NULL, 
	total_steps INTEGER NOT NULL, 
	steps JSON NOT NULL, 
	started_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	completed_at TIMESTAMP WITH TIME ZONE, 
	PRIMARY KEY (id), 
	FOREIGN KEY(capability_id) REFERENCES capability_definitions (id) ON DELETE CASCADE
);

CREATE TABLE legal_instruments (
	id UUID NOT NULL, 
	source_id UUID NOT NULL, 
	jurisdiction TEXT NOT NULL, 
	title TEXT NOT NULL, 
	authority_name TEXT NOT NULL, 
	instrument_type TEXT NOT NULL, 
	status TEXT NOT NULL, 
	official_url TEXT NOT NULL, 
	document_hash TEXT NOT NULL, 
	summary TEXT, 
	published_at TIMESTAMP WITH TIME ZONE, 
	effective_at TIMESTAMP WITH TIME ZONE, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT ck_legal_instrument_type CHECK (instrument_type IN ('constitution', 'legislation', 'regulation', 'court_judgment', 'guidance', 'policy', 'bill', 'draft_regulation', 'treaty', 'standard', 'announcement')), 
	CONSTRAINT ck_legal_instrument_status CHECK (status IN ('proposed', 'draft', 'enacted', 'guidance', 'announcement', 'repealed')), 
	FOREIGN KEY(source_id) REFERENCES legal_sources (id) ON DELETE RESTRICT
);

CREATE TABLE map_tile_cache (
	id UUID NOT NULL, 
	provider_id UUID NOT NULL, 
	tile_key TEXT NOT NULL, 
	content_hash TEXT NOT NULL, 
	size_bytes INTEGER NOT NULL, 
	fetched_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(provider_id) REFERENCES geo_providers (id) ON DELETE CASCADE
);

CREATE TABLE memory_embeddings (
	id UUID NOT NULL, 
	memory_item_id UUID NOT NULL, 
	embedding VECTOR(1536), 
	model TEXT, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(memory_item_id) REFERENCES memory_items (id) ON DELETE CASCADE
);

CREATE TABLE memory_relationships (
	id UUID NOT NULL, 
	source_memory_id UUID NOT NULL, 
	target_memory_id UUID NOT NULL, 
	relationship_type TEXT NOT NULL, 
	strength NUMERIC(3, 2) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(source_memory_id) REFERENCES memory_items (id) ON DELETE CASCADE, 
	FOREIGN KEY(target_memory_id) REFERENCES memory_items (id) ON DELETE CASCADE
);

CREATE TABLE model_evaluations (
	id UUID NOT NULL, 
	model_id UUID NOT NULL, 
	task_type TEXT, 
	score NUMERIC(5, 4), 
	details JSON NOT NULL, 
	evaluated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(model_id) REFERENCES model_registry (id) ON DELETE CASCADE
);

CREATE TABLE model_versions (
	id UUID NOT NULL, 
	model_id UUID NOT NULL, 
	version TEXT NOT NULL, 
	is_primary BOOLEAN NOT NULL, 
	deployed_at TIMESTAMP WITH TIME ZONE, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(model_id) REFERENCES model_registry (id) ON DELETE CASCADE
);

CREATE TABLE node_attestations (
	id UUID NOT NULL, 
	node_id UUID NOT NULL, 
	public_key TEXT NOT NULL, 
	core_hash TEXT NOT NULL, 
	platform_hash TEXT, 
	signature TEXT NOT NULL, 
	payload JSON NOT NULL, 
	verified BOOLEAN NOT NULL, 
	result TEXT NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT ck_node_attestation_result CHECK (result IN ('candidate', 'restricted', 'trusted', 'revoked')), 
	FOREIGN KEY(node_id) REFERENCES registered_nodes (id) ON DELETE CASCADE
);

CREATE INDEX ix_node_attestations_node_id ON node_attestations (node_id);

CREATE TABLE node_resource_reports (
	id UUID NOT NULL, 
	node_id UUID NOT NULL, 
	cpu_cores INTEGER NOT NULL, 
	ram_bytes FLOAT NOT NULL, 
	storage_bytes FLOAT NOT NULL, 
	used_percent FLOAT, 
	contribution_percent FLOAT NOT NULL, 
	permitted_ram_bytes FLOAT NOT NULL, 
	permitted_storage_bytes FLOAT NOT NULL, 
	reported_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(node_id) REFERENCES registered_nodes (id) ON DELETE CASCADE
);

CREATE INDEX ix_node_resource_reports_node_id ON node_resource_reports (node_id);

CREATE TABLE plans (
	id UUID NOT NULL, 
	goal_id UUID NOT NULL, 
	title TEXT NOT NULL, 
	steps JSON NOT NULL, 
	status TEXT NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT ck_plan_status CHECK (status IN ('pending', 'in_progress', 'completed', 'failed')), 
	FOREIGN KEY(goal_id) REFERENCES goals (id) ON DELETE CASCADE
);

CREATE TABLE public_profiles (
	id UUID NOT NULL, 
	person_id UUID NOT NULL, 
	source_name TEXT NOT NULL, 
	source_url TEXT NOT NULL, 
	source_domain TEXT NOT NULL, 
	profile_type TEXT NOT NULL, 
	stated_name TEXT, 
	role TEXT, 
	organization TEXT, 
	bio TEXT, 
	interests JSON NOT NULL, 
	status TEXT NOT NULL, 
	confidence FLOAT NOT NULL, 
	content_hash TEXT NOT NULL, 
	published_at TIMESTAMP WITH TIME ZONE, 
	retrieved_at TIMESTAMP WITH TIME ZONE, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT ck_public_profile_status CHECK (status IN ('verified','self_reported','uncertain','corrected')), 
	FOREIGN KEY(person_id) REFERENCES public_people (id) ON DELETE CASCADE
);

CREATE INDEX ix_public_profiles_person_id ON public_profiles (person_id);

CREATE TABLE public_records (
	id UUID NOT NULL, 
	source_id UUID NOT NULL, 
	category TEXT NOT NULL, 
	jurisdiction TEXT NOT NULL, 
	subject_name TEXT, 
	title TEXT NOT NULL, 
	published_at TIMESTAMP WITH TIME ZONE, 
	retrieved_at TIMESTAMP WITH TIME ZONE, 
	source_url TEXT NOT NULL, 
	content_hash TEXT NOT NULL, 
	facts JSON NOT NULL, 
	status TEXT NOT NULL, 
	confidence FLOAT NOT NULL, 
	legal_authority_reference TEXT, 
	is_statistical BOOLEAN NOT NULL, 
	is_correction BOOLEAN NOT NULL, 
	supersedes_id UUID, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT ck_public_record_status CHECK (status IN ('verified', 'self_reported', 'uncertain', 'allegation', 'restricted')), 
	CONSTRAINT ck_public_record_confidence CHECK (confidence >= 0 AND confidence <= 1), 
	FOREIGN KEY(source_id) REFERENCES public_sources (id) ON DELETE RESTRICT
);

CREATE TABLE public_relationships (
	id UUID NOT NULL, 
	person_id UUID NOT NULL, 
	related_person_id UUID, 
	organization_name TEXT, 
	relationship_type TEXT NOT NULL, 
	evidence JSON NOT NULL, 
	confidence FLOAT NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(person_id) REFERENCES public_people (id) ON DELETE CASCADE
);

CREATE TABLE research_experiments (
	id UUID NOT NULL, 
	hypothesis_id UUID NOT NULL, 
	title TEXT NOT NULL, 
	methodology TEXT, 
	status TEXT NOT NULL, 
	started_at TIMESTAMP WITH TIME ZONE, 
	completed_at TIMESTAMP WITH TIME ZONE, 
	PRIMARY KEY (id), 
	CONSTRAINT ck_experiment_status CHECK (status IN ('planned', 'running', 'completed', 'failed')), 
	FOREIGN KEY(hypothesis_id) REFERENCES research_hypotheses (id) ON DELETE CASCADE
);

CREATE TABLE security_engine_scopes (
	id UUID NOT NULL, 
	engine_id UUID NOT NULL, 
	target TEXT NOT NULL, 
	target_type TEXT NOT NULL, 
	description TEXT, 
	authorization_id TEXT, 
	authorized_by TEXT NOT NULL, 
	allow_write BOOLEAN NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(engine_id) REFERENCES security_engines (id) ON DELETE CASCADE
);

CREATE TABLE signed_challenges (
	id UUID NOT NULL, 
	request_id UUID NOT NULL, 
	nonce TEXT NOT NULL, 
	payload JSON NOT NULL, 
	payload_hash TEXT NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	expires_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	consumed_at TIMESTAMP WITH TIME ZONE, 
	PRIMARY KEY (id), 
	FOREIGN KEY(request_id) REFERENCES creator_requests (id) ON DELETE CASCADE, 
	UNIQUE (nonce)
);

CREATE TABLE skill_runtime_logs (
	id UUID NOT NULL, 
	execution_id UUID NOT NULL, 
	stream TEXT NOT NULL, 
	content TEXT NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(execution_id) REFERENCES skill_runtime_executions (id) ON DELETE CASCADE
);

CREATE TABLE skillforge_audit_events (
	id UUID NOT NULL, 
	package_id UUID, 
	action TEXT NOT NULL, 
	actor TEXT NOT NULL, 
	details JSON NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(package_id) REFERENCES skillforge_packages (id) ON DELETE CASCADE
);

CREATE TABLE skillforge_permission_grants (
	id UUID NOT NULL, 
	package_id UUID NOT NULL, 
	permission TEXT NOT NULL, 
	granted_by TEXT NOT NULL, 
	reason TEXT, 
	is_active BOOLEAN NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(package_id) REFERENCES skillforge_packages (id) ON DELETE CASCADE
);

CREATE TABLE skillforge_test_results (
	id UUID NOT NULL, 
	package_id UUID NOT NULL, 
	version TEXT NOT NULL, 
	test_type TEXT NOT NULL, 
	passed BOOLEAN NOT NULL, 
	details JSON NOT NULL, 
	executed_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(package_id) REFERENCES skillforge_packages (id) ON DELETE CASCADE
);

CREATE TABLE skillforge_versions (
	id UUID NOT NULL, 
	package_id UUID NOT NULL, 
	version TEXT NOT NULL, 
	manifest JSON NOT NULL, 
	permissions JSON NOT NULL, 
	checksum TEXT, 
	change_note TEXT, 
	is_current BOOLEAN NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT ck_skillforge_version_semver CHECK (version ~ '^[0-9]+\.[0-9]+\.[0-9]+$'), 
	FOREIGN KEY(package_id) REFERENCES skillforge_packages (id) ON DELETE CASCADE
);

CREATE TABLE sync_objects (
	id UUID NOT NULL, 
	publisher_node_id UUID NOT NULL, 
	object_type TEXT NOT NULL, 
	content_hash TEXT NOT NULL, 
	payload JSON NOT NULL, 
	signature TEXT NOT NULL, 
	verified BOOLEAN NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(publisher_node_id) REFERENCES registered_nodes (id) ON DELETE CASCADE
);

CREATE INDEX ix_sync_objects_publisher_node_id ON sync_objects (publisher_node_id);

CREATE INDEX ix_sync_objects_content_hash ON sync_objects (content_hash);

CREATE TABLE tool_permissions (
	id UUID NOT NULL, 
	tool_id UUID NOT NULL, 
	permission_level TEXT NOT NULL, 
	requires_human_approval BOOLEAN NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT ck_tool_permission_level CHECK (permission_level IN ('autonomous', 'authorized', 'explicit', 'blocked')), 
	FOREIGN KEY(tool_id) REFERENCES tool_registry (id) ON DELETE CASCADE
);

CREATE TABLE visitor_consents (
	id UUID NOT NULL, 
	visitor_id UUID NOT NULL, 
	consent_type TEXT NOT NULL, 
	granted BOOLEAN NOT NULL, 
	retention_days INTEGER, 
	recorded_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(visitor_id) REFERENCES anonymous_visitors (id) ON DELETE CASCADE
);

CREATE TABLE visitor_memory_permissions (
	id UUID NOT NULL, 
	visitor_id UUID NOT NULL, 
	allow_session_memory BOOLEAN NOT NULL, 
	allow_anonymous_memory BOOLEAN NOT NULL, 
	allow_shared_knowledge BOOLEAN NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(visitor_id) REFERENCES anonymous_visitors (id) ON DELETE CASCADE
);

CREATE TABLE visitor_preferences (
	id UUID NOT NULL, 
	visitor_id UUID NOT NULL, 
	key TEXT NOT NULL, 
	value JSON NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(visitor_id) REFERENCES anonymous_visitors (id) ON DELETE CASCADE
);

CREATE TABLE visitor_sessions (
	id UUID NOT NULL, 
	visitor_id UUID NOT NULL, 
	session_token VARCHAR(64) NOT NULL, 
	started_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	last_activity_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	ended_at TIMESTAMP WITH TIME ZONE, 
	mode VARCHAR(16) NOT NULL, 
	is_active BOOLEAN NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT ck_session_mode CHECK (mode IN ('focus', 'recall', 'create')), 
	FOREIGN KEY(visitor_id) REFERENCES anonymous_visitors (id) ON DELETE CASCADE
);

CREATE UNIQUE INDEX ix_visitor_sessions_session_token ON visitor_sessions (session_token);

CREATE TABLE business_budgets (
	id UUID NOT NULL, 
	business_project_id UUID NOT NULL, 
	category TEXT NOT NULL, 
	amount NUMERIC(15, 4) NOT NULL, 
	period TEXT NOT NULL, 
	is_approved BOOLEAN NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT ck_business_budget_amount CHECK (amount >= 0), 
	FOREIGN KEY(business_project_id) REFERENCES business_projects (id) ON DELETE CASCADE
);

CREATE TABLE business_performance (
	id UUID NOT NULL, 
	project_id UUID NOT NULL, 
	period TEXT NOT NULL, 
	revenue NUMERIC(15, 4) NOT NULL, 
	expenses NUMERIC(15, 4) NOT NULL, 
	profit NUMERIC(15, 4) NOT NULL, 
	recorded_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(project_id) REFERENCES business_projects (id) ON DELETE CASCADE
);

CREATE TABLE business_reports (
	id UUID NOT NULL, 
	business_project_id UUID NOT NULL, 
	report_type TEXT NOT NULL, 
	title TEXT NOT NULL, 
	content TEXT NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	is_approved BOOLEAN NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT ck_business_report_type CHECK (report_type IN ('plan', 'performance', 'review', 'closure')), 
	FOREIGN KEY(business_project_id) REFERENCES business_projects (id) ON DELETE CASCADE
);

CREATE TABLE conversation_threads (
	id UUID NOT NULL, 
	session_id UUID NOT NULL, 
	title TEXT, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(session_id) REFERENCES visitor_sessions (id) ON DELETE CASCADE
);

CREATE TABLE customers (
	id UUID NOT NULL, 
	business_project_id UUID NOT NULL, 
	name TEXT NOT NULL, 
	email TEXT, 
	company TEXT, 
	total_spent NUMERIC(15, 4) NOT NULL, 
	customer_since TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	last_purchase_at TIMESTAMP WITH TIME ZONE, 
	PRIMARY KEY (id), 
	CONSTRAINT ck_customer_total_spent CHECK (total_spent >= 0), 
	FOREIGN KEY(business_project_id) REFERENCES business_projects (id) ON DELETE CASCADE
);

CREATE TABLE experiment_results (
	id UUID NOT NULL, 
	experiment_id UUID NOT NULL, 
	outcome TEXT NOT NULL, 
	success BOOLEAN NOT NULL, 
	data JSON NOT NULL, 
	recorded_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	reproducible BOOLEAN NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(experiment_id) REFERENCES research_experiments (id) ON DELETE CASCADE
);

CREATE TABLE free_sandbox_results (
	id UUID NOT NULL, 
	environment_id UUID NOT NULL, 
	payload JSON NOT NULL, 
	artifacts JSON NOT NULL, 
	error TEXT, 
	collected_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(environment_id) REFERENCES free_sandbox_environments (id) ON DELETE CASCADE
);

CREATE INDEX ix_free_sandbox_results_environment_id ON free_sandbox_results (environment_id);

CREATE TABLE legal_changes (
	id UUID NOT NULL, 
	instrument_id UUID NOT NULL, 
	change_type TEXT NOT NULL, 
	severity TEXT NOT NULL, 
	lifecycle_stage TEXT NOT NULL, 
	authenticated BOOLEAN NOT NULL, 
	evidence JSON NOT NULL, 
	creator_approval_reference TEXT, 
	professional_review_reference TEXT, 
	implemented_at TIMESTAMP WITH TIME ZONE, 
	verified_at TIMESTAMP WITH TIME ZONE, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT ck_legal_change_type CHECK (change_type IN ('new', 'amendment', 'repeal', 'correction')), 
	CONSTRAINT ck_legal_change_severity CHECK (severity IN ('critical', 'important', 'informational')), 
	CONSTRAINT ck_legal_change_stage CHECK (lifecycle_stage IN ('discover','authenticate','understand','assess','recommend','authorise','implement','verify')), 
	FOREIGN KEY(instrument_id) REFERENCES legal_instruments (id) ON DELETE CASCADE
);

CREATE INDEX ix_legal_changes_instrument_id ON legal_changes (instrument_id);

CREATE TABLE legal_versions (
	id UUID NOT NULL, 
	instrument_id UUID NOT NULL, 
	version_label TEXT NOT NULL, 
	document_hash TEXT NOT NULL, 
	content JSON NOT NULL, 
	valid_from TIMESTAMP WITH TIME ZONE, 
	valid_to TIMESTAMP WITH TIME ZONE, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(instrument_id) REFERENCES legal_instruments (id) ON DELETE CASCADE
);

CREATE INDEX ix_legal_versions_instrument_id ON legal_versions (instrument_id);

CREATE TABLE presence_claims (
	id UUID NOT NULL, 
	person_id UUID NOT NULL, 
	profile_id UUID, 
	claim_type TEXT NOT NULL, 
	value JSON NOT NULL, 
	status TEXT NOT NULL, 
	confidence FLOAT NOT NULL, 
	source_url TEXT, 
	first_seen_at TIMESTAMP WITH TIME ZONE, 
	last_seen_at TIMESTAMP WITH TIME ZONE, 
	supersedes_id UUID, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT ck_presence_claim_confidence CHECK (confidence BETWEEN 0 AND 1), 
	FOREIGN KEY(person_id) REFERENCES public_people (id) ON DELETE CASCADE, 
	FOREIGN KEY(profile_id) REFERENCES public_profiles (id) ON DELETE SET NULL
);

CREATE INDEX ix_presence_claims_person_id ON presence_claims (person_id);

CREATE TABLE record_relationships (
	id UUID NOT NULL, 
	from_record_id UUID NOT NULL, 
	to_record_id UUID NOT NULL, 
	relation_type TEXT NOT NULL, 
	evidence JSON NOT NULL, 
	confidence FLOAT NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT ck_record_relationship_type CHECK (relation_type IN ('same_entity', 'related_entity', 'conflict', 'correction')), 
	CONSTRAINT ck_record_relationship_confidence CHECK (confidence >= 0 AND confidence <= 1), 
	FOREIGN KEY(from_record_id) REFERENCES public_records (id) ON DELETE CASCADE, 
	FOREIGN KEY(to_record_id) REFERENCES public_records (id) ON DELETE CASCADE
);

CREATE TABLE request_jobs (
	id UUID NOT NULL, 
	session_id UUID, 
	status TEXT NOT NULL, 
	mode TEXT, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	started_at TIMESTAMP WITH TIME ZONE, 
	completed_at TIMESTAMP WITH TIME ZONE, 
	PRIMARY KEY (id), 
	CONSTRAINT ck_request_job_status CHECK (status IN ('queued', 'running', 'completed', 'failed')), 
	FOREIGN KEY(session_id) REFERENCES visitor_sessions (id) ON DELETE SET NULL
);

CREATE TABLE security_engine_tasks (
	id UUID NOT NULL, 
	engine_id UUID NOT NULL, 
	scope_id UUID, 
	parent_task_id UUID, 
	target TEXT NOT NULL, 
	operation TEXT NOT NULL, 
	description TEXT NOT NULL, 
	risk_level TEXT NOT NULL, 
	status TEXT NOT NULL, 
	created_by TEXT NOT NULL, 
	approved_by TEXT, 
	approved_at TIMESTAMP WITH TIME ZONE, 
	external_task_id TEXT, 
	metadata JSON NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	started_at TIMESTAMP WITH TIME ZONE, 
	completed_at TIMESTAMP WITH TIME ZONE, 
	PRIMARY KEY (id), 
	CONSTRAINT ck_security_task_status CHECK (status IN ('pending_approval', 'authorized', 'dispatched', 'running', 'completed', 'failed', 'cancelled', 'rejected')), 
	CONSTRAINT ck_security_task_risk CHECK (risk_level IN ('personal', 'operational', 'sensitive', 'protected_core')), 
	FOREIGN KEY(engine_id) REFERENCES security_engines (id) ON DELETE CASCADE, 
	FOREIGN KEY(scope_id) REFERENCES security_engine_scopes (id) ON DELETE SET NULL, 
	FOREIGN KEY(parent_task_id) REFERENCES security_engine_tasks (id) ON DELETE SET NULL
);

CREATE TABLE tasks (
	id UUID NOT NULL, 
	plan_id UUID, 
	title TEXT NOT NULL, 
	description TEXT, 
	status TEXT NOT NULL, 
	tool_used TEXT, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	started_at TIMESTAMP WITH TIME ZONE, 
	completed_at TIMESTAMP WITH TIME ZONE, 
	PRIMARY KEY (id), 
	CONSTRAINT ck_task_status CHECK (status IN ('pending', 'in_progress', 'completed', 'failed', 'blocked')), 
	FOREIGN KEY(plan_id) REFERENCES plans (id) ON DELETE SET NULL
);

CREATE TABLE visitor_locations (
	id UUID NOT NULL, 
	session_id UUID NOT NULL, 
	country TEXT, 
	region TEXT, 
	city TEXT, 
	language TEXT, 
	timezone TEXT, 
	currency TEXT, 
	is_estimate BOOLEAN NOT NULL, 
	user_corrected BOOLEAN NOT NULL, 
	resolved_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(session_id) REFERENCES visitor_sessions (id) ON DELETE CASCADE
);

CREATE TABLE legal_impacts (
	id UUID NOT NULL, 
	change_id UUID NOT NULL, 
	affected_system TEXT NOT NULL, 
	assessment TEXT NOT NULL, 
	risk_level TEXT NOT NULL, 
	recommendation TEXT NOT NULL, 
	obligations JSON NOT NULL, 
	evidence JSON NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT ck_legal_impact_risk_level CHECK (risk_level IN ('low', 'medium', 'high', 'critical')), 
	FOREIGN KEY(change_id) REFERENCES legal_changes (id) ON DELETE CASCADE
);

CREATE INDEX ix_legal_impacts_change_id ON legal_impacts (change_id);

CREATE TABLE sales_records (
	id UUID NOT NULL, 
	business_project_id UUID NOT NULL, 
	customer_id UUID, 
	amount NUMERIC(15, 4) NOT NULL, 
	currency TEXT NOT NULL, 
	product_or_service TEXT NOT NULL, 
	sold_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT ck_sales_amount CHECK (amount > 0), 
	FOREIGN KEY(business_project_id) REFERENCES business_projects (id) ON DELETE CASCADE, 
	FOREIGN KEY(customer_id) REFERENCES customers (id) ON DELETE SET NULL
);

CREATE TABLE security_engine_audit (
	id UUID NOT NULL, 
	engine_id UUID, 
	task_id UUID, 
	action TEXT NOT NULL, 
	actor TEXT NOT NULL, 
	details JSON NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(engine_id) REFERENCES security_engines (id) ON DELETE SET NULL, 
	FOREIGN KEY(task_id) REFERENCES security_engine_tasks (id) ON DELETE SET NULL
);

CREATE TABLE security_findings (
	id UUID NOT NULL, 
	task_id UUID NOT NULL, 
	external_id TEXT, 
	title TEXT NOT NULL, 
	severity TEXT NOT NULL, 
	description TEXT, 
	evidence JSON NOT NULL, 
	raw JSON NOT NULL, 
	remediation TEXT, 
	verified BOOLEAN NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(task_id) REFERENCES security_engine_tasks (id) ON DELETE CASCADE
);

CREATE TABLE task_executions (
	id UUID NOT NULL, 
	task_id UUID NOT NULL, 
	status TEXT NOT NULL, 
	output TEXT, 
	error_message TEXT, 
	duration_ms INTEGER, 
	executed_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT ck_task_execution_status CHECK (status IN ('success', 'failure', 'partial')), 
	FOREIGN KEY(task_id) REFERENCES tasks (id) ON DELETE CASCADE
);

CREATE TABLE visitor_messages (
	id UUID NOT NULL, 
	thread_id UUID NOT NULL, 
	role TEXT NOT NULL, 
	content TEXT NOT NULL, 
	mode TEXT, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	metadata JSON NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT ck_visitor_message_role CHECK (role IN ('user', 'assistant', 'system', 'tool')), 
	FOREIGN KEY(thread_id) REFERENCES conversation_threads (id) ON DELETE CASCADE
);
