"""
NBA Fantasy Basketball Platform - Opponent Analyzer
Predict H2H matchup outcomes and provide strategic recommendations
"""

from typing import Dict, Any, List
import logging
import dbb2_scoring_engine as scoring

logger = logging.getLogger(__name__)


def analyze_h2h_matchup(
    my_projections: List[Dict[str, Any]],
    opponent_projections: List[Dict[str, Any]],
    league_config: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Analyze H2H matchup and provide recommendations
    
    Args:
        my_projections: My roster projections
        opponent_projections: Opponent roster projections
        league_config: League configuration
        
    Returns:
        Matchup analysis with strategies
    """
    
    scoring_type = league_config.get('scoring_type', 'h2h_categories')
    
    if scoring_type == 'h2h_categories':
        return analyze_h2h_categories_matchup(
            my_projections,
            opponent_projections,
            league_config
        )
    elif scoring_type == 'h2h_points':
        return analyze_h2h_points_matchup(
            my_projections,
            opponent_projections,
            league_config
        )
    else:
        return {'error': 'Unsupported scoring type for matchup analysis'}


def analyze_h2h_categories_matchup(
    my_projections: List[Dict[str, Any]],
    opponent_projections: List[Dict[str, Any]],
    league_config: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Analyze H2H Categories matchup
    
    Args:
        my_projections: My roster projections
        opponent_projections: Opponent roster projections
        league_config: League configuration
        
    Returns:
        Detailed matchup analysis
    """
    
    categories = league_config.get('categories', [])
    games_per_week = league_config.get('games_per_week', 3.33)
    
    # Get basic matchup results
    matchup = scoring.calculate_h2h_categories(
        my_projections,
        opponent_projections,
        categories,
        games_per_week
    )
    
    # Generate strategic recommendations
    strategies = generate_category_strategies(matchup)
    
    matchup['strategy_recommendations'] = strategies
    
    return {'matchup_analysis': matchup}


def generate_category_strategies(matchup: Dict[str, Any]) -> List[str]:
    """
    Generate strategic recommendations for H2H Categories
    
    Args:
        matchup: Matchup results from scoring engine
        
    Returns:
        List of strategic recommendations
    """
    
    strategies = []
    
    close_categories = matchup.get('close_categories', [])
    blowout_categories = matchup.get('blowout_categories', [])
    category_breakdown = matchup.get('category_breakdown', [])
    
    # Focus on close categories you're losing
    close_losing = [c for c in close_categories if c['status'] == 'loss']
    if close_losing:
        cats = [c['category'] for c in close_losing]
        strategies.append(f"🎯 Focus on close categories you're losing: {', '.join(cats)}")
    
    # Protect narrow leads
    close_winning = [c for c in close_categories if c['status'] == 'win']
    if close_winning:
        cats = [c['category'] for c in close_winning]
        strategies.append(f"🛡️ Protect narrow leads in: {', '.join(cats)}")
    
    # Consider punting blowout losses
    blowout_losses = [c for c in blowout_categories if c['status'] == 'loss']
    if blowout_losses:
        cats = [c['category'] for c in blowout_losses]
        strategies.append(f"❌ Consider punting (giving up) categories: {', '.join(cats)}")
    
    # Maintain dominance in big wins
    blowout_wins = [c for c in blowout_categories if c['status'] == 'win']
    if blowout_wins:
        cats = [c['category'] for c in blowout_wins]
        strategies.append(f"✅ Dominating in: {', '.join(cats)} - maintain lead")
    
    # Overall strategy based on winning probability
    win_prob = matchup.get('winning_probability', 50)
    
    if win_prob >= 70:
        strategies.append("💪 Strong advantage - focus on consistency, avoid risky moves")
    elif win_prob >= 55:
        strategies.append("📊 Slight advantage - target close categories to secure win")
    elif win_prob >= 45:
        strategies.append("⚖️ Very close matchup - every category matters")
    elif win_prob >= 30:
        strategies.append("📈 Need to gain ground - target multiple close categories")
    else:
        strategies.append("🔥 Significant deficit - consider aggressive streaming for close cats")
    
    # Streaming recommendation
    if close_categories:
        strategies.append("📊 Consider streaming players strong in your close categories")
    
    return strategies


def analyze_h2h_points_matchup(
    my_projections: List[Dict[str, Any]],
    opponent_projections: List[Dict[str, Any]],
    league_config: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Analyze H2H Points matchup
    
    Args:
        my_projections: My roster projections
        opponent_projections: Opponent roster projections
        league_config: League configuration
        
    Returns:
        Points matchup analysis
    """
    
    points_values = league_config.get('points_values', {})
    games_per_week = league_config.get('games_per_week', 3.33)
    
    # Calculate points for both teams
    my_results = scoring.calculate_h2h_points(
        my_projections,
        points_values,
        games_per_week
    )
    
    opponent_results = scoring.calculate_h2h_points(
        opponent_projections,
        points_values,
        games_per_week
    )
    
    my_points = my_results['total_fantasy_points']
    opponent_points = opponent_results['total_fantasy_points']
    
    point_diff = my_points - opponent_points
    
    # Determine result
    if my_points > opponent_points:
        matchup_result = 'win'
        win_prob = min(95, 50 + (point_diff / opponent_points * 100))
    elif my_points < opponent_points:
        matchup_result = 'loss'
        win_prob = max(5, 50 - (abs(point_diff) / my_points * 100))
    else:
        matchup_result = 'tie'
        win_prob = 50
    
    # Generate strategies
    strategies = generate_points_strategies(my_points, opponent_points, point_diff)
    
    # Find top performers
    top_my_players = my_results['player_breakdown'][:5]
    top_opponent_players = opponent_results['player_breakdown'][:5]
    
    return {
        'matchup_analysis': {
            'matchup_result': matchup_result,
            'my_points': my_points,
            'opponent_points': opponent_points,
            'point_difference': round(point_diff, 1),
            'winning_probability': round(win_prob, 1),
            'my_top_performers': top_my_players,
            'opponent_top_performers': top_opponent_players,
            'strategy_recommendations': strategies
        }
    }


def generate_points_strategies(
    my_points: float,
    opponent_points: float,
    point_diff: float
) -> List[str]:
    """
    Generate strategies for H2H Points leagues
    
    Args:
        my_points: My projected points
        opponent_points: Opponent projected points
        point_diff: Point difference
        
    Returns:
        List of strategies
    """
    
    strategies = []
    
    diff_percent = abs(point_diff) / max(my_points, opponent_points) * 100
    
    if point_diff > 0:
        # Winning
        if diff_percent >= 20:
            strategies.append("✅ Large lead - focus on maintaining consistency")
            strategies.append("🛡️ Avoid risky adds, play it safe")
        elif diff_percent >= 10:
            strategies.append("📊 Solid lead - maintain your advantage")
            strategies.append("👀 Monitor opponent's moves")
        else:
            strategies.append("⚠️ Close lead - stay aggressive")
            strategies.append("🎯 Look for high-upside streaming options")
    else:
        # Losing
        if diff_percent >= 20:
            strategies.append("🔥 Significant deficit - need aggressive moves")
            strategies.append("📈 Target high-ceiling players on waiver wire")
            strategies.append("🎲 Consider risky but high-upside adds")
        elif diff_percent >= 10:
            strategies.append("📊 Behind but catchable - be strategic")
            strategies.append("🎯 Focus on players with heavy schedules")
        else:
            strategies.append("⚖️ Very close - every move matters")
            strategies.append("👀 Monitor daily adds/drops closely")
    
    strategies.append("💡 Consider players with 4+ games this week")
    
    return strategies


def predict_matchup_outcome(
    my_projections: List[Dict[str, Any]],
    opponent_projections: List[Dict[str, Any]],
    league_config: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Quick matchup prediction
    
    Args:
        my_projections: My roster projections
        opponent_projections: Opponent roster projections
        league_config: League configuration
        
    Returns:
        Win probability and summary
    """
    
    analysis = analyze_h2h_matchup(
        my_projections,
        opponent_projections,
        league_config
    )
    
    matchup = analysis['matchup_analysis']
    
    return {
        'predicted_result': matchup.get('matchup_result', 'unknown'),
        'winning_probability': matchup.get('winning_probability', 50),
        'confidence': 'High' if abs(matchup.get('winning_probability', 50) - 50) > 20 else 'Moderate',
        'key_insights': matchup.get('strategy_recommendations', [])[:3]
    }
