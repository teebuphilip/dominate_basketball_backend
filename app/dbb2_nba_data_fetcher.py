"""
NBA Fantasy Basketball Platform - NBA Data Fetcher
Fetches player data and calculates projections using nba-api
"""

from nba_api.stats.static import players, teams
from nba_api.stats.endpoints import playercareerstats, commonplayerinfo
import pandas as pd
import numpy as np
from typing import Dict, Any, Optional, List
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


# Age-based performance curves
def get_age_factor(age: int) -> float:
    """
    Calculate age-based performance adjustment factor
    Prime years: 24-29 (factor = 1.0)
    Early career: 20-23 (gradual improvement)
    Decline: 30+ (gradual decline)
    
    Args:
        age: Player's age
        
    Returns:
        Performance adjustment factor (0.7 to 1.0)
    """
    if age < 20:
        return 0.75
    elif age <= 23:
        # Improvement phase: 0.85 at 20, 0.95 at 23
        return 0.85 + (age - 20) * 0.033
    elif age <= 29:
        # Prime years
        return 1.0
    elif age <= 35:
        # Decline phase: 0.95 at 30, 0.75 at 35
        return 1.0 - (age - 29) * 0.04
    else:
        # Severe decline
        return max(0.7, 1.0 - (age - 29) * 0.05)


def get_injury_risk_factor(age: int) -> float:
    """
    Calculate injury risk as inverted bell curve
    Lowest risk: 24-27
    Higher risk: younger and older players
    
    Args:
        age: Player's age
        
    Returns:
        Injury risk factor (0.0 to 1.0, higher = more risk)
    """
    if age <= 22:
        # Young players: moderate risk
        return 0.3 + (22 - age) * 0.05
    elif age <= 27:
        # Prime years: lowest risk
        return 0.2
    else:
        # Older players: increasing risk
        return min(0.8, 0.2 + (age - 27) * 0.06)


def predict_games_played(minutes_per_game: float, age: int, position: str) -> int:
    """
    Predict games played based on usage and injury risk
    
    Args:
        minutes_per_game: Average minutes per game
        age: Player's age
        position: Player position
        
    Returns:
        Predicted games played
    """
    # Base games (82 game season)
    base_games = 82
    
    # Minutes factor (high usage = more injury risk)
    if minutes_per_game >= 35:
        minutes_factor = 0.85
    elif minutes_per_game >= 30:
        minutes_factor = 0.90
    elif minutes_per_game >= 25:
        minutes_factor = 0.95
    else:
        minutes_factor = 1.0
    
    # Age-based injury risk
    injury_risk = get_injury_risk_factor(age)
    injury_factor = 1.0 - (injury_risk * 0.15)  # Max 15% reduction
    
    # Position factor (big men get hurt more)
    position_factor = 0.92 if position in ['C', 'PF'] else 1.0
    
    predicted = int(base_games * minutes_factor * injury_factor * position_factor)
    
    return max(50, min(82, predicted))  # Clamp between 50-82


def get_all_players() -> List[Dict[str, Any]]:
    """
    Get all NBA players from nba-api
    
    Returns:
        List of player dictionaries
    """
    try:
        all_players = players.get_players()
        logger.info(f"✅ Fetched {len(all_players)} players from NBA API")
        return all_players
    except Exception as e:
        logger.error(f"❌ Failed to fetch players: {e}")
        return []


def get_player_info(player_id: int) -> Optional[Dict[str, Any]]:
    """
    Get detailed player information
    
    Args:
        player_id: NBA player ID
        
    Returns:
        Player info dictionary or None
    """
    try:
        player_info = commonplayerinfo.CommonPlayerInfo(player_id=player_id)
        df = player_info.get_data_frames()[0]
        
        if len(df) > 0:
            row = df.iloc[0]
            
            # Calculate age
            birthdate = pd.to_datetime(row.get('BIRTHDATE', ''))
            age = (datetime.now() - birthdate).days // 365 if pd.notna(birthdate) else 28
            
            return {
                'player_id': player_id,
                'player_name': row.get('DISPLAY_FIRST_LAST', ''),
                'team': row.get('TEAM_ABBREVIATION', ''),
                'position': row.get('POSITION', ''),
                'height': row.get('HEIGHT', ''),
                'weight': row.get('WEIGHT', 0),
                'age': age,
                'jersey_number': row.get('JERSEY', ''),
                'is_active': row.get('ROSTERSTATUS', '') == 'Active'
            }
    except Exception as e:
        logger.warning(f"⚠️ Failed to get info for player {player_id}: {e}")
    
    return None


def get_player_career_stats(player_id: int) -> pd.DataFrame:
    """
    Get player's career statistics
    
    Args:
        player_id: NBA player ID
        
    Returns:
        DataFrame with career stats by season
    """
    try:
        career = playercareerstats.PlayerCareerStats(player_id=player_id)
        df = career.get_data_frames()[0]
        
        # Filter to regular season only
        df = df[df['SEASON_ID'].str.startswith('2')]  # Regular season IDs start with '2'
        
        return df
    except Exception as e:
        logger.warning(f"⚠️ Failed to get career stats for player {player_id}: {e}")
        return pd.DataFrame()


