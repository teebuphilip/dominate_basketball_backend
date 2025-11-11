"""
NBA Fantasy Basketball Platform - Main FastAPI Application
Complete API with 50+ endpoints for production use
"""

from fastapi import FastAPI, Request, HTTPException, Header
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import time
import traceback
import uvicorn
import json

# Import all modules
import dbb2_database as db
import dbb2_nba_data_fetcher as nba
import dbb2_scoring_engine as scoring
import dbb2_league_db as league_db
import dbb2_weekly_tracking as weekly
import dbb2_lineup_optimizer as lineup
import dbb2_streaming_optimizer as streaming
import dbb2_opponent_analyzer as opponent
import dbb2_trade_analyzer as trade
import dbb2_api_logger as logger

# Initialize FastAPI app
app = FastAPI(
    title="NBA Fantasy Basketball Platform",
    description="Complete fantasy basketball API with projections, leagues, and advanced analytics",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================
# REQUEST MODELS
# ============================================

class LeagueCreate(BaseModel):
    league_name: str
    platform: Optional[str] = None
    scoring_type: str
    categories: List[str]
    category_display_names: Optional[Dict[str, str]] = {}
    weekly_targets: Optional[Dict[str, float]] = {}
    points_values: Optional[Dict[str, float]] = {}
    roster_size: Optional[int] = 13
    games_per_week: Optional[float] = 3.33
    position_requirements: Optional[Dict[str, int]] = None


class LeagueUpdate(BaseModel):
    league_name: Optional[str] = None
    weekly_targets: Optional[Dict[str, float]] = None
    points_values: Optional[Dict[str, float]] = None
    roster_size: Optional[int] = None
    games_per_week: Optional[float] = None
    position_requirements: Optional[Dict[str, int]] = None


class RosterAdd(BaseModel):
    player_id: int
    player_name: str
    player_team: Optional[str] = None
    player_position: Optional[str] = None
    roster_slot: Optional[str] = None


class WatchlistAdd(BaseModel):
    player_id: int
    player_name: str
    notes: Optional[str] = None
    priority: Optional[str] = "medium"


class MatchupAnalyze(BaseModel):
    opponent_player_ids: List[int]


class TradeAnalyze(BaseModel):
    giving: List[int]
    receiving: List[int]


class TradeCompare(BaseModel):
    trades: List[Dict[str, Any]]


class InjuryOverride(BaseModel):
    player_id: int
    games_override: int
    notes: Optional[str] = None


# ============================================
# MIDDLEWARE
# ============================================

@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all API requests"""
    start_time = time.time()
    
    # Get customer from API key
    api_key = request.headers.get("x-api-key")
    customer = None
    
    if api_key:
        customer = db.get_customer_by_api_key(api_key)
    
    # Process request
    try:
        response = await call_next(request)
        response_time = int((time.time() - start_time) * 1000)
        
        # Log successful request
        logger.log_api_request(
            customer_id=customer['customer_id'] if customer else None,
            customer_email=customer['email'] if customer else None,
            customer_tier=customer['tier'] if customer else None,
            endpoint=request.url.path,
            http_method=request.method,
            full_url=str(request.url),
            query_params=dict(request.query_params),
            request_body=None,
            request_headers=dict(request.headers),
            response_status_code=response.status_code,
            response_body=None,
            response_time_ms=response_time,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent")
        )
        
        return response
        
    except Exception as e:
        response_time = int((time.time() - start_time) * 1000)
        error_trace = traceback.format_exc()
        
        # Log error
        logger.log_api_request(
            customer_id=customer['customer_id'] if customer else None,
            customer_email=customer['email'] if customer else None,
            customer_tier=customer['tier'] if customer else None,
            endpoint=request.url.path,
            http_method=request.method,
            full_url=str(request.url),
            query_params=dict(request.query_params),
            request_body=None,
            request_headers=dict(request.headers),
            response_status_code=500,
            response_body={"error": str(e)},
            response_time_ms=response_time,
            error_message=str(e),
            error_stack_trace=error_trace,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent")
        )
        
        raise


def verify_api_key(x_api_key: str = Header(...)) -> dict:
    """Verify API key and return customer"""
    customer = db.get_customer_by_api_key(x_api_key)
    
    if not customer:
        raise HTTPException(status_code=401, detail="Invalid API key")
    
    # Check rate limit
    within_limit, used, limit = db.check_rate_limit(x_api_key)
    
    if not within_limit:
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded. Used {used}/{limit} requests this hour"
        )
    
    # Update rate limit counter
    db.update_rate_limit(x_api_key)
    
    return customer


# ============================================
# BASIC ENDPOINTS
# ============================================

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "name": "NBA Fantasy Basketball Platform",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    db_healthy = db.health_check()
    
    return {
        "status": "healthy" if db_healthy else "unhealthy",
        "database": "connected" if db_healthy else "disconnected"
    }


# ============================================
# ACCOUNT ENDPOINTS
# ============================================

@app.get("/account")
async def get_account(x_api_key: str = Header(...)):
    """Get account information"""
    customer = verify_api_key(x_api_key)
    
    usage = db.get_customer_usage(customer['customer_id'])
    
    return {
        "customer_id": customer['customer_id'],
        "email": customer['email'],
        "tier": customer['tier'],
        "features": {
            "current_season_access": customer['can_access_current_season'],
            "custom_models": customer['can_train_models'],
            "custom_override_limit": customer['custom_override_limit']
        },
        "usage": usage
    }


@app.get("/tiers")
async def get_tiers():
    """Get pricing tier information"""
    return {
        "tiers": [
            {
                "name": "free",
                "price": 0,
                "rate_limit": 100,
                "features": {
                    "5year_projections": True,
                    "current_season": False,
                    "custom_overrides": 0,
                    "advanced_analytics": False
                }
            },
            {
                "name": "pro",
                "price": 49,
                "rate_limit": 1000,
                "features": {
                    "5year_projections": True,
                    "current_season": True,
                    "custom_overrides": 50,
                    "advanced_analytics": True
                }
            },
            {
                "name": "enterprise",
                "price": 499,
                "rate_limit": 10000,
                "features": {
                    "5year_projections": True,
                    "current_season": True,
                    "custom_overrides": -1,
                    "advanced_analytics": True,
                    "custom_models": True
                }
            }
        ]
    }


@app.get("/usage")
async def get_usage(x_api_key: str = Header(...), days: int = 30):
    """Get usage statistics"""
    customer = verify_api_key(x_api_key)
    
    usage = db.get_customer_usage(customer['customer_id'], days)
    
    return {
        "customer_id": customer['customer_id'],
        "days": days,
        "usage": usage
    }


# ============================================
# PROJECTION ENDPOINTS
# ============================================

@app.get("/projections/5year/{player_id}")
async def get_5year_projection(player_id: int, x_api_key: str = Header(...)):
    """Get 5-year average projection"""
    customer = verify_api_key(x_api_key)
    
    projection = nba.calculate_5year_average(player_id)
    
    if not projection:
        raise HTTPException(status_code=404, detail="Player not found or insufficient data")
    
    return {"player_id": player_id, "projection": projection}


@app.get("/projections/current/{player_id}")
async def get_current_projection(player_id: int, x_api_key: str = Header(...)):
    """Get current season projection (Pro/Enterprise only)"""
    customer = verify_api_key(x_api_key)
    
    if not customer['can_access_current_season']:
        raise HTTPException(status_code=403, detail="Current season projections require Pro or Enterprise tier")
    
    projection = nba.calculate_current_season_projection(player_id)
    
    if not projection:
        raise HTTPException(status_code=404, detail="Player not found or insufficient data")
    
    return {"player_id": player_id, "projection": projection}


@app.get("/projections/5year/team/{team}")
async def get_team_5year_projections(team: str, x_api_key: str = Header(...)):
    """Get 5-year projections for all team players"""
    customer = verify_api_key(x_api_key)
    
    player_ids = nba.get_team_players(team)
    
    projections = []
    for player_id in player_ids:
        proj = nba.calculate_5year_average(player_id)
        if proj:
            projections.append(proj)
    
    return {"team": team, "projections": projections, "count": len(projections)}


@app.get("/projections/current/team/{team}")
async def get_team_current_projections(team: str, x_api_key: str = Header(...)):
    """Get current season projections for all team players (Pro/Enterprise only)"""
    customer = verify_api_key(x_api_key)
    
    if not customer['can_access_current_season']:
        raise HTTPException(status_code=403, detail="Current season projections require Pro or Enterprise tier")
    
    player_ids = nba.get_team_players(team)
    
    projections = []
    for player_id in player_ids:
        proj = nba.calculate_current_season_projection(player_id)
        if proj:
            projections.append(proj)
    
    return {"team": team, "projections": projections, "count": len(projections)}


@app.get("/age-analysis/{player_id}")
async def get_age_analysis(player_id: int, x_api_key: str = Header(...)):
    """Get age-based performance analysis"""
    customer = verify_api_key(x_api_key)
    
    player_info = nba.get_player_info(player_id)
    
    if not player_info:
        raise HTTPException(status_code=404, detail="Player not found")
    
    age = player_info.get('age', 28)
    
    return {
        "player_id": player_id,
        "player_name": player_info.get('player_name', 'Unknown'),
        "age": age,
        "age_factor": nba.get_age_factor(age),
        "injury_risk_factor": nba.get_injury_risk_factor(age),
        "predicted_games": nba.predict_games_played(30.0, age, player_info.get('position', 'G'))
    }


@app.get("/injury-curve")
async def get_injury_curve():
    """Get injury risk curve by age"""
    curve_data = []
    
    for age in range(19, 40):
        curve_data.append({
            "age": age,
            "age_factor": nba.get_age_factor(age),
            "injury_risk": nba.get_injury_risk_factor(age)
        })
    
    return {"injury_curve": curve_data}


@app.get("/players")
async def search_players(q: str, x_api_key: str = Header(...)):
    """Search for players"""
    customer = verify_api_key(x_api_key)
    
    results = nba.search_players(q)
    
    return {"query": q, "results": results, "count": len(results)}


# ============================================
# LEAGUE ENDPOINTS
# ============================================

@app.post("/leagues")
async def create_league(league: LeagueCreate, x_api_key: str = Header(...)):
    """Create a new league"""
    customer = verify_api_key(x_api_key)
    
    created = league_db.create_league(
        customer['customer_id'],
        league.league_name,
        league.scoring_type,
        league.categories,
        platform=league.platform,
        category_display_names=league.category_display_names,
        weekly_targets=league.weekly_targets,
        points_values=league.points_values,
        roster_size=league.roster_size,
        games_per_week=league.games_per_week,
        position_requirements=league.position_requirements
    )
    
    return {"message": "League created", "league": created}


@app.get("/leagues")
async def get_leagues(x_api_key: str = Header(...)):
    """Get all leagues for customer"""
    customer = verify_api_key(x_api_key)
    
    leagues = league_db.get_customer_leagues(customer['customer_id'])
    
    return {"leagues": leagues, "count": len(leagues)}


@app.get("/leagues/{league_id}")
async def get_league(league_id: str, x_api_key: str = Header(...)):
    """Get league details"""
    customer = verify_api_key(x_api_key)
    
    league = league_db.get_league(league_id, customer['customer_id'])
    
    if not league:
        raise HTTPException(status_code=404, detail="League not found")
    
    return {"league": league}


@app.put("/leagues/{league_id}")
async def update_league(league_id: str, updates: LeagueUpdate, x_api_key: str = Header(...)):
    """Update league settings"""
    customer = verify_api_key(x_api_key)
    
    update_dict = {k: v for k, v in updates.dict().items() if v is not None}
    
    updated = league_db.update_league(league_id, customer['customer_id'], update_dict)
    
    if not updated:
        raise HTTPException(status_code=404, detail="League not found")
    
    return {"message": "League updated", "league": updated}


@app.delete("/leagues/{league_id}")
async def delete_league(league_id: str, x_api_key: str = Header(...)):
    """Delete a league"""
    customer = verify_api_key(x_api_key)
    
    success = league_db.delete_league(league_id, customer['customer_id'])
    
    if not success:
        raise HTTPException(status_code=404, detail="League not found")
    
    return {"message": "League deleted"}


@app.get("/category-presets")
async def get_presets(x_api_key: str = Header(...)):
    """Get category presets"""
    customer = verify_api_key(x_api_key)
    
    presets = league_db.get_category_presets()
    
    return {"presets": presets}


# ============================================
# ROSTER ENDPOINTS
# ============================================

@app.get("/leagues/{league_id}/roster")
async def get_roster(league_id: str, x_api_key: str = Header(...)):
    """Get league roster"""
    customer = verify_api_key(x_api_key)
    
    roster = league_db.get_roster(league_id, customer['customer_id'])
    
    return {"league_id": league_id, "roster": roster, "count": len(roster)}


@app.post("/leagues/{league_id}/roster")
async def add_to_roster(league_id: str, player: RosterAdd, x_api_key: str = Header(...)):
    """Add player to roster"""
    customer = verify_api_key(x_api_key)
    
    added = league_db.add_roster_player(
        league_id,
        customer['customer_id'],
        player.player_id,
        player.player_name,
        player_team=player.player_team,
        player_position=player.player_position,
        roster_slot=player.roster_slot
    )
    
    return {"message": "Player added to roster", "player": added}


@app.delete("/leagues/{league_id}/roster/{player_id}")
async def remove_from_roster(league_id: str, player_id: int, x_api_key: str = Header(...)):
    """Remove player from roster"""
    customer = verify_api_key(x_api_key)
    
    success = league_db.remove_roster_player(league_id, customer['customer_id'], player_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Player not found in roster")
    
    return {"message": "Player removed from roster"}


# ============================================
# SCORING ENDPOINTS
# ============================================

@app.get("/leagues/{league_id}/score")
async def get_league_score(league_id: str, x_api_key: str = Header(...)):
    """Get current league score"""
    customer = verify_api_key(x_api_key)
    
    # Get league config
    league = league_db.get_league(league_id, customer['customer_id'])
    if not league:
        raise HTTPException(status_code=404, detail="League not found")
    
    # Get roster
    roster = league_db.get_roster(league_id, customer['customer_id'])
    
    # Get projections for roster
    roster_projections = []
    for player in roster:
        if customer['can_access_current_season']:
            proj = nba.calculate_current_season_projection(player['player_id'])
        else:
            proj = nba.calculate_5year_average(player['player_id'])
        
        if proj:
            proj['player_name'] = player['player_name']
            roster_projections.append(proj)
    
    # Calculate score based on league type
    scoring_type = league['scoring_type']
    
    if scoring_type == 'roto':
        weekly_targets = json.loads(league['weekly_targets']) if isinstance(league['weekly_targets'], str) else league['weekly_targets']
        categories = league['categories']
        
        score = scoring.calculate_roto_score(
            roster_projections,
            categories,
            weekly_targets,
            league['games_per_week']
        )
        
        return {
            "league_id": league_id,
            "league_name": league['league_name'],
            "scoring_type": scoring_type,
            "roster_count": len(roster),
            "score": score
        }
    
    elif scoring_type == 'h2h_points':
        points_values = json.loads(league['points_values']) if isinstance(league['points_values'], str) else league['points_values']
        
        score = scoring.calculate_h2h_points(
            roster_projections,
            points_values,
            league['games_per_week']
        )
        
        return {
            "league_id": league_id,
            "league_name": league['league_name'],
            "scoring_type": scoring_type,
            "roster_count": len(roster),
            "score": score
        }
    
    else:
        raise HTTPException(status_code=400, detail="Unsupported scoring type")


@app.get("/leagues/{league_id}/gaps")
async def get_gap_analysis(league_id: str, x_api_key: str = Header(...)):
    """Get gap analysis for Roto leagues"""
    customer = verify_api_key(x_api_key)
    
    # Get score first
    score_response = await get_league_score(league_id, x_api_key)
    
    if score_response['scoring_type'] != 'roto':
        raise HTTPException(status_code=400, detail="Gap analysis only available for Roto leagues")
    
    category_results = score_response['score']['category_results']
    roster_size = score_response['roster_count']
    
    gaps = scoring.get_gap_analysis(category_results, roster_size)
    
    return {
        "league_id": league_id,
        "gap_analysis": gaps
    }


@app.get("/leagues/{league_id}/recommendations")
async def get_recommendations(
    league_id: str,
    x_api_key: str = Header(...),
    limit: int = 20,
    focus_categories: Optional[str] = None
):
    """Get player recommendations based on league needs"""
    customer = verify_api_key(x_api_key)
    
    # Get league and roster
    league = league_db.get_league(league_id, customer['customer_id'])
    if not league:
        raise HTTPException(status_code=404, detail="League not found")
    
    roster = league_db.get_roster(league_id, customer['customer_id'])
    roster_player_ids = [p['player_id'] for p in roster]
    
    # Get gap analysis to determine needs
    if league['scoring_type'] == 'roto':
        gap_response = await get_gap_analysis(league_id, x_api_key)
        needs = [cat['category'] for cat in gap_response['gap_analysis']['needs_help'][:3]]
    else:
        needs = []
    
    if focus_categories:
        needs = focus_categories.split(',')
    
    # Get all players (simplified - in production would filter available players)
    all_players = nba.get_all_players()
    
    recommendations = []
    
    for player_data in all_players[:100]:  # Limit search
        player_id = player_data['id']
        
        if player_id in roster_player_ids:
            continue
        
        proj = nba.calculate_5year_average(player_id)
        
        if not proj:
            continue
        
        # Calculate value for needed categories
        value = 0.0
        for cat in needs:
            value += scoring.get_category_value(proj, cat)
        
        recommendations.append({
            "player_id": player_id,
            "player_name": player_data['full_name'],
            "value_score": round(value, 1),
            "category_contributions": {cat: scoring.get_category_value(proj, cat) for cat in needs},
            "projected_games": proj.get('games_played', 0),
            "injury_risk": "Low"  # Simplified
        })
    
    recommendations.sort(key=lambda x: x['value_score'], reverse=True)
    
    return {
        "league_id": league_id,
        "focus_categories": needs,
        "available_count": len(recommendations),
        "recommendations": recommendations[:limit]
    }


@app.get("/stats/{player_id}")
async def get_player_stats(player_id: int, x_api_key: str = Header(...)):
    """Get player statistics"""
    customer = verify_api_key(x_api_key)
    
    stats = nba.get_player_career_stats(player_id)
    
    if stats.empty:
        raise HTTPException(status_code=404, detail="No stats found for player")
    
    return {
        "player_id": player_id,
        "stats": stats.to_dict('records')
    }


# ============================================
# CUSTOM OVERRIDES ENDPOINTS
# ============================================

@app.get("/overrides")
async def get_overrides(x_api_key: str = Header(...)):
    """Get custom injury overrides"""
    customer = verify_api_key(x_api_key)
    
    query = """
        SELECT * FROM injury_overrides
        WHERE customer_id = %s
        AND is_active = TRUE
        ORDER BY created_at DESC
    """
    
    results = db.execute_query(query, (customer['customer_id'],))
    
    return {"overrides": results if results else [], "count": len(results) if results else 0}


@app.post("/overrides")
async def create_override(override: InjuryOverride, x_api_key: str = Header(...)):
    """Create injury override (Pro/Enterprise only)"""
    customer = verify_api_key(x_api_key)
    
    # Check limits
    if customer['custom_override_limit'] == 0:
        raise HTTPException(status_code=403, detail="Custom overrides require Pro or Enterprise tier")
    
    # Count current overrides
    query = "SELECT COUNT(*) as count FROM injury_overrides WHERE customer_id = %s AND is_active = TRUE"
    result = db.execute_query(query, (customer['customer_id'],))
    current_count = result[0]['count'] if result else 0
    
    if customer['custom_override_limit'] != -1 and current_count >= customer['custom_override_limit']:
        raise HTTPException(status_code=403, detail=f"Override limit reached ({customer['custom_override_limit']})")
    
    # Create override
    insert_query = """
        INSERT INTO injury_overrides (customer_id, player_id, games_override, notes)
        VALUES (%s, %s, %s, %s)
        RETURNING *
    """
    
    results = db.execute_query(
        insert_query,
        (customer['customer_id'], override.player_id, override.games_override, override.notes)
    )
    
    return {"message": "Override created", "override": results[0] if results else None}


@app.delete("/overrides/{player_id}")
async def delete_override(player_id: int, x_api_key: str = Header(...)):
    """Delete injury override"""
    customer = verify_api_key(x_api_key)
    
    query = """
        UPDATE injury_overrides
        SET is_active = FALSE
        WHERE customer_id = %s
        AND player_id = %s
    """
    
    db.execute_query(query, (customer['customer_id'], player_id), fetch=False)
    
    return {"message": "Override deleted"}


# ============================================
# WEEKLY TRACKING ENDPOINTS (Pro/Enterprise)
# ============================================

@app.post("/leagues/{league_id}/save-week")
async def save_week(league_id: str, x_api_key: str = Header(...), week_number: Optional[int] = None):
    """Save current week performance"""
    customer = verify_api_key(x_api_key)
    
    if customer['tier'] == 'free':
        raise HTTPException(status_code=403, detail="Weekly tracking requires Pro or Enterprise tier")
    
    # Get current score
    score_response = await get_league_score(league_id, x_api_key)
    
    # Determine week number
    if week_number is None:
        from datetime import datetime
        week_number = datetime.now().isocalendar()[1]
    
    # Get roster
    roster = league_db.get_roster(league_id, customer['customer_id'])
    
    # Save performance
    saved = weekly.save_week_performance(
        league_id,
        customer['customer_id'],
        week_number,
        score_response['score'].get('category_results', {}),
        [{"player_id": p['player_id'], "player_name": p['player_name']} for p in roster]
    )
    
    return {"message": "Week saved", "performance": saved}


@app.get("/leagues/{league_id}/history")
async def get_history(league_id: str, x_api_key: str = Header(...), weeks: int = 10):
    """Get performance history"""
    customer = verify_api_key(x_api_key)
    
    if customer['tier'] == 'free':
        raise HTTPException(status_code=403, detail="Weekly tracking requires Pro or Enterprise tier")
    
    history = weekly.get_performance_history(league_id, customer['customer_id'], weeks)
    
    summary = weekly.get_performance_summary(league_id, customer['customer_id'])
    
    return {
        "league_id": league_id,
        "weeks_tracked": summary['weeks_tracked'],
        "history": history
    }


@app.get("/leagues/{league_id}/trends/{category}")
async def get_trend(league_id: str, category: str, x_api_key: str = Header(...), weeks: int = 10):
    """Get category trend analysis"""
    customer = verify_api_key(x_api_key)
    
    if customer['tier'] == 'free':
        raise HTTPException(status_code=403, detail="Weekly tracking requires Pro or Enterprise tier")
    
    trend = weekly.get_category_trend(league_id, customer['customer_id'], category, weeks)
    
    return trend


@app.get("/leagues/{league_id}/compare-weeks")
async def compare_weeks(league_id: str, x_api_key: str = Header(...), week1: int = 1, week2: int = 2):
    """Compare two weeks"""
    customer = verify_api_key(x_api_key)
    
    if customer['tier'] == 'free':
        raise HTTPException(status_code=403, detail="Weekly tracking requires Pro or Enterprise tier")
    
    comparison = weekly.compare_weeks(league_id, customer['customer_id'], week1, week2)
    
    return comparison


# ============================================
# LINEUP OPTIMIZATION ENDPOINT (Pro/Enterprise)
# ============================================

@app.get("/leagues/{league_id}/optimize-lineup")
async def optimize_lineup_endpoint(league_id: str, x_api_key: str = Header(...)):
    """Optimize starting lineup"""
    customer = verify_api_key(x_api_key)
    
    if customer['tier'] == 'free':
        raise HTTPException(status_code=403, detail="Lineup optimizer requires Pro or Enterprise tier")
    
    # Get league and roster
    league = league_db.get_league(league_id, customer['customer_id'])
    if not league:
        raise HTTPException(status_code=404, detail="League not found")
    
    roster = league_db.get_roster(league_id, customer['customer_id'])
    
    # Get projections
    roster_with_projections = []
    for player in roster:
        if customer['can_access_current_season']:
            proj = nba.calculate_current_season_projection(player['player_id'])
        else:
            proj = nba.calculate_5year_average(player['player_id'])
        
        if proj:
            proj['player_id'] = player['player_id']
            proj['player_name'] = player['player_name']
            proj['player_position'] = player['player_position']
            roster_with_projections.append(proj)
    
    # Get position requirements
    position_requirements = json.loads(league['position_requirements']) if isinstance(league['position_requirements'], str) else league['position_requirements']
    
    # Optimize
    optimized = lineup.optimize_lineup(
        roster_with_projections,
        position_requirements,
        league['scoring_type']
    )
    
    return {
        "league_id": league_id,
        "optimized_lineup": optimized
    }


# ============================================
# STREAMING OPTIMIZER ENDPOINTS (Pro/Enterprise)
# ============================================

@app.get("/leagues/{league_id}/streaming-candidates")
async def get_streaming_candidates(league_id: str, x_api_key: str = Header(...), limit: int = 20):
    """Get streaming candidates"""
    customer = verify_api_key(x_api_key)
    
    if customer['tier'] == 'free':
        raise HTTPException(status_code=403, detail="Streaming optimizer requires Pro or Enterprise tier")
    
    # Get league needs
    league = league_db.get_league(league_id, customer['customer_id'])
    if not league:
        raise HTTPException(status_code=404, detail="League not found")
    
    roster = league_db.get_roster(league_id, customer['customer_id'])
    
    # Determine league needs (simplified)
    if league['scoring_type'] == 'roto':
        gap_response = await get_gap_analysis(league_id, x_api_key)
        needs = [cat['category'] for cat in gap_response['gap_analysis']['needs_help'][:3]]
    else:
        needs = ['PTS', 'REB', 'AST']
    
    # Get available players (simplified)
    all_players = nba.get_all_players()
    roster_ids = [p['player_id'] for p in roster]
    
    available = []
    for player_data in all_players[:200]:
        if player_data['id'] not in roster_ids:
            proj = nba.calculate_5year_average(player_data['id'])
            if proj:
                proj['player_name'] = player_data['full_name']
                proj['team'] = ''
                available.append(proj)
    
    # Get roster projections
    roster_projections = []
    for player in roster:
        proj = nba.calculate_5year_average(player['player_id'])
        if proj:
            proj['player_name'] = player['player_name']
            roster_projections.append(proj)
    
    # Get streaming candidates
    candidates = streaming.get_streaming_candidates(
        available,
        roster_projections,
        needs
    )
    
    return {
        "league_id": league_id,
        **candidates
    }


@app.get("/leagues/{league_id}/hot-pickups")
async def get_hot_pickups(league_id: str, x_api_key: str = Header(...), limit: int = 20):
    """Get hot pickup candidates"""
    customer = verify_api_key(x_api_key)
    
    if customer['tier'] == 'free':
        raise HTTPException(status_code=403, detail="Streaming optimizer requires Pro or Enterprise tier")
    
    # Get available players
    roster = league_db.get_roster(league_id, customer['customer_id'])
    roster_ids = [p['player_id'] for p in roster]
    
    all_players = nba.get_all_players()
    
    available = []
    for player_data in all_players[:200]:
        if player_data['id'] not in roster_ids:
            proj = nba.calculate_5year_average(player_data['id'])
            if proj:
                proj['player_name'] = player_data['full_name']
                proj['team'] = ''
                available.append(proj)
    
    hot_pickups = streaming.get_hot_pickups(available, limit)
    
    return {
        "league_id": league_id,
        "hot_pickups": hot_pickups
    }


@app.get("/leagues/{league_id}/schedule-advantage")
async def get_schedule_advantage(league_id: str, x_api_key: str = Header(...)):
    """Get players with schedule advantages"""
    customer = verify_api_key(x_api_key)
    
    if customer['tier'] == 'free':
        raise HTTPException(status_code=403, detail="Streaming optimizer requires Pro or Enterprise tier")
    
    # Get available players
    roster = league_db.get_roster(league_id, customer['customer_id'])
    roster_ids = [p['player_id'] for p in roster]
    
    all_players = nba.get_all_players()
    
    available = []
    for player_data in all_players[:200]:
        if player_data['id'] not in roster_ids:
            proj = nba.calculate_5year_average(player_data['id'])
            if proj:
                proj['player_name'] = player_data['full_name']
                proj['team'] = ''
                available.append(proj)
    
    schedule_players = streaming.get_schedule_advantage_players(available)
    
    return {
        "league_id": league_id,
        "schedule_advantage_players": schedule_players
    }


# ============================================
# OPPONENT ANALYSIS ENDPOINT (Pro/Enterprise)
# ============================================

@app.post("/leagues/{league_id}/analyze-matchup")
async def analyze_matchup(league_id: str, matchup: MatchupAnalyze, x_api_key: str = Header(...)):
    """Analyze H2H matchup"""
    customer = verify_api_key(x_api_key)
    
    if customer['tier'] == 'free':
        raise HTTPException(status_code=403, detail="Opponent analysis requires Pro or Enterprise tier")
    
    # Get league
    league = league_db.get_league(league_id, customer['customer_id'])
    if not league:
        raise HTTPException(status_code=404, detail="League not found")
    
    # Get my roster projections
    roster = league_db.get_roster(league_id, customer['customer_id'])
    
    my_projections = []
    for player in roster:
        if customer['can_access_current_season']:
            proj = nba.calculate_current_season_projection(player['player_id'])
        else:
            proj = nba.calculate_5year_average(player['player_id'])
        
        if proj:
            proj['player_name'] = player['player_name']
            my_projections.append(proj)
    
    # Get opponent projections
    opponent_projections = []
    for player_id in matchup.opponent_player_ids:
        if customer['can_access_current_season']:
            proj = nba.calculate_current_season_projection(player_id)
        else:
            proj = nba.calculate_5year_average(player_id)
        
        if proj:
            opponent_projections.append(proj)
    
    # Parse league config
    league_config = {
        'scoring_type': league['scoring_type'],
        'categories': league['categories'],
        'games_per_week': league['games_per_week']
    }
    
    if league['scoring_type'] == 'h2h_points':
        league_config['points_values'] = json.loads(league['points_values']) if isinstance(league['points_values'], str) else league['points_values']
    
    # Analyze
    analysis = opponent.analyze_h2h_matchup(
        my_projections,
        opponent_projections,
        league_config
    )
    
    return analysis


# ============================================
# TRADE ANALYZER ENDPOINTS (Pro/Enterprise)
# ============================================

@app.post("/leagues/{league_id}/analyze-trade")
async def analyze_trade_endpoint(league_id: str, trade_data: TradeAnalyze, x_api_key: str = Header(...)):
    """Analyze a trade proposal"""
    customer = verify_api_key(x_api_key)
    
    if customer['tier'] == 'free':
        raise HTTPException(status_code=403, detail="Trade analyzer requires Pro or Enterprise tier")
    
    # Get league
    league = league_db.get_league(league_id, customer['customer_id'])
    if not league:
        raise HTTPException(status_code=404, detail="League not found")
    
    # Get current roster
    roster = league_db.get_roster(league_id, customer['customer_id'])
    
    current_roster = []
    for player in roster:
        proj = nba.calculate_5year_average(player['player_id'])
        if proj:
            proj['player_id'] = player['player_id']
            proj['player_name'] = player['player_name']
            proj['player_position'] = player['player_position']
            current_roster.append(proj)
    
    # Get projections for trade players
    giving_projections = []
    for player_id in trade_data.giving:
        proj = nba.calculate_5year_average(player_id)
        if proj:
            proj['player_id'] = player_id
            giving_projections.append(proj)
    
    receiving_projections = []
    for player_id in trade_data.receiving:
        proj = nba.calculate_5year_average(player_id)
        if proj:
            proj['player_id'] = player_id
            receiving_projections.append(proj)
    
    # League config
    league_config = {
        'scoring_type': league['scoring_type'],
        'categories': league['categories'],
        'games_per_week': league['games_per_week']
    }
    
    # Analyze
    analysis = trade.analyze_trade(
        giving_projections,
        receiving_projections,
        current_roster,
        league_config
    )
    
    return analysis


@app.post("/leagues/{league_id}/compare-trades")
async def compare_trades_endpoint(league_id: str, trades: TradeCompare, x_api_key: str = Header(...)):
    """Compare multiple trade offers"""
    customer = verify_api_key(x_api_key)
    
    if customer['tier'] == 'free':
        raise HTTPException(status_code=403, detail="Trade analyzer requires Pro or Enterprise tier")
    
    # Get league and roster
    league = league_db.get_league(league_id, customer['customer_id'])
    if not league:
        raise HTTPException(status_code=404, detail="League not found")
    
    roster = league_db.get_roster(league_id, customer['customer_id'])
    
    current_roster = []
    for player in roster:
        proj = nba.calculate_5year_average(player['player_id'])
        if proj:
            proj['player_id'] = player['player_id']
            proj['player_name'] = player['player_name']
            current_roster.append(proj)
    
    # Parse trade offers
    trade_offers = []
    for offer in trades.trades:
        giving_projs = []
        for pid in offer['giving']:
            proj = nba.calculate_5year_average(pid)
            if proj:
                proj['player_id'] = pid
                giving_projs.append(proj)
        
        receiving_projs = []
        for pid in offer['receiving']:
            proj = nba.calculate_5year_average(pid)
            if proj:
                proj['player_id'] = pid
                receiving_projs.append(proj)
        
        trade_offers.append({
            'offer_id': offer.get('offer_id', 'unknown'),
            'giving': giving_projs,
            'receiving': receiving_projs
        })
    
    # League config
    league_config = {
        'scoring_type': league['scoring_type'],
        'categories': league['categories'],
        'games_per_week': league['games_per_week']
    }
    
    # Compare
    comparisons = trade.compare_trades(trade_offers, current_roster, league_config)
    
    return {
        "league_id": league_id,
        "trade_comparisons": comparisons
    }


# ============================================
# WATCHLIST ENDPOINTS
# ============================================

@app.get("/leagues/{league_id}/watchlist")
async def get_watchlist(league_id: str, x_api_key: str = Header(...)):
    """Get watchlist"""
    customer = verify_api_key(x_api_key)
    
    watchlist = league_db.get_watchlist(league_id, customer['customer_id'])
    
    return {"league_id": league_id, "watchlist": watchlist, "count": len(watchlist)}


@app.post("/leagues/{league_id}/watchlist")
async def add_to_watchlist(league_id: str, player: WatchlistAdd, x_api_key: str = Header(...)):
    """Add player to watchlist"""
    customer = verify_api_key(x_api_key)
    
    added = league_db.add_to_watchlist(
        league_id,
        customer['customer_id'],
        player.player_id,
        player.player_name,
        notes=player.notes,
        priority=player.priority
    )
    
    return {"message": "Player added to watchlist", "watchlist_entry": added}


@app.delete("/leagues/{league_id}/watchlist/{player_id}")
async def remove_from_watchlist(league_id: str, player_id: int, x_api_key: str = Header(...)):
    """Remove player from watchlist"""
    customer = verify_api_key(x_api_key)
    
    success = league_db.remove_from_watchlist(league_id, customer['customer_id'], player_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Player not found in watchlist")
    
    return {"message": "Player removed from watchlist"}


# ============================================
# DEBUG ENDPOINTS
# ============================================

@app.get("/debug/my-logs")
async def get_my_logs(x_api_key: str = Header(...), hours: int = 24, limit: int = 100):
    """Get my API logs"""
    customer = verify_api_key(x_api_key)
    
    logs = logger.get_customer_logs(customer['customer_id'], hours, limit)
    
    return {
        "customer_id": customer['customer_id'],
        "hours": hours,
        "log_count": len(logs),
        "logs": logs
    }


@app.get("/debug/recent-errors")
async def get_my_errors(x_api_key: str = Header(...), hours: int = 24, limit: int = 50):
    """Get my recent errors"""
    customer = verify_api_key(x_api_key)
    
    errors = logger.get_customer_errors(customer['customer_id'], hours, limit)
    
    return {
        "customer_id": customer['customer_id'],
        "hours": hours,
        "error_count": len(errors),
        "errors": errors
    }


@app.get("/debug/slow-requests")
async def get_my_slow_requests(x_api_key: str = Header(...), threshold_ms: int = 1000, limit: int = 50):
    """Get my slow requests"""
    customer = verify_api_key(x_api_key)
    
    slow_requests = logger.get_slow_requests(customer['customer_id'], threshold_ms, limit)
    
    return {
        "threshold_ms": threshold_ms,
        "slow_request_count": len(slow_requests),
        "slow_requests": slow_requests
    }


@app.get("/debug/endpoint-stats/{endpoint:path}")
async def get_endpoint_statistics(endpoint: str, x_api_key: str = Header(...), hours: int = 24):
    """Get statistics for an endpoint"""
    customer = verify_api_key(x_api_key)
    
    stats = logger.get_endpoint_stats(f"/{endpoint}", hours)
    
    return {
        "endpoint": f"/{endpoint}",
        "hours": hours,
        "stats": stats
    }


@app.get("/debug/search")
async def search_my_logs(q: str, x_api_key: str = Header(...), limit: int = 100):
    """Search my logs"""
    customer = verify_api_key(x_api_key)
    
    results = logger.search_logs(customer['customer_id'], q, limit)
    
    return {
        "query": q,
        "result_count": len(results),
        "results": results
    }


@app.get("/debug/dashboard")
async def get_debug_dashboard(x_api_key: str = Header(...), hours: int = 24):
    """Get debug dashboard summary"""
    customer = verify_api_key(x_api_key)
    
    logs = logger.get_customer_logs(customer['customer_id'], hours, 1000)
    errors = logger.get_customer_errors(customer['customer_id'], hours, 100)
    
    # Calculate summary
    total_requests = len(logs)
    successful = sum(1 for log in logs if log.get('response_status_code', 500) < 400)
    failed = total_requests - successful
    
    avg_response_time = sum(log.get('response_time_ms', 0) for log in logs) / total_requests if total_requests > 0 else 0
    
    # Endpoint breakdown
    endpoint_counts = {}
    for log in logs:
        endpoint = log.get('endpoint', 'unknown')
        endpoint_counts[endpoint] = endpoint_counts.get(endpoint, 0) + 1
    
    # Error breakdown
    error_codes = {}
    for error in errors:
        code = error.get('response_status_code', 500)
        error_codes[str(code)] = error_codes.get(str(code), 0) + 1
    
    return {
        "customer_id": customer['customer_id'],
        "customer_tier": customer['tier'],
        "time_period_hours": hours,
        "summary": {
            "total_requests": total_requests,
            "successful_requests": successful,
            "failed_requests": failed,
            "success_rate": round((successful / total_requests * 100), 2) if total_requests > 0 else 0,
            "avg_response_time_ms": round(avg_response_time, 0)
        },
        "endpoint_breakdown": dict(sorted(endpoint_counts.items(), key=lambda x: x[1], reverse=True)[:10]),
        "error_breakdown": error_codes,
        "recent_errors": errors[:5],
        "slowest_requests": sorted(logs, key=lambda x: x.get('response_time_ms', 0), reverse=True)[:5]
    }


# ============================================
# ADMIN ENDPOINTS (Enterprise only)
# ============================================

@app.get("/admin/error-summary")
async def get_error_summary(x_api_key: str = Header(...), status: str = "active", limit: int = 50):
    """Get system-wide error summary (Enterprise only)"""
    customer = verify_api_key(x_api_key)
    
    if customer['tier'] != 'enterprise':
        raise HTTPException(status_code=403, detail="Admin endpoints require Enterprise tier")
    
    query = """
        SELECT * FROM api_errors
        WHERE status = %s
        ORDER BY occurrence_count DESC
        LIMIT %s
    """
    
    errors = db.execute_query(query, (status, limit))
    
    return {
        "status": status,
        "error_count": len(errors) if errors else 0,
        "errors": errors if errors else []
    }


@app.get("/admin/slow-queries")
async def get_system_slow_queries(x_api_key: str = Header(...), threshold_ms: int = 1000, limit: int = 100):
    """Get system-wide slow queries (Enterprise only)"""
    customer = verify_api_key(x_api_key)
    
    if customer['tier'] != 'enterprise':
        raise HTTPException(status_code=403, detail="Admin endpoints require Enterprise tier")
    
    query = """
        SELECT * FROM api_debug_log
        WHERE response_time_ms > %s
        ORDER BY response_time_ms DESC
        LIMIT %s
    """
    
    slow_queries = db.execute_query(query, (threshold_ms, limit))
    
    return {
        "threshold_ms": threshold_ms,
        "slow_query_count": len(slow_queries) if slow_queries else 0,
        "slow_queries": slow_queries if slow_queries else []
    }


@app.post("/admin/resolve-error/{error_id}")
async def resolve_error(error_id: int, x_api_key: str = Header(...), notes: Optional[str] = None):
    """Mark error as resolved (Enterprise only)"""
    customer = verify_api_key(x_api_key)
    
    if customer['tier'] != 'enterprise':
        raise HTTPException(status_code=403, detail="Admin endpoints require Enterprise tier")
    
    query = """
        UPDATE api_errors
        SET status = 'resolved',
            resolution_notes = %s,
            resolved_at = CURRENT_TIMESTAMP
        WHERE error_id = %s
    """
    
    db.execute_query(query, (notes, error_id), fetch=False)
    
    return {"message": "Error marked as resolved", "error_id": error_id}


@app.get("/admin/recent-logs")
async def get_system_logs(
    x_api_key: str = Header(...),
    customer_id: Optional[str] = None,
    status_code: Optional[int] = None,
    minutes: int = 60,
    limit: int = 100
):
    """Get system-wide recent logs (Enterprise only)"""
    customer = verify_api_key(x_api_key)
    
    if customer['tier'] != 'enterprise':
        raise HTTPException(status_code=403, detail="Admin endpoints require Enterprise tier")
    
    conditions = [f"request_timestamp > NOW() - INTERVAL '{minutes} minutes'"]
    params = []
    
    if customer_id:
        conditions.append("customer_id = %s")
        params.append(customer_id)
    
    if status_code:
        conditions.append("response_status_code = %s")
        params.append(status_code)
    
    params.append(limit)
    
    query = f"""
        SELECT * FROM api_debug_log
        WHERE {' AND '.join(conditions)}
        ORDER BY request_timestamp DESC
        LIMIT %s
    """
    
    logs = db.execute_query(query, tuple(params))
    
    return {
        "minutes": minutes,
        "log_count": len(logs) if logs else 0,
        "logs": logs if logs else []
    }


@app.post("/admin/cleanup-logs")
async def cleanup_logs(x_api_key: str = Header(...), days: int = 30):
    """Clean up old logs (Enterprise only)"""
    customer = verify_api_key(x_api_key)
    
    if customer['tier'] != 'enterprise':
        raise HTTPException(status_code=403, detail="Admin endpoints require Enterprise tier")
    
    result = logger.cleanup_old_logs(days)
    
    return {
        "message": "Old logs cleaned up",
        "days": days,
        "deleted": result
    }


# ============================================
# MODEL TRAINING ENDPOINT (Enterprise only)
# ============================================

@app.post("/train")
async def train_custom_model(x_api_key: str = Header(...)):
    """Train custom projection model (Enterprise only)"""
    customer = verify_api_key(x_api_key)
    
    if not customer['can_train_models']:
        raise HTTPException(status_code=403, detail="Custom model training requires Enterprise tier")
    
    # Log training request
    query = """
        INSERT INTO model_training_logs (customer_id, model_type, status)
        VALUES (%s, %s, %s)
        RETURNING *
    """
    
    result = db.execute_query(query, (customer['customer_id'], 'custom_projections', 'running'))
    
    return {
        "message": "Model training started",
        "training_log": result[0] if result else None,
        "note": "This is a placeholder - actual model training would be implemented here"
    }


# ============================================
# RUN SERVER
# ============================================

if __name__ == "__main__":
    print("=" * 60)
    print("🏀 NBA Fantasy Basketball Platform API")
    print("=" * 60)
    print("✅ Starting server on http://0.0.0.0:8000")
    print("📚 API Documentation: http://localhost:8000/docs")
    print("🔧 Health Check: http://localhost:8000/health")
    print("=" * 60)
    
    uvicorn.run(app, host="0.0.0.0", port=8000)