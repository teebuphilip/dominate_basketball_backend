-- NBA Fantasy Basketball Platform - Scoring Schema
-- Tables for leagues, rosters, performance tracking, and analytics

-- ==========================================
-- LEAGUES TABLE
-- ==========================================
CREATE TABLE IF NOT EXISTS leagues (
    league_id VARCHAR(50) PRIMARY KEY,
    customer_id VARCHAR(100) NOT NULL,
    league_name VARCHAR(255) NOT NULL,
    platform VARCHAR(50),
    scoring_type VARCHAR(20) NOT NULL CHECK (scoring_type IN ('roto', 'h2h_categories', 'h2h_points')),
    
    -- Categories configuration
    categories TEXT[] NOT NULL,
    category_display_names JSONB DEFAULT '{}',
    
    -- Roto-specific settings
    weekly_targets JSONB,
    
    -- H2H Points-specific settings
    points_values JSONB,
    
    -- League settings
    roster_size INTEGER DEFAULT 13,
    games_per_week NUMERIC(4,2) DEFAULT 3.33,
    
    -- Position requirements
    position_requirements JSONB DEFAULT '{
        "PG": 1, "SG": 1, "SF": 1, "PF": 1, "C": 1,
        "G": 1, "F": 1, "UTIL": 2, "BE": 3
    }',
    
    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id) ON DELETE CASCADE
);

CREATE INDEX idx_leagues_customer ON leagues(customer_id);
CREATE INDEX idx_leagues_active ON leagues(is_active);

-- ==========================================
-- ROSTERS TABLE
-- ==========================================
CREATE TABLE IF NOT EXISTS rosters (
    roster_id SERIAL PRIMARY KEY,
    league_id VARCHAR(50) NOT NULL,
    customer_id VARCHAR(100) NOT NULL,
    
    -- Player info
    player_id INTEGER NOT NULL,
    player_name VARCHAR(255) NOT NULL,
    player_team VARCHAR(10),
    player_position VARCHAR(50),
    
    -- Roster management
    roster_slot VARCHAR(20),
    acquisition_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    
    -- Metadata
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (league_id) REFERENCES leagues(league_id) ON DELETE CASCADE,
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id) ON DELETE CASCADE,
    
    UNIQUE(league_id, player_id, is_active)
);

CREATE INDEX idx_rosters_league ON rosters(league_id);
CREATE INDEX idx_rosters_customer ON rosters(customer_id);
CREATE INDEX idx_rosters_player ON rosters(player_id);
CREATE INDEX idx_rosters_active ON rosters(is_active);

-- ==========================================
-- WEEKLY PERFORMANCE TABLE
-- ==========================================
CREATE TABLE IF NOT EXISTS weekly_performance (
    performance_id SERIAL PRIMARY KEY,
    league_id VARCHAR(50) NOT NULL,
    customer_id VARCHAR(100) NOT NULL,
    
    -- Week tracking
    week_number INTEGER NOT NULL,
    week_start DATE NOT NULL,
    week_end DATE NOT NULL,
    season_year INTEGER DEFAULT EXTRACT(YEAR FROM CURRENT_DATE),
    
    -- Performance data
    category_totals JSONB NOT NULL,
    roster_snapshot JSONB,
    
    -- Status
    is_complete BOOLEAN DEFAULT FALSE,
    saved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (league_id) REFERENCES leagues(league_id) ON DELETE CASCADE,
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id) ON DELETE CASCADE,
    
    UNIQUE(league_id, season_year, week_number)
);

CREATE INDEX idx_weekly_performance_league ON weekly_performance(league_id);
CREATE INDEX idx_weekly_performance_customer ON weekly_performance(customer_id);
CREATE INDEX idx_weekly_performance_week ON weekly_performance(season_year, week_number);

