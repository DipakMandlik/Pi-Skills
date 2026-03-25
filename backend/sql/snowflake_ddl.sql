/*
 * pi-optimized canonical Snowflake DDL
 * Security-aligned schema for backend + MCP session revocation model.
 */

USE ROLE SYSADMIN;

CREATE DATABASE IF NOT EXISTS PI_OPTIMIZED;
CREATE SCHEMA IF NOT EXISTS PI_OPTIMIZED.APP;
CREATE SCHEMA IF NOT EXISTS PI_OPTIMIZED.AUDIT;
CREATE SCHEMA IF NOT EXISTS PI_OPTIMIZED.ANALYTICS;

CREATE WAREHOUSE IF NOT EXISTS PI_APP_WH
  WAREHOUSE_SIZE = 'X-SMALL'
  AUTO_SUSPEND = 60
  AUTO_RESUME = TRUE
  MIN_CLUSTER_COUNT = 1
  MAX_CLUSTER_COUNT = 2
  SCALING_POLICY = 'STANDARD';

CREATE WAREHOUSE IF NOT EXISTS PI_ANALYTICS_WH
  WAREHOUSE_SIZE = 'SMALL'
  AUTO_SUSPEND = 300
  AUTO_RESUME = TRUE
  MIN_CLUSTER_COUNT = 1
  MAX_CLUSTER_COUNT = 3
  SCALING_POLICY = 'STANDARD';

USE DATABASE PI_OPTIMIZED;
USE SCHEMA APP;

CREATE TABLE IF NOT EXISTS users (
  id STRING NOT NULL,
  external_id STRING NOT NULL,
  email STRING NOT NULL,
  display_name STRING,
  platform_role STRING NOT NULL DEFAULT 'VIEWER',
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  password_hash STRING NOT NULL,
  created_at TIMESTAMP_NTZ NOT NULL DEFAULT CURRENT_TIMESTAMP(),
  last_login_at TIMESTAMP_NTZ,
  metadata VARIANT DEFAULT OBJECT_CONSTRUCT(),
  CONSTRAINT pk_users PRIMARY KEY (id),
  CONSTRAINT uq_users_external_id UNIQUE (external_id),
  CONSTRAINT uq_users_email UNIQUE (email)
);

CREATE TABLE IF NOT EXISTS registered_models (
  model_id STRING NOT NULL,
  display_name STRING NOT NULL,
  provider STRING NOT NULL,
  tier STRING DEFAULT 'standard',
  is_available BOOLEAN NOT NULL DEFAULT TRUE,
  max_tokens NUMBER,
  cost_per_1k_tokens FLOAT NOT NULL DEFAULT 0.0,
  created_at TIMESTAMP_NTZ NOT NULL DEFAULT CURRENT_TIMESTAMP(),
  CONSTRAINT pk_registered_models PRIMARY KEY (model_id)
);

CREATE TABLE IF NOT EXISTS model_permissions (
  id STRING NOT NULL,
  user_id STRING NOT NULL,
  model_id STRING NOT NULL,
  granted_by STRING NOT NULL,
  granted_at TIMESTAMP_NTZ NOT NULL DEFAULT CURRENT_TIMESTAMP(),
  expires_at TIMESTAMP_NTZ,
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  revoked_by STRING,
  revoked_at TIMESTAMP_NTZ,
  notes STRING,
  CONSTRAINT pk_model_permissions PRIMARY KEY (id),
  CONSTRAINT uq_model_permissions_user_model UNIQUE (user_id, model_id)
);

CREATE TABLE IF NOT EXISTS skill_assignments (
  id STRING NOT NULL,
  user_id STRING NOT NULL,
  skill_id STRING NOT NULL,
  assigned_by STRING NOT NULL,
  assigned_at TIMESTAMP_NTZ NOT NULL DEFAULT CURRENT_TIMESTAMP(),
  expires_at TIMESTAMP_NTZ,
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  revoked_by STRING,
  revoked_at TIMESTAMP_NTZ,
  CONSTRAINT pk_skill_assignments PRIMARY KEY (id),
  CONSTRAINT uq_skill_assignments_user_skill UNIQUE (user_id, skill_id)
);

CREATE TABLE IF NOT EXISTS subscriptions (
  plan_name STRING NOT NULL,
  display_name STRING NOT NULL,
  monthly_token_limit NUMBER NOT NULL,
  max_tokens_per_request NUMBER NOT NULL DEFAULT 4096,
  allowed_models VARIANT NOT NULL DEFAULT ARRAY_CONSTRUCT(),
  features VARIANT NOT NULL DEFAULT ARRAY_CONSTRUCT(),
  priority STRING NOT NULL DEFAULT 'standard',
  rate_limit_per_minute NUMBER NOT NULL DEFAULT 60,
  cost_budget_monthly FLOAT NOT NULL DEFAULT 0.0,
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMP_NTZ NOT NULL DEFAULT CURRENT_TIMESTAMP(),
  updated_at TIMESTAMP_NTZ NOT NULL DEFAULT CURRENT_TIMESTAMP(),
  CONSTRAINT pk_subscriptions PRIMARY KEY (plan_name)
);

CREATE TABLE IF NOT EXISTS user_subscriptions (
  id STRING NOT NULL,
  user_id STRING NOT NULL,
  plan_name STRING NOT NULL,
  assigned_at TIMESTAMP_NTZ NOT NULL DEFAULT CURRENT_TIMESTAMP(),
  assigned_by STRING,
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  CONSTRAINT pk_user_subscriptions PRIMARY KEY (id),
  CONSTRAINT uq_user_subscriptions_user UNIQUE (user_id)
);

