"""
NBA Fantasy Basketball Platform - Trade Analyzer
Evaluate multi-player trades and provide recommendations
"""

from typing import Dict, Any, List
import logging

logger = logging.getLogger(__name__)


def analyze_trade(
    giving_projections: List[Dict[str, Any]],
    receiving_projections: List[Dict[str, Any]],
    current_roster: List[Dict[str, Any]],
    league_config: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Analyze a trade proposal
    
    Args:
        giving_projections: Players you're giving away
        receiving_projections: Players you're receiving
        current_roster: Your current roster
        league_config: League configuration
        
    Returns:
        Complete trade analysis
    """
    
    # Calculate current roster value
    current_value = calculate_roster_value(current_roster, league_config)
    
    # Calculate post-trade roster
    post_trade_roster = [p for p in current_roster if p['player_id'] not in [g['player_id'] for g in giving_projections]]
    post_trade_roster.extend(receiving_projections)
    
    post_trade_value = calculate_roster_value(post_trade_roster, league_config)
    
    value_change = post_trade_value - current_value
    percent_change = (value_change / current_value * 100) if current_value > 0 else 0
    
    # Analyze category impact
    category_impact = analyze_category_impact(
        giving_projections,
        receiving_projections,
        current_roster,
        league_config
    )
    
    # Analyze positional impact
    positional_impact = analyze_positional_impact(
        giving_projections,
        receiving_projections
    )
    
    # Generate recommendation
    recommendation = generate_trade_recommendation(
        value_change,
        category_impact,
        positional_impact
    )
    
    # Calculate trade rating
    trade_rating = calculate_trade_rating(value_change, percent_change)
    
    return {
        'trade_analysis': {
            'trade_summary': {
                'giving': [{
                    'player_id': p['player_id'],
                    'player_name': p.get('player_name', 'Unknown')
                } for p in giving_projections],
                'receiving': [{
                    'player_id': p['player_id'],
                    'player_name': p.get('player_name', 'Unknown')
                } for p in receiving_projections]
            },
            'value_analysis': {
                'current_roster_value': round(current_value, 1),
                'post_trade_value': round(post_trade_value, 1),
                'value_change': round(value_change, 1),
                'percent_change': round(percent_change, 1)
            },
            'category_impact': category_impact,
            'positional_impact': positional_impact,
            'recommendation': recommendation,
            'trade_rating': trade_rating
        }
    }


def calculate_roster_value(
    roster: List[Dict[str, Any]],
    league_config: Dict[str, Any]
) -> float:
    """
    Calculate total roster value
    
    Args:
        roster: Roster with projections
        league_config: League configuration
        
    Returns:
        Total value score
    """
    
    scoring_type = league_config.get('scoring_type', 'roto')
    categories = league_config.get('categories', [])
    
    total_value = 0.0
    
    for player in roster:
        # Calculate per-category contributions
        for cat in categories:
            value = get_category_value(player, cat)
            total_value += value
    
    return total_value


def get_category_value(player: Dict[str, Any], category: str) -> float:
    """
    Get player's value in a specific category
    
    Args:
        player: Player with projections
        category: Category name
        
    Returns:
        Value score
    """
    
    category_mapping = {
        'PTS': ('points_per_game', 0.5),
        'REB': ('rebounds_per_game', 1.5),
        'AST': ('assists_per_game', 1.5),
        'STL': ('steals_per_game', 4.0),
        'BLK': ('blocks_per_game', 4.0),
        '3PM': ('three_pointers_made', 3.0),
        'TO': ('turnovers_per_game', -1.5),
        'FG_PCT': ('field_goal_percentage', 50.0),
        'FT_PCT': ('free_throw_percentage', 30.0)
    }
    
    if category in category_mapping:
        proj_key, weight = category_mapping[category]
        return player.get(proj_key, 0) * weight
    
    return 0.0


def analyze_category_impact(
    giving: List[Dict[str, Any]],
    receiving: List[Dict[str, Any]],
    current_roster: List[Dict[str, Any]],
    league_config: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Analyze how trade impacts each category
    
    Args:
        giving: Players being traded away
        receiving: Players being received
        current_roster: Current roster
        league_config: League configuration
        
    Returns:
        Category impact analysis
    """
    
    categories = league_config.get('categories', [])
    games_per_week = league_config.get('games_per_week', 3.33)
    
    category_impact = {}
    
    for cat in categories:
        # Calculate current category total
        current_total = sum(
            get_category_value(p, cat) * games_per_week 
            for p in current_roster
        )
        
        # Calculate what we're losing
        losing = sum(
            get_category_value(p, cat) * games_per_week 
            for p in giving
        )
        
        # Calculate what we're gaining
        gaining = sum(
            get_category_value(p, cat) * games_per_week 
            for p in receiving
        )
        
        # Post-trade total
        post_trade_total = current_total - losing + gaining
        
        difference = post_trade_total - current_total
        percent_change = (difference / current_total * 100) if current_total != 0 else 0
        
        # Determine status
        if abs(percent_change) < 3:
            status = 'neutral'
        elif difference > 0:
            status = 'improved'
        else:
            status = 'declined'
        
        category_impact[cat] = {
            'current': round(current_total, 2),
            'post_trade': round(post_trade_total, 2),
            'difference': round(difference, 2),
            'percent_change': round(percent_change, 1),
            'status': status
        }
    
    return category_impact


def analyze_positional_impact(
    giving: List[Dict[str, Any]],
    receiving: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Analyze positional depth changes
    
    Args:
        giving: Players being traded away
        receiving: Players being received
        
    Returns:
        Positional impact
    """
    
    positions = ['PG', 'SG', 'SF', 'PF', 'C']
    
    positional_impact = {}
    
    for pos in positions:
        giving_count = sum(
            1 for p in giving 
            if pos in p.get('player_position', '').split(',')
        )
        
        receiving_count = sum(
            1 for p in receiving 
            if pos in p.get('player_position', '').split(',')
        )
        
        net_change = receiving_count - giving_count
        
        if net_change > 0:
            status = 'gaining'
        elif net_change < 0:
            status = 'losing'
        else:
            status = 'neutral'
        
        positional_impact[pos] = {
            'giving': giving_count,
            'receiving': receiving_count,
            'net_change': net_change,
            'status': status
        }
    
    return positional_impact


def generate_trade_recommendation(
    value_change: float,
    category_impact: Dict[str, Any],
    positional_impact: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Generate trade recommendation
    
    Args:
        value_change: Overall value change
        category_impact: Category-by-category impact
        positional_impact: Positional changes
        
    Returns:
        Recommendation
    """
    
    # Count improved/declined categories
    improved = sum(1 for c in category_impact.values() if c['status'] == 'improved')
    declined = sum(1 for c in category_impact.values() if c['status'] == 'declined')
    
    # Determine verdict
    if value_change > 20:
        verdict = 'ACCEPT'
        confidence = 'Strong'
        reason = 'Excellent value gain'
    elif value_change > 10:
        verdict = 'ACCEPT'
        confidence = 'Moderate'
        reason = 'Good value gain'
    elif value_change > 0:
        verdict = 'CONSIDER'
        confidence = 'Low'
        reason = 'Slight value gain'
    elif value_change > -10:
        verdict = 'CONSIDER'
        confidence = 'Low'
        reason = 'Marginal value loss'
    elif value_change > -20:
        verdict = 'DECLINE'
        confidence = 'Moderate'
        reason = 'Notable value loss'
    else:
        verdict = 'DECLINE'
        confidence = 'Strong'
        reason = 'Significant value loss'
    
    # Generate notes
    notes = []
    
    if improved > declined:
        notes.append(f"Improves {improved} categories, declines {declined}")
    elif declined > improved:
        notes.append(f"Declines {declined} categories, improves {improved}")
    
    # Check for major improvements
    major_improvements = [
        cat for cat, impact in category_impact.items()
        if impact['percent_change'] > 15
    ]
    
    if major_improvements:
        notes.append(f"Opportunity: Major improvement in {', '.join(major_improvements)}")
    
    # Check for major declines
    major_declines = [
        cat for cat, impact in category_impact.items()
        if impact['percent_change'] < -15
    ]
    
    if major_declines:
        notes.append(f"Risk: Significant decline in {', '.join(major_declines)}")
    
    return {
        'verdict': verdict,
        'confidence': confidence,
        'reason': reason,
        'categories_improved': improved,
        'categories_declined': declined,
        'notes': notes
    }


def calculate_trade_rating(value_change: float, percent_change: float) -> str:
    """
    Calculate letter grade for trade
    
    Args:
        value_change: Absolute value change
        percent_change: Percentage value change
        
    Returns:
        Letter grade (A+ to F)
    """
    
    if percent_change >= 15:
        return 'A+'
    elif percent_change >= 10:
        return 'A'
    elif percent_change >= 7:
        return 'A-'
    elif percent_change >= 5:
        return 'B+'
    elif percent_change >= 3:
        return 'B'
    elif percent_change >= 1:
        return 'B-'
    elif percent_change >= -1:
        return 'C+'
    elif percent_change >= -3:
        return 'C'
    elif percent_change >= -5:
        return 'C-'
    elif percent_change >= -7:
        return 'D+'
    elif percent_change >= -10:
        return 'D'
    elif percent_change >= -15:
        return 'D-'
    else:
        return 'F'


def compare_trades(
    trade_offers: List[Dict[str, Any]],
    current_roster: List[Dict[str, Any]],
    league_config: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """
    Compare multiple trade offers
    
    Args:
        trade_offers: List of trade offers (each with giving/receiving)
        current_roster: Current roster
        league_config: League configuration
        
    Returns:
        Ranked trade comparisons
    """
    
    comparisons = []
    
    for offer in trade_offers:
        analysis = analyze_trade(
            offer['giving'],
            offer['receiving'],
            current_roster,
            league_config
        )
        
        comparisons.append({
            'offer_id': offer.get('offer_id', 'unknown'),
            'value_change': analysis['trade_analysis']['value_analysis']['value_change'],
            'rating': analysis['trade_analysis']['trade_rating'],
            'verdict': analysis['trade_analysis']['recommendation']['verdict'],
            'analysis': analysis['trade_analysis']
        })
    
    # Sort by value change (best first)
    comparisons.sort(key=lambda x: x['value_change'], reverse=True)
    
    return comparisons
