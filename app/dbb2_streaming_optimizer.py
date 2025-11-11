"""
NBA Fantasy Basketball Platform - Streaming Optimizer
Daily add/drop suggestions for maximizing weekly production
"""

from typing import Dict, Any, List
import logging

logger = logging.getLogger(__name__)


def get_streaming_candidates(
    available_players: List[Dict[str, Any]],
    roster_players: List[Dict[str, Any]],
    league_needs: List[str],
    games_remaining_this_week: Dict[int, int] = None
) -> Dict[str, Any]:
    """
    Find best streaming candidates
    
    Args:
        available_players: Available free agents with projections
        roster_players: Current roster with projections
        league_needs: Categories that need help
        games_remaining_this_week: Dict of player_id -> games remaining
        
    Returns:
        Streaming candidates and suggestions
    """
    
    # Calculate streaming value for each available player
    streaming_candidates = []
    
    for player in available_players:
        games_left = games_remaining_this_week.get(player['player_id'], 3) if games_remaining_this_week else 3
        
        # Calculate value for league needs
        value = calculate_streaming_value(player, league_needs, games_left)
        
        streaming_candidates.append({
            'player_id': player['player_id'],
            'player_name': player.get('player_name', 'Unknown'),
            'team': player.get('team', ''),
            'games_remaining': games_left,
            'streaming_value': round(value, 1),
            'per_game_value': round(value / games_left, 1) if games_left > 0 else 0,
            'projection': player
        })
    
    # Sort by streaming value
    streaming_candidates.sort(key=lambda x: x['streaming_value'], reverse=True)
    
    # Generate streaming suggestions (who to drop)
    suggestions = generate_streaming_suggestions(
        streaming_candidates[:20],
        roster_players,
        games_remaining_this_week
    )
    
    return {
        'league_needs': league_needs,
        'streaming_candidates': streaming_candidates[:20],
        'streaming_suggestions': suggestions
    }


def calculate_streaming_value(
    player: Dict[str, Any],
    league_needs: List[str],
    games_remaining: int
) -> float:
    """
    Calculate streaming value based on league needs
    
    Args:
        player: Player with projections
        league_needs: Categories needed
        games_remaining: Games left this week
        
    Returns:
        Streaming value score
    """
    
    value = 0.0
    
    # Category weights (higher for needs)
    category_mapping = {
        'PTS': ('points_per_game', 1.0),
        'REB': ('rebounds_per_game', 1.5),
        'AST': ('assists_per_game', 1.5),
        'STL': ('steals_per_game', 4.0),
        'BLK': ('blocks_per_game', 4.0),
        '3PM': ('three_pointers_made', 3.0),
        'FG_PCT': ('field_goal_percentage', 50.0),
        'FT_PCT': ('free_throw_percentage', 30.0)
    }
    
    for category in league_needs:
        if category in category_mapping:
            proj_key, weight = category_mapping[category]
            stat_value = player.get(proj_key, 0)
            
            # Double weight for categories we need
            value += stat_value * weight * 2.0
    
    # Add base value for all other stats
    value += player.get('points_per_game', 0) * 0.5
    value += player.get('rebounds_per_game', 0) * 0.8
    value += player.get('assists_per_game', 0) * 0.8
    
    # Multiply by games remaining
    value *= games_remaining
    
    return value


def generate_streaming_suggestions(
    streaming_candidates: List[Dict[str, Any]],
    roster_players: List[Dict[str, Any]],
    games_remaining_this_week: Dict[int, int] = None
) -> List[Dict[str, Any]]:
    """
    Generate add/drop suggestions
    
    Args:
        streaming_candidates: Top streaming options
        roster_players: Current roster
        games_remaining_this_week: Games remaining dict
        
    Returns:
        List of streaming suggestions
    """
    
    suggestions = []
    
    # Calculate remaining value for roster players
    for roster_player in roster_players:
        games_left = games_remaining_this_week.get(roster_player['player_id'], 2) if games_remaining_this_week else 2
        roster_player['games_remaining'] = games_left
        roster_player['remaining_value'] = calculate_base_value(roster_player) * games_left
    
    # Sort roster by remaining value (lowest first)
    roster_players.sort(key=lambda x: x['remaining_value'])
    
    # Match streaming candidates with drop targets
    for candidate in streaming_candidates[:10]:
        for roster_player in roster_players[:5]:  # Consider bottom 5 roster players
            
            # Only suggest if streaming candidate has significantly more value
            if candidate['streaming_value'] > roster_player['remaining_value'] * 1.5:
                suggestions.append({
                    'type': 'stream',
                    'drop': {
                        'player_id': roster_player['player_id'],
                        'player_name': roster_player.get('player_name', 'Unknown'),
                        'games_remaining': roster_player['games_remaining'],
                        'remaining_value': round(roster_player['remaining_value'], 1)
                    },
                    'add': {
                        'player_id': candidate['player_id'],
                        'player_name': candidate['player_name'],
                        'games_remaining': candidate['games_remaining'],
                        'streaming_value': candidate['streaming_value']
                    },
                    'value_improvement': round(candidate['streaming_value'] - roster_player['remaining_value'], 1),
                    'reason': f"Add {candidate['player_name']} ({candidate['games_remaining']} games) for {roster_player.get('player_name', 'Unknown')} ({roster_player['games_remaining']} games)"
                })
                break  # Only one suggestion per candidate
    
    return suggestions[:5]  # Return top 5 suggestions


