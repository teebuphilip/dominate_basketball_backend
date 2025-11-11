-- NBA Fantasy Basketball Platform - Main Database Schema
-- Multi-tenant SaaS architecture with complete authentication and projections

-- ==========================================
-- CUSTOMERS TABLE (Multi-tenant isolation)
-- ==========================================
CREATE TABLE IF NOT EXISTS customers (
    customer_id VARCHAR(100) PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    company_name VARCHAR(255),
    tier VARCHAR(20) NOT NULL DEFAULT 'free' CHECK (tier IN ('free', 'pro', 'enterprise')),
    
    -- Account settings
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    
    -- Billing
    billing_email VARCHAR(255),
    stripe_customer_id VARCHAR(100),
    subscription_status VARCHAR(20) DEFAULT 'active',
    
    -- Features & limits
    custom_override_limit INTEGER DEFAULT 0,
    can_access_current_season BOOLEAN DEFAULT FALSE,
    can_train_models BOOLEAN DEFAULT FALSE
);

CREATE INDEX idx_customers_email ON customers(email);
CREATE INDEX idx_customers_tier ON customers(tier);
CREATE INDEX idx_customers_active ON customers(is_active);

-- ==========================================
-- API KEYS TABLE (Authentication)
-- ==========================================
CREATE TABLE IF NOT EXISTS api_keys (
    key_id SERIAL PRIMARY KEY,
    customer_id VARCHAR(100) NOT NULL,
    api_key VARCHAR(100) UNIQUE NOT NULL,
    key_name VARCHAR(100),
    
    -- Rate limiting
    rate_limit_per_hour INTEGER DEFAULT 100,
    requests_used_this_hour INTEGER DEFAULT 0,
    rate_limit_reset_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Status
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_used_at TIMESTAMP,
    expires_at TIMESTAMP,
    
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id) ON DELETE CASCADE
);

CREATE INDEX idx_api_keys_key ON api_keys(api_key);
CREATE INDEX idx_api_keys_customer ON api_keys(customer_id);
CREATE INDEX idx_api_keys_active ON api_keys(is_active);