-- ==========================================
-- CATEGORY PRESETS TABLE
-- ==========================================
CREATE TABLE IF NOT EXISTS category_presets (
    preset_id SERIAL PRIMARY KEY,
    preset_name VARCHAR(100) UNIQUE NOT NULL,
    description TEXT,
    scoring_type VARCHAR(20) NOT NULL,
    
    -- Configuration
    categories TEXT[] NOT NULL,
    category_display_names JSONB DEFAULT '{}',
    weekly_targets JSONB,
    points_values JSONB,
    
    -- Metadata
    is_default BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insert default presets
INSERT INTO category_presets (preset_name, description, scoring_type, categories, weekly_targets) VALUES
('Standard 9-Category', 'Most common fantasy format', 'roto', 
 ARRAY['PTS', 'REB', 'AST', 'STL', 'BLK', '3PM', 'TO', 'FG_PCT', 'FT_PCT'],
 '{"PTS": 712, "REB": 196, "AST": 142, "STL": 54, "BLK": 41, "3PM": 43, "TO": 85, "FG_PCT": 0.47, "FT_PCT": 0.75}'::jsonb
),
('Standard 8-Category', 'No turnovers', 'roto',
 ARRAY['PTS', 'REB', 'AST', 'STL', 'BLK', '3PM', 'FG_PCT', 'FT_PCT'],
 '{"PTS": 712, "REB": 196, "AST": 142, "STL": 54, "BLK": 41, "3PM": 43, "FG_PCT": 0.47, "FT_PCT": 0.75}'::jsonb
),
('11-Category Split Rebounds', 'OREB and DREB separate', 'roto',
 ARRAY['PTS', 'OREB', 'DREB', 'AST', 'STL', 'BLK', '3PM', 'TO', 'FG_PCT', 'FT_PCT', 'FGM'],
 '{"PTS": 712, "OREB": 55, "DREB": 141, "AST": 142, "STL": 54, "BLK": 41, "3PM": 43, "TO": 85, "FG_PCT": 0.47, "FT_PCT": 0.75, "FGM": 265}'::jsonb
),
('ESPN Standard Points', 'Standard points league', 'h2h_points',
 ARRAY['PTS', 'REB', 'AST', 'STL', 'BLK', '3PM', 'TO', 'FGM', 'FGA', 'FTM', 'FTA'],
 NULL
)
ON CONFLICT (preset_name) DO NOTHING;

-- Update ESPN points preset with points values
UPDATE category_presets 
SET points_values = '{"PTS": 1.0, "REB": 1.2, "AST": 1.5, "STL": 3.0, "BLK": 3.0, "3PM": 3.0, "TO": -1.0, "FGM": 2.0, "FGA": -1.0, "FTM": 1.0, "FTA": -1.0}'::jsonb
WHERE preset_name = 'ESPN Standard Points';

-- ==========================================
-- PLAYER TRANSACTIONS TABLE
-- ==========================================
CREATE TABLE IF NOT EXISTS player_transactions (
    transaction_id SERIAL PRIMARY KEY,
    league_id VARCHAR(50) NOT NULL,
    customer_id VARCHAR(100) NOT NULL,
    
    -- Transaction details
    transaction_type VARCHAR(20) NOT NULL CHECK (transaction_type IN ('add', 'drop', 'trade')),
    player_id INTEGER NOT NULL,
    player_name VARCHAR(255) NOT NULL,
    
    -- Context
    transaction_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    notes TEXT,
    
    FOREIGN KEY (league_id) REFERENCES leagues(league_id) ON DELETE CASCADE,
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id) ON DELETE CASCADE
);

CREATE INDEX idx_transactions_league ON player_transactions(league_id);
CREATE INDEX idx_transactions_customer ON player_transactions(customer_id);
CREATE INDEX idx_transactions_date ON player_transactions(transaction_date);