def calculate_base_value(player: Dict[str, Any]) -> float:
    """
    Calculate base per-game value
    
    Args:
        player: Player with projections
        
    Returns:
        Per-game value
    """
    
    return (
        player.get('points_per_game', 0) * 0.5 +
        player.get('rebounds_per_game', 0) * 1.5 +
        player.get('assists_per_game', 0) * 1.5 +
        player.get('steals_per_game', 0) * 4.0 +
        player.get('blocks_per_game', 0) * 4.0 +
        player.get('three_pointers_made', 0) * 3.0
    )


def get_hot_pickups(
    available_players: List[Dict[str, Any]],
    limit: int = 20
) -> List[Dict[str, Any]]:
    """
    Get hottest available players (trending up)
    
    Args:
        available_players: Available players with projections
        limit: Number of players to return
        
    Returns:
        List of hot pickup candidates
    """
    
    hot_pickups = []
    
    for player in available_players:
        # Calculate "hotness" score
        hotness = calculate_hotness_score(player)
        
        hot_pickups.append({
            'player_id': player['player_id'],
            'player_name': player.get('player_name', 'Unknown'),
            'team': player.get('team', ''),
            'hotness_score': round(hotness, 1),
            'reason': determine_hot_reason(player),
            'projection': player
        })
    
    # Sort by hotness
    hot_pickups.sort(key=lambda x: x['hotness_score'], reverse=True)
    
    return hot_pickups[:limit]


def calculate_hotness_score(player: Dict[str, Any]) -> float:
    """
    Calculate how "hot" a player is
    
    Args:
        player: Player with projections
        
    Returns:
        Hotness score (0-100)
    """
    
    # High minutes = playing well
    minutes = player.get('minutes_per_game', 0)
    minutes_score = min(minutes / 35 * 40, 40)
    
    # High usage = productive
    points = player.get('points_per_game', 0)
    usage_score = min(points / 25 * 30, 30)
    
    # Well-rounded stats = valuable
    categories_filled = 0
    if player.get('rebounds_per_game', 0) >= 5:
        categories_filled += 1
    if player.get('assists_per_game', 0) >= 4:
        categories_filled += 1
    if player.get('steals_per_game', 0) >= 1:
        categories_filled += 1
    if player.get('blocks_per_game', 0) >= 0.8:
        categories_filled += 1
    if player.get('three_pointers_made', 0) >= 2:
        categories_filled += 1
    
    versatility_score = categories_filled * 6
    
    return minutes_score + usage_score + versatility_score


def determine_hot_reason(player: Dict[str, Any]) -> str:
    """
    Determine why player is hot
    
    Args:
        player: Player with projections
        
    Returns:
        Reason string
    """
    
    reasons = []
    
    if player.get('minutes_per_game', 0) >= 30:
        reasons.append("High minutes")
    if player.get('points_per_game', 0) >= 20:
        reasons.append("High scoring")
    if player.get('rebounds_per_game', 0) >= 8:
        reasons.append("Strong rebounding")
    if player.get('assists_per_game', 0) >= 6:
        reasons.append("Great playmaker")
    if player.get('steals_per_game', 0) >= 1.5:
        reasons.append("Defensive stats")
    
    if not reasons:
        return "Healthy and producing at high level"
    
    return " + ".join(reasons)


def get_schedule_advantage_players(
    available_players: List[Dict[str, Any]],
    team_schedules: Dict[str, int] = None
) -> List[Dict[str, Any]]:
    """
    Find players with schedule advantages (4+ games this week)
    
    Args:
        available_players: Available players
        team_schedules: Dict of team -> games this week
        
    Returns:
        Players with schedule advantage
    """
    
    if not team_schedules:
        # Default: all teams have 3-4 games
        team_schedules = {}
    
    schedule_players = []
    
    for player in available_players:
        team = player.get('team', '')
        games_next_week = team_schedules.get(team, 3)
        
        if games_next_week >= 4:
            value = calculate_base_value(player) * games_next_week
            
            schedule_players.append({
                'player_id': player['player_id'],
                'player_name': player.get('player_name', 'Unknown'),
                'team': team,
                'games_next_week': games_next_week,
                'schedule_reason': f"{games_next_week} games in 5 nights",
                'projected_value': round(value, 1)
            })
    
    # Sort by projected value
    schedule_players.sort(key=lambda x: x['projected_value'], reverse=True)
    
    return schedule_players[:20]