CREATE TABLE IF NOT EXISTS user_tokens (
  id STRING NOT NULL,
  user_id STRING NOT NULL,
  period STRING NOT NULL,
  tokens_used NUMBER NOT NULL DEFAULT 0,
  tokens_limit NUMBER NOT NULL,
  cost_accumulated FLOAT NOT NULL DEFAULT 0.0,
  last_reset TIMESTAMP_NTZ NOT NULL DEFAULT CURRENT_TIMESTAMP(),
  CONSTRAINT pk_user_tokens PRIMARY KEY (id),
  CONSTRAINT uq_user_tokens_user_period UNIQUE (user_id, period)
);

CREATE TABLE IF NOT EXISTS token_usage_log (
  id STRING NOT NULL,
  user_id STRING NOT NULL,
  model_id STRING NOT NULL,
  skill_id STRING,
  tokens_used NUMBER NOT NULL,
  cost FLOAT NOT NULL DEFAULT 0.0,
  request_id STRING,
  latency_ms NUMBER,
  outcome STRING NOT NULL DEFAULT 'SUCCESS',
  timestamp TIMESTAMP_NTZ NOT NULL DEFAULT CURRENT_TIMESTAMP(),
  CONSTRAINT pk_token_usage_log PRIMARY KEY (id)
);

CREATE TABLE IF NOT EXISTS model_access_control (
  model_id STRING NOT NULL,
  allowed_roles VARIANT NOT NULL DEFAULT ARRAY_CONSTRUCT(),
  max_tokens_per_request NUMBER NOT NULL DEFAULT 4096,
  enabled BOOLEAN NOT NULL DEFAULT TRUE,
  rate_limit_per_minute NUMBER DEFAULT 60,
  created_at TIMESTAMP_NTZ NOT NULL DEFAULT CURRENT_TIMESTAMP(),
  updated_at TIMESTAMP_NTZ NOT NULL DEFAULT CURRENT_TIMESTAMP(),
  CONSTRAINT pk_model_access_control PRIMARY KEY (model_id)
);

CREATE TABLE IF NOT EXISTS feature_flags (
  id STRING NOT NULL,
  feature_name STRING NOT NULL,
  model_id STRING NOT NULL,
  enabled_for VARIANT NOT NULL DEFAULT ARRAY_CONSTRUCT(),
  enabled BOOLEAN NOT NULL DEFAULT TRUE,
  config VARIANT NOT NULL DEFAULT OBJECT_CONSTRUCT(),
  created_at TIMESTAMP_NTZ NOT NULL DEFAULT CURRENT_TIMESTAMP(),
  updated_at TIMESTAMP_NTZ NOT NULL DEFAULT CURRENT_TIMESTAMP(),
  CONSTRAINT pk_feature_flags PRIMARY KEY (id),
  CONSTRAINT uq_feature_flags_feature_model UNIQUE (feature_name, model_id)
);

CREATE TABLE IF NOT EXISTS cost_tracking (
  id STRING NOT NULL,
  user_id STRING NOT NULL,
  period STRING NOT NULL,
  model_id STRING NOT NULL,
  tokens_used NUMBER NOT NULL,
  cost FLOAT NOT NULL,
  recorded_at TIMESTAMP_NTZ NOT NULL DEFAULT CURRENT_TIMESTAMP(),
  CONSTRAINT pk_cost_tracking PRIMARY KEY (id)
);

USE SCHEMA AUDIT;

CREATE TABLE IF NOT EXISTS audit_log (
  id STRING NOT NULL,
  request_id STRING NOT NULL,
  user_id STRING,
  skill_id STRING,
  model_id STRING,
  action STRING NOT NULL,
  outcome STRING NOT NULL,
  tokens_used NUMBER,
  latency_ms NUMBER,
  ip_address STRING,
  user_agent STRING,
  error_detail STRING,
  metadata VARIANT NOT NULL DEFAULT OBJECT_CONSTRUCT(),
  timestamp TIMESTAMP_NTZ NOT NULL DEFAULT CURRENT_TIMESTAMP(),
  CONSTRAINT pk_audit_log PRIMARY KEY (id)
);

USE SCHEMA APP;

CREATE TABLE IF NOT EXISTS mcp_sessions (
  session_id STRING NOT NULL,
  user_id STRING NOT NULL,
  access_token_hash STRING NOT NULL,
  refresh_token_hash STRING NOT NULL,
  parent_session_id STRING,
  is_revoked BOOLEAN NOT NULL DEFAULT FALSE,
  revoked_at TIMESTAMP_NTZ,
  expires_at TIMESTAMP_NTZ NOT NULL,
  created_at TIMESTAMP_NTZ NOT NULL DEFAULT CURRENT_TIMESTAMP(),
  updated_at TIMESTAMP_NTZ NOT NULL DEFAULT CURRENT_TIMESTAMP(),
  CONSTRAINT pk_mcp_sessions PRIMARY KEY (session_id),
  CONSTRAINT uq_mcp_sessions_access_hash UNIQUE (access_token_hash),
  CONSTRAINT uq_mcp_sessions_refresh_hash UNIQUE (refresh_token_hash)
);

-- Search optimization for revocation and lookup paths.
ALTER TABLE IF EXISTS APP.mcp_sessions
  ADD SEARCH OPTIMIZATION ON EQUALITY(access_token_hash, refresh_token_hash, user_id, parent_session_id);

ALTER TABLE IF EXISTS AUDIT.audit_log
  ADD SEARCH OPTIMIZATION ON EQUALITY(user_id, request_id, action, outcome);