-- ==========================================
-- WATCHLIST TABLE
-- ==========================================
CREATE TABLE IF NOT EXISTS watchlist (
    watchlist_id SERIAL PRIMARY KEY,
    league_id VARCHAR(50) NOT NULL,
    customer_id VARCHAR(100) NOT NULL,
    
    -- Player info
    player_id INTEGER NOT NULL,
    player_name VARCHAR(255) NOT NULL,
    
    -- Notes
    notes TEXT,
    priority VARCHAR(20) DEFAULT 'medium' CHECK (priority IN ('low', 'medium', 'high')),
    
    -- Metadata
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (league_id) REFERENCES leagues(league_id) ON DELETE CASCADE,
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id) ON DELETE CASCADE,
    
    UNIQUE(league_id, player_id)
);

CREATE INDEX idx_watchlist_league ON watchlist(league_id);
CREATE INDEX idx_watchlist_customer ON watchlist(customer_id);
CREATE INDEX idx_watchlist_priority ON watchlist(priority);

-- ==========================================
-- MATCHUP HISTORY TABLE (For H2H tracking)
-- ==========================================
CREATE TABLE IF NOT EXISTS matchup_history (
    matchup_id SERIAL PRIMARY KEY,
    league_id VARCHAR(50) NOT NULL,
    customer_id VARCHAR(100) NOT NULL,
    
    -- Week info
    week_number INTEGER NOT NULL,
    season_year INTEGER DEFAULT EXTRACT(YEAR FROM CURRENT_DATE),
    
    -- Matchup details
    opponent_name VARCHAR(255),
    opponent_roster JSONB,
    
    -- Results (for H2H Categories)
    categories_won INTEGER DEFAULT 0,
    categories_lost INTEGER DEFAULT 0,
    categories_tied INTEGER DEFAULT 0,
    
    -- Results (for H2H Points)
    my_points NUMERIC(10,2),
    opponent_points NUMERIC(10,2),
    
    -- Metadata
    matchup_result VARCHAR(10) CHECK (matchup_result IN ('win', 'loss', 'tie')),
    saved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (league_id) REFERENCES leagues(league_id) ON DELETE CASCADE,
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id) ON DELETE CASCADE,
    
    UNIQUE(league_id, season_year, week_number)
);

CREATE INDEX idx_matchup_history_league ON matchup_history(league_id);
CREATE INDEX idx_matchup_history_week ON matchup_history(season_year, week_number);

-- ==========================================
-- TRADE EVALUATIONS TABLE
-- ==========================================
CREATE TABLE IF NOT EXISTS trade_evaluations (
    evaluation_id SERIAL PRIMARY KEY,
    league_id VARCHAR(50) NOT NULL,
    customer_id VARCHAR(100) NOT NULL,
    
    -- Trade details
    giving_player_ids INTEGER[] NOT NULL,
    receiving_player_ids INTEGER[] NOT NULL,
    
    -- Analysis results
    value_change NUMERIC(10,2),
    trade_rating VARCHAR(5),
    recommendation VARCHAR(20),
    
    -- Full analysis
    analysis_json JSONB,
    
    -- Metadata
    evaluated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    notes TEXT,
    
    FOREIGN KEY (league_id) REFERENCES leagues(league_id) ON DELETE CASCADE,
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id) ON DELETE CASCADE
);

CREATE INDEX idx_trade_evaluations_league ON trade_evaluations(league_id);
CREATE INDEX idx_trade_evaluations_customer ON trade_evaluations(customer_id);
CREATE INDEX idx_trade_evaluations_date ON trade_evaluations(evaluated_at);

-- ==========================================
-- STREAMING TARGETS TABLE
-- ==========================================
CREATE TABLE IF NOT EXISTS streaming_targets (
    target_id SERIAL PRIMARY KEY,
    league_id VARCHAR(50) NOT NULL,
    customer_id VARCHAR(100) NOT NULL,
    
    -- Player info
    player_id INTEGER NOT NULL,
    player_name VARCHAR(255) NOT NULL,
    
    -- Streaming context
    target_week INTEGER NOT NULL,
    games_scheduled INTEGER NOT NULL,
    streaming_value NUMERIC(10,2),
    
    -- Status
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'added', 'skipped')),
    
    -- Metadata
    identified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (league_id) REFERENCES leagues(league_id) ON DELETE CASCADE,
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id) ON DELETE CASCADE
);