-- ==========================================
-- NBA PLAYERS TABLE
-- ==========================================
CREATE TABLE IF NOT EXISTS nba_players (
    player_id INTEGER PRIMARY KEY,
    player_name VARCHAR(255) NOT NULL,
    team VARCHAR(10),
    position VARCHAR(50),
    
    -- Career info
    height VARCHAR(10),
    weight INTEGER,
    birth_date DATE,
    age INTEGER,
    jersey_number VARCHAR(5),
    
    -- Status
    is_active BOOLEAN DEFAULT TRUE,
    injury_status VARCHAR(50),
    
    -- Metadata
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_nba_players_name ON nba_players(player_name);
CREATE INDEX idx_nba_players_team ON nba_players(team);
CREATE INDEX idx_nba_players_active ON nba_players(is_active);

-- ==========================================
-- PLAYER STATISTICS (Historical data)
-- ==========================================
CREATE TABLE IF NOT EXISTS player_statistics (
    stat_id SERIAL PRIMARY KEY,
    player_id INTEGER NOT NULL,
    season VARCHAR(10) NOT NULL,
    
    -- Basic stats
    games_played INTEGER,
    minutes_per_game NUMERIC(5,2),
    points_per_game NUMERIC(5,2),
    rebounds_per_game NUMERIC(5,2),
    assists_per_game NUMERIC(5,2),
    steals_per_game NUMERIC(5,2),
    blocks_per_game NUMERIC(5,2),
    turnovers_per_game NUMERIC(5,2),
    
    -- Shooting stats
    field_goals_made NUMERIC(5,2),
    field_goals_attempted NUMERIC(5,2),
    field_goal_percentage NUMERIC(5,4),
    three_pointers_made NUMERIC(5,2),
    three_pointers_attempted NUMERIC(5,2),
    three_point_percentage NUMERIC(5,4),
    free_throws_made NUMERIC(5,2),
    free_throws_attempted NUMERIC(5,2),
    free_throw_percentage NUMERIC(5,4),
    
    -- Advanced stats
    offensive_rebounds NUMERIC(5,2),
    defensive_rebounds NUMERIC(5,2),
    personal_fouls NUMERIC(5,2),
    plus_minus NUMERIC(6,2),
    
    -- Metadata
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (player_id) REFERENCES nba_players(player_id) ON DELETE CASCADE,
    UNIQUE(player_id, season)
);

CREATE INDEX idx_player_stats_player ON player_statistics(player_id);
CREATE INDEX idx_player_stats_season ON player_statistics(season);

-- ==========================================
-- PROJECTIONS (5-Year Average)
-- ==========================================
CREATE TABLE IF NOT EXISTS projections_5year (
    projection_id SERIAL PRIMARY KEY,
    player_id INTEGER NOT NULL,
    
    -- Projected stats
    games_played NUMERIC(5,2),
    minutes_per_game NUMERIC(5,2),
    points_per_game NUMERIC(5,2),
    rebounds_per_game NUMERIC(5,2),
    assists_per_game NUMERIC(5,2),
    steals_per_game NUMERIC(5,2),
    blocks_per_game NUMERIC(5,2),
    turnovers_per_game NUMERIC(5,2),
    
    -- Shooting projections
    field_goals_made NUMERIC(5,2),
    field_goals_attempted NUMERIC(5,2),
    field_goal_percentage NUMERIC(5,4),
    three_pointers_made NUMERIC(5,2),
    three_pointers_attempted NUMERIC(5,2),
    three_point_percentage NUMERIC(5,4),
    free_throws_made NUMERIC(5,2),
    free_throws_attempted NUMERIC(5,2),
    free_throw_percentage NUMERIC(5,4),
    
    -- Model info
    seasons_included TEXT[],
    confidence_score NUMERIC(5,4),
    last_calculated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (player_id) REFERENCES nba_players(player_id) ON DELETE CASCADE,
    UNIQUE(player_id)
);

CREATE INDEX idx_projections_5year_player ON projections_5year(player_id);

-- ==========================================
-- PROJECTIONS (Current Season)
-- ==========================================
CREATE TABLE IF NOT EXISTS projections_current (
    projection_id SERIAL PRIMARY KEY,
    player_id INTEGER NOT NULL,
    season VARCHAR(10) NOT NULL,
    
    -- Projected stats
    games_played NUMERIC(5,2),
    minutes_per_game NUMERIC(5,2),
    points_per_game NUMERIC(5,2),
    rebounds_per_game NUMERIC(5,2),
    assists_per_game NUMERIC(5,2),
    steals_per_game NUMERIC(5,2),
    blocks_per_game NUMERIC(5,2),
    turnovers_per_game NUMERIC(5,2),
    
    -- Shooting projections
    field_goals_made NUMERIC(5,2),
    field_goals_attempted NUMERIC(5,2),
    field_goal_percentage NUMERIC(5,4),
    three_pointers_made NUMERIC(5,2),
    three_pointers_attempted NUMERIC(5,2),
    three_point_percentage NUMERIC(5,4),
    free_throws_made NUMERIC(5,2),
    free_throws_attempted NUMERIC(5,2),
    free_throw_percentage NUMERIC(5,4),
    
    -- Age-based adjustments
    age_factor NUMERIC(5,4),
    injury_risk_factor NUMERIC(5,4),
    
    -- Model info
    model_version VARCHAR(50),
    confidence_score NUMERIC(5,4),
    last_calculated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (player_id) REFERENCES nba_players(player_id) ON DELETE CASCADE,
    UNIQUE(player_id, season)
);

CREATE INDEX idx_projections_current_player ON projections_current(player_id);
CREATE INDEX idx_projections_current_season ON projections_current(season);

-- ==========================================
-- CUSTOM INJURY OVERRIDES (Per-customer adjustments)
-- ==========================================
CREATE TABLE IF NOT EXISTS injury_overrides (
    override_id SERIAL PRIMARY KEY,
    customer_id VARCHAR(100) NOT NULL,
    player_id INTEGER NOT NULL,
    
    -- Override values
    games_override INTEGER,
    notes TEXT,
    
    -- Status
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP,
    
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id) ON DELETE CASCADE,
    FOREIGN KEY (player_id) REFERENCES nba_players(player_id) ON DELETE CASCADE,
    UNIQUE(customer_id, player_id, is_active)
);

CREATE INDEX idx_injury_overrides_customer ON injury_overrides(customer_id);
CREATE INDEX idx_injury_overrides_player ON injury_overrides(player_id);