def calculate_5year_average(player_id: int) -> Optional[Dict[str, Any]]:
    """
    Calculate 5-year average projections
    
    Args:
        player_id: NBA player ID
        
    Returns:
        Projection dictionary or None
    """
    try:
        df = get_player_career_stats(player_id)
        
        if df.empty or len(df) == 0:
            return None
        
        # Get last 5 seasons
        df = df.tail(5)
        
        if len(df) == 0:
            return None
        
        # Calculate per-game averages
        total_games = df['GP'].sum()
        
        if total_games == 0:
            return None
        
        projection = {
            'player_id': player_id,
            'games_played': df['GP'].mean(),
            'minutes_per_game': (df['MIN'].sum() / total_games) if total_games > 0 else 0,
            'points_per_game': (df['PTS'].sum() / total_games) if total_games > 0 else 0,
            'rebounds_per_game': (df['REB'].sum() / total_games) if total_games > 0 else 0,
            'assists_per_game': (df['AST'].sum() / total_games) if total_games > 0 else 0,
            'steals_per_game': (df['STL'].sum() / total_games) if total_games > 0 else 0,
            'blocks_per_game': (df['BLK'].sum() / total_games) if total_games > 0 else 0,
            'turnovers_per_game': (df['TOV'].sum() / total_games) if total_games > 0 else 0,
            'field_goals_made': (df['FGM'].sum() / total_games) if total_games > 0 else 0,
            'field_goals_attempted': (df['FGA'].sum() / total_games) if total_games > 0 else 0,
            'field_goal_percentage': (df['FG_PCT'].mean()) if len(df) > 0 else 0,
            'three_pointers_made': (df['FG3M'].sum() / total_games) if total_games > 0 else 0,
            'three_pointers_attempted': (df['FG3A'].sum() / total_games) if total_games > 0 else 0,
            'three_point_percentage': (df['FG3_PCT'].mean()) if len(df) > 0 else 0,
            'free_throws_made': (df['FTM'].sum() / total_games) if total_games > 0 else 0,
            'free_throws_attempted': (df['FTA'].sum() / total_games) if total_games > 0 else 0,
            'free_throw_percentage': (df['FT_PCT'].mean()) if len(df) > 0 else 0,
            'seasons_included': df['SEASON_ID'].tolist(),
            'confidence_score': min(len(df) / 5.0, 1.0)  # Higher confidence with more seasons
        }
        
        return projection
        
    except Exception as e:
        logger.error(f"❌ Failed to calculate 5-year average for player {player_id}: {e}")
        return None


def calculate_current_season_projection(player_id: int) -> Optional[Dict[str, Any]]:
    """
    Calculate current season projection with age-based adjustments
    
    Args:
        player_id: NBA player ID
        
    Returns:
        Projection dictionary or None
    """
    try:
        # Get 5-year baseline
        baseline = calculate_5year_average(player_id)
        
        if baseline is None:
            return None
        
        # Get player info for age
        player_info = get_player_info(player_id)
        
        if player_info is None:
            return None
        
        age = player_info.get('age', 28)
        position = player_info.get('position', 'G')
        
        # Apply age factor
        age_factor = get_age_factor(age)
        injury_risk = get_injury_risk_factor(age)
        
        # Adjust stats
        projection = {
            'player_id': player_id,
            'season': '2024-25',
            'games_played': predict_games_played(
                baseline['minutes_per_game'], 
                age, 
                position
            ),
            'minutes_per_game': baseline['minutes_per_game'] * age_factor,
            'points_per_game': baseline['points_per_game'] * age_factor,
            'rebounds_per_game': baseline['rebounds_per_game'] * age_factor,
            'assists_per_game': baseline['assists_per_game'] * age_factor,
            'steals_per_game': baseline['steals_per_game'] * age_factor,
            'blocks_per_game': baseline['blocks_per_game'] * age_factor,
            'turnovers_per_game': baseline['turnovers_per_game'] * age_factor,
            'field_goals_made': baseline['field_goals_made'] * age_factor,
            'field_goals_attempted': baseline['field_goals_attempted'] * age_factor,
            'field_goal_percentage': baseline['field_goal_percentage'],  # Don't adjust percentages
            'three_pointers_made': baseline['three_pointers_made'] * age_factor,
            'three_pointers_attempted': baseline['three_pointers_attempted'] * age_factor,
            'three_point_percentage': baseline['three_point_percentage'],
            'free_throws_made': baseline['free_throws_made'] * age_factor,
            'free_throws_attempted': baseline['free_throws_attempted'] * age_factor,
            'free_throw_percentage': baseline['free_throw_percentage'],
            'age_factor': age_factor,
            'injury_risk_factor': injury_risk,
            'model_version': 'v1.0',
            'confidence_score': baseline['confidence_score'] * (1.0 - injury_risk * 0.2)
        }
        
        return projection
        
    except Exception as e:
        logger.error(f"❌ Failed to calculate current season projection for player {player_id}: {e}")
        return None


def search_players(name: str) -> List[Dict[str, Any]]:
    """
    Search for players by name
    
    Args:
        name: Player name or partial name
        
    Returns:
        List of matching players
    """
    try:
        all_players = get_all_players()
        name_lower = name.lower()
        
        matches = [
            p for p in all_players 
            if name_lower in p['full_name'].lower()
        ]
        
        return matches[:20]  # Limit to 20 results
        
    except Exception as e:
        logger.error(f"❌ Failed to search players: {e}")
        return []


def get_team_players(team_abbr: str) -> List[int]:
    """
    Get all player IDs for a team
    
    Args:
        team_abbr: Team abbreviation (e.g., 'LAL', 'GSW')
        
    Returns:
        List of player IDs
    """
    try:
        all_players = get_all_players()
        
        # This is simplified - in production, you'd need current roster data
        # For now, return empty list (would need additional API calls)
        return []
        
    except Exception as e:
        logger.error(f"❌ Failed to get team players: {e}")
        return []