CREATE INDEX idx_streaming_targets_league ON streaming_targets(league_id);
CREATE INDEX idx_streaming_targets_week ON streaming_targets(target_week);
CREATE INDEX idx_streaming_targets_status ON streaming_targets(status);

-- ==========================================
-- HELPER VIEWS
-- ==========================================

-- View: Active rosters with player details
CREATE OR REPLACE VIEW active_rosters AS
SELECT 
    r.roster_id,
    r.league_id,
    r.customer_id,
    r.player_id,
    r.player_name,
    r.player_team,
    r.player_position,
    r.roster_slot,
    r.acquisition_date,
    l.league_name,
    l.scoring_type
FROM rosters r
JOIN leagues l ON r.league_id = l.league_id
WHERE r.is_active = TRUE AND l.is_active = TRUE;

-- View: League performance summary
CREATE OR REPLACE VIEW league_performance_summary AS
SELECT 
    wp.league_id,
    wp.customer_id,
    COUNT(*) as weeks_tracked,
    MAX(wp.week_number) as latest_week,
    MIN(wp.week_start) as first_week_start,
    MAX(wp.week_end) as latest_week_end
FROM weekly_performance wp
WHERE wp.is_complete = TRUE
GROUP BY wp.league_id, wp.customer_id;

-- View: Transaction summary
CREATE OR REPLACE VIEW transaction_summary AS
SELECT 
    pt.league_id,
    pt.customer_id,
    pt.transaction_type,
    COUNT(*) as transaction_count,
    MAX(pt.transaction_date) as last_transaction
FROM player_transactions pt
GROUP BY pt.league_id, pt.customer_id, pt.transaction_type;

-- ==========================================
-- CLEANUP FUNCTIONS
-- ==========================================

-- Function to archive old weekly performance data
CREATE OR REPLACE FUNCTION archive_old_weekly_performance()
RETURNS void AS $$
BEGIN
    DELETE FROM weekly_performance
    WHERE saved_at < NOW() - INTERVAL '2 years';
END;
$$ LANGUAGE plpgsql;

-- Function to clean up inactive rosters
CREATE OR REPLACE FUNCTION cleanup_inactive_rosters()
RETURNS void AS $$
BEGIN
    DELETE FROM rosters
    WHERE is_active = FALSE
    AND added_at < NOW() - INTERVAL '90 days';
END;
$$ LANGUAGE plpgsql;

-- ==========================================
-- COMMENTS
-- ==========================================
COMMENT ON TABLE leagues IS 'Fantasy basketball league configurations';
COMMENT ON TABLE rosters IS 'Player rosters for each league';
COMMENT ON TABLE weekly_performance IS 'Historical weekly performance tracking';
COMMENT ON TABLE category_presets IS 'Pre-configured league templates';
COMMENT ON TABLE player_transactions IS 'Add/drop/trade history';
COMMENT ON TABLE watchlist IS 'Players being monitored by users';
COMMENT ON TABLE matchup_history IS 'H2H matchup results tracking';
COMMENT ON TABLE trade_evaluations IS 'Trade analysis history';
COMMENT ON TABLE streaming_targets IS 'Players identified for streaming strategy';

-- ==========================================
-- COMPLETION MESSAGE
-- ==========================================
DO $$
BEGIN
    RAISE NOTICE '✅ Scoring schema created successfully!';
    RAISE NOTICE '📊 Tables: leagues, rosters, weekly_performance, category_presets, player_transactions, watchlist, matchup_history, trade_evaluations, streaming_targets';
    RAISE NOTICE '🎯 Views: active_rosters, league_performance_summary, transaction_summary';
    RAISE NOTICE '🔧 Functions: archive_old_weekly_performance(), cleanup_inactive_rosters()';
    RAISE NOTICE '✨ 4 default category presets inserted';
END $$;