-- ==========================================
-- MODEL TRAINING LOGS
-- ==========================================
CREATE TABLE IF NOT EXISTS model_training_logs (
    log_id SERIAL PRIMARY KEY,
    customer_id VARCHAR(100) NOT NULL,
    
    -- Training info
    model_type VARCHAR(50) NOT NULL,
    training_started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    training_completed_at TIMESTAMP,
    
    -- Results
    status VARCHAR(20) DEFAULT 'running' CHECK (status IN ('running', 'completed', 'failed')),
    accuracy_score NUMERIC(5,4),
    error_message TEXT,
    
    -- Metadata
    parameters JSONB,
    
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id) ON DELETE CASCADE
);

CREATE INDEX idx_model_training_customer ON model_training_logs(customer_id);
CREATE INDEX idx_model_training_status ON model_training_logs(status);

-- ==========================================
-- API DEBUG LOG (Comprehensive logging)
-- ==========================================
CREATE TABLE IF NOT EXISTS api_debug_log (
    log_id SERIAL PRIMARY KEY,
    
    -- Request info
    customer_id VARCHAR(100),
    customer_email VARCHAR(255),
    customer_tier VARCHAR(20),
    request_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Endpoint details
    endpoint VARCHAR(255) NOT NULL,
    http_method VARCHAR(10),
    full_url TEXT,
    query_params JSONB,
    
    -- Request data
    request_body JSONB,
    request_headers JSONB,
    
    -- Response info
    response_status_code INTEGER,
    response_body JSONB,
    response_time_ms INTEGER,
    
    -- Error tracking
    error_message TEXT,
    error_stack_trace TEXT,
    
    -- Context
    ip_address VARCHAR(50),
    user_agent TEXT,
    league_id VARCHAR(50),
    player_ids INTEGER[],
    
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id) ON DELETE SET NULL
);

CREATE INDEX idx_api_debug_customer ON api_debug_log(customer_id);
CREATE INDEX idx_api_debug_timestamp ON api_debug_log(request_timestamp);
CREATE INDEX idx_api_debug_endpoint ON api_debug_log(endpoint);
CREATE INDEX idx_api_debug_status ON api_debug_log(response_status_code);
CREATE INDEX idx_api_debug_response_time ON api_debug_log(response_time_ms);

-- ==========================================
-- API ERRORS (Aggregated error tracking)
-- ==========================================
CREATE TABLE IF NOT EXISTS api_errors (
    error_id SERIAL PRIMARY KEY,
    
    -- Error details
    endpoint VARCHAR(255) NOT NULL,
    error_type VARCHAR(100),
    error_message TEXT NOT NULL,
    
    -- Tracking
    first_occurrence TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_occurrence TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    occurrence_count INTEGER DEFAULT 1,
    
    -- Affected customers
    customer_count INTEGER DEFAULT 0,
    affected_customers TEXT[],
    
    -- Status
    status VARCHAR(20) DEFAULT 'active' CHECK (status IN ('active', 'resolved', 'investigating')),
    resolution_notes TEXT,
    resolved_at TIMESTAMP
);

CREATE INDEX idx_api_errors_endpoint ON api_errors(endpoint);
CREATE INDEX idx_api_errors_status ON api_errors(status);

-- ==========================================
-- API PERFORMANCE METRICS (Hourly aggregates)
-- ==========================================
CREATE TABLE IF NOT EXISTS api_performance_metrics (
    metric_id SERIAL PRIMARY KEY,
    
    -- Time bucket
    time_bucket TIMESTAMP NOT NULL,
    endpoint VARCHAR(255) NOT NULL,
    
    -- Metrics
    total_requests INTEGER DEFAULT 0,
    successful_requests INTEGER DEFAULT 0,
    failed_requests INTEGER DEFAULT 0,
    
    -- Response times
    avg_response_time_ms INTEGER,
    min_response_time_ms INTEGER,
    max_response_time_ms INTEGER,
    p95_response_time_ms INTEGER,
    p99_response_time_ms INTEGER,
    
    -- Customer metrics
    unique_customers INTEGER DEFAULT 0,
    
    UNIQUE(time_bucket, endpoint)
);

CREATE INDEX idx_performance_metrics_time ON api_performance_metrics(time_bucket);
CREATE INDEX idx_performance_metrics_endpoint ON api_performance_metrics(endpoint);

-- ==========================================
-- USAGE TRACKING (For billing/analytics)
-- ==========================================
CREATE TABLE IF NOT EXISTS usage_tracking (
    usage_id SERIAL PRIMARY KEY,
    customer_id VARCHAR(100) NOT NULL,
    
    -- Time period
    date DATE NOT NULL,
    hour INTEGER,
    
    -- Usage counts
    total_requests INTEGER DEFAULT 0,
    projection_requests INTEGER DEFAULT 0,
    league_requests INTEGER DEFAULT 0,
    
    -- Costs (if applicable)
    estimated_cost NUMERIC(10,4) DEFAULT 0,
    
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id) ON DELETE CASCADE,
    UNIQUE(customer_id, date, hour)
);

CREATE INDEX idx_usage_tracking_customer ON usage_tracking(customer_id);
CREATE INDEX idx_usage_tracking_date ON usage_tracking(date);

-- ==========================================
-- DEMO DATA (For testing)
-- ==========================================

-- Insert demo customers
INSERT INTO customers (customer_id, email, company_name, tier, can_access_current_season, can_train_models, custom_override_limit) VALUES
('free_demo_customer', 'free@demo.com', 'Free Demo Co', 'free', FALSE, FALSE, 0),
('pro_demo_customer', 'pro@demo.com', 'Pro Demo Co', 'pro', TRUE, FALSE, 50),
('enterprise_demo_customer', 'enterprise@demo.com', 'Enterprise Demo Co', 'enterprise', TRUE, TRUE, 999999)
ON CONFLICT (customer_id) DO NOTHING;

-- Insert demo API keys
INSERT INTO api_keys (customer_id, api_key, key_name, rate_limit_per_hour) VALUES
('free_demo_customer', 'free_demo_key_12345', 'Free Demo Key', 100),
('pro_demo_customer', 'pro_demo_key_67890', 'Pro Demo Key', 1000),
('enterprise_demo_customer', 'enterprise_demo_key_11111', 'Enterprise Demo Key', 10000)
ON CONFLICT (api_key) DO NOTHING;

-- ==========================================
-- HELPER FUNCTIONS
-- ==========================================

-- Function to update rate limits
CREATE OR REPLACE FUNCTION reset_rate_limits()
RETURNS void AS $$
BEGIN
    UPDATE api_keys
    SET requests_used_this_hour = 0,
        rate_limit_reset_at = CURRENT_TIMESTAMP
    WHERE rate_limit_reset_at < CURRENT_TIMESTAMP - INTERVAL '1 hour';
END;
$$ LANGUAGE plpgsql;

-- Function to cleanup old logs
CREATE OR REPLACE FUNCTION cleanup_old_debug_logs(days_to_keep INTEGER DEFAULT 30)
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    -- Delete successful requests older than days_to_keep
    DELETE FROM api_debug_log
    WHERE request_timestamp < NOW() - (days_to_keep || ' days')::INTERVAL
    AND response_status_code < 400;
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    
    -- Delete error requests older than 90 days
    DELETE FROM api_debug_log
    WHERE request_timestamp < NOW() - INTERVAL '90 days'
    AND response_status_code >= 400;
    
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- ==========================================
-- VIEWS
-- ==========================================

-- Active customers view
CREATE OR REPLACE VIEW active_customers AS
SELECT 
    c.customer_id,
    c.email,
    c.tier,
    COUNT(DISTINCT ak.api_key) as api_key_count,
    MAX(ak.last_used_at) as last_api_usage
FROM customers c
LEFT JOIN api_keys ak ON c.customer_id = ak.customer_id AND ak.is_active = TRUE
WHERE c.is_active = TRUE
GROUP BY c.customer_id, c.email, c.tier;

-- Customer usage summary
CREATE OR REPLACE VIEW customer_usage_summary AS
SELECT 
    ut.customer_id,
    c.email,
    c.tier,
    SUM(ut.total_requests) as total_requests,
    MAX(ut.date) as last_usage_date
FROM usage_tracking ut
JOIN customers c ON ut.customer_id = c.customer_id
WHERE ut.date >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY ut.customer_id, c.email, c.tier;

-- ==========================================
-- GRANTS (Adjust as needed)
-- ==========================================
-- GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO your_app_user;
-- GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO your_app_user;

-- ==========================================
-- COMPLETION MESSAGE
-- ==========================================
DO $$
BEGIN
    RAISE NOTICE '✅ Main database schema created successfully!';
    RAISE NOTICE '👥 Demo customers created: free@demo.com, pro@demo.com, enterprise@demo.com';
    RAISE NOTICE '🔑 Demo API keys created for testing';
    RAISE NOTICE '📊 Tables: customers, api_keys, nba_players, player_statistics, projections, logs, etc.';
END $$;
