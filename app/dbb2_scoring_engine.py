"""
NBA Fantasy Basketball Platform - Scoring Engine
Calculate scores for Roto, H2H Categories, and H2H Points leagues
"""

from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)


def calculate_roto_score(
    roster_projections: List[Dict[str, Any]],
    categories: List[str],
    weekly_targets: Dict[str, float],
    games_per_week: float = 3.33
) -> Dict[str, Any]:
    """
    Calculate Rotisserie scoring with gap analysis
    
    Args:
        roster_projections: List of player projections
        categories: List of category names
        weekly_targets: Target values per category per week
        games_per_week: Average games per week per player
        
    Returns:
        Scoring results with gaps
    """
    
    # Calculate totals
    category_totals = {}
    
    for cat in categories:
        total = 0.0
        
        if cat.endswith('_PCT'):
            # Handle percentages specially (weighted average)
            makes_cat = cat.replace('_PCT', 'M')
            attempts_cat = cat.replace('_PCT', 'A')
            
            total_makes = 0.0
            total_attempts = 0.0
            
            # Map category to projection keys
            key_mapping = {
                'FG_PCT': ('field_goals_made', 'field_goals_attempted'),
                'FT_PCT': ('free_throws_made', 'free_throws_attempted'),
                'THREE_PCT': ('three_pointers_made', 'three_pointers_attempted'),
                '3P_PCT': ('three_pointers_made', 'three_pointers_attempted')
            }
            
            if cat in key_mapping:
                makes_key, attempts_key = key_mapping[cat]
                
                for proj in roster_projections:
                    makes = proj.get(makes_key, 0) * games_per_week
                    attempts = proj.get(attempts_key, 0) * games_per_week
                    total_makes += makes
                    total_attempts += attempts
                
                if total_attempts > 0:
                    total = total_makes / total_attempts
                else:
                    total = 0.0
                
                category_totals[cat] = {
                    'actual': total,
                    'makes': total_makes,
                    'attempts': total_attempts
                }
            else:
                category_totals[cat] = {'actual': 0.0}
        
        else:
            # Regular counting stats
            key_mapping = {
                'PTS': 'points_per_game',
                'REB': 'rebounds_per_game',
                'AST': 'assists_per_game',
                'STL': 'steals_per_game',
                'BLK': 'blocks_per_game',
                'TO': 'turnovers_per_game',
                '3PM': 'three_pointers_made',
                'FGM': 'field_goals_made',
                'FTM': 'free_throws_made',
                'OREB': 'offensive_rebounds',
                'DREB': 'defensive_rebounds'
            }
            
            proj_key = key_mapping.get(cat, cat.lower())
            
            for proj in roster_projections:
                value = proj.get(proj_key, 0)
                total += value * games_per_week
            
            category_totals[cat] = {'actual': total}
    
    # Calculate gaps vs targets
    category_results = {}
    
    for cat in categories:
        target = weekly_targets.get(cat, 0)
        actual = category_totals[cat]['actual']
        gap = target - actual
        
        result = {
            'target': target,
            'actual': round(actual, 2),
            'gap': round(gap, 2),
            'percentage_complete': round((actual / target * 100) if target > 0 else 0, 1)
        }
        
        # Add makes/attempts for percentages
        if cat.endswith('_PCT'):
            result['makes'] = round(category_totals[cat].get('makes', 0), 1)
            result['attempts'] = round(category_totals[cat].get('attempts', 0), 1)
        
        # Determine status
        if cat == 'TO':  # Turnovers: lower is better
            if actual <= target:
                result['status'] = 'ahead'
            elif gap < 5:
                result['status'] = 'on_track'
            else:
                result['status'] = 'behind'
        else:
            if actual >= target:
                result['status'] = 'ahead'
            elif gap <= target * 0.1:  # Within 10%
                result['status'] = 'on_track'
            else:
                result['status'] = 'behind'
        
        category_results[cat] = result
    
    # Overall status summary
    status_counts = {
        'ahead': sum(1 for r in category_results.values() if r['status'] == 'ahead'),
        'behind': sum(1 for r in category_results.values() if r['status'] == 'behind'),
        'on_track': sum(1 for r in category_results.values() if r['status'] == 'on_track')
    }
    
    return {
        'category_results': category_results,
        'overall_status': status_counts,
        'games_counted': games_per_week * len(roster_projections)
    }


def calculate_h2h_categories(
    my_projections: List[Dict[str, Any]],
    opponent_projections: List[Dict[str, Any]],
    categories: List[str],
    games_per_week: float = 3.33
) -> Dict[str, Any]:
    """
    Calculate Head-to-Head Categories matchup
    
    Args:
        my_projections: My roster projections
        opponent_projections: Opponent roster projections
        categories: List of categories
        games_per_week: Average games per week
        
    Returns:
        Matchup analysis with wins/losses
    """
    
    # Calculate totals for both teams
    my_totals = {}
    opp_totals = {}
    
    for cat in categories:
        my_total = calculate_category_total(my_projections, cat, games_per_week)
        opp_total = calculate_category_total(opponent_projections, cat, games_per_week)
        
        my_totals[cat] = my_total
        opp_totals[cat] = opp_total
    
    # Determine winners
    category_breakdown = []
    wins = 0
    losses = 0
    ties = 0
    
    for cat in categories:
        my_val = my_totals[cat]
        opp_val = opp_totals[cat]
        diff = my_val - opp_val
        
        # For turnovers, lower is better
        if cat == 'TO':
            if my_val < opp_val:
                status = 'win'
                wins += 1
            elif my_val > opp_val:
                status = 'loss'
                losses += 1
            else:
                status = 'tie'
                ties += 1
        else:
            if my_val > opp_val:
                status = 'win'
                wins += 1
            elif my_val < opp_val:
                status = 'loss'
                losses += 1
            else:
                status = 'tie'
                ties += 1
        
        category_breakdown.append({
            'category': cat,
            'my_total': round(my_val, 2),
            'opponent_total': round(opp_val, 2),
            'difference': round(diff, 2),
            'percent_difference': round((diff / opp_val * 100) if opp_val > 0 else 0, 1),
            'status': status
        })
    
    # Determine matchup result
    if wins > losses:
        matchup_result = 'win'
    elif losses > wins:
        matchup_result = 'loss'
    else:
        matchup_result = 'tie'
    
    # Find close categories (within 10%)
    close_categories = [
        c for c in category_breakdown 
        if abs(c['percent_difference']) <= 10 and c['status'] != 'tie'
    ]
    
    # Find blowout categories (>30% difference)
    blowout_categories = [
        c for c in category_breakdown 
        if abs(c['percent_difference']) > 30
    ]
    
    return {
        'matchup_result': matchup_result,
        'wins': wins,
        'losses': losses,
        'ties': ties,
        'categories_won': [c['category'] for c in category_breakdown if c['status'] == 'win'],
        'categories_lost': [c['category'] for c in category_breakdown if c['status'] == 'loss'],
        'category_breakdown': category_breakdown,
        'close_categories': close_categories,
        'blowout_categories': blowout_categories,
        'winning_probability': round((wins / len(categories) * 100), 1)
    }


def calculate_h2h_points(
    roster_projections: List[Dict[str, Any]],
    points_values: Dict[str, float],
    games_per_week: float = 3.33
) -> Dict[str, Any]:
    """
    Calculate Head-to-Head Points scoring
    
    Args:
        roster_projections: List of player projections
        points_values: Point values for each stat
        games_per_week: Average games per week
        
    Returns:
        Total fantasy points
    """
    
    total_points = 0.0
    player_breakdown = []
    
    for proj in roster_projections:
        player_points = 0.0
        
        # Map stats to projection keys
        stat_mapping = {
            'PTS': 'points_per_game',
            'REB': 'rebounds_per_game',
            'AST': 'assists_per_game',
            'STL': 'steals_per_game',
            'BLK': 'blocks_per_game',
            'TO': 'turnovers_per_game',
            '3PM': 'three_pointers_made',
            'FGM': 'field_goals_made',
            'FGA': 'field_goals_attempted',
            'FTM': 'free_throws_made',
            'FTA': 'free_throws_attempted'
        }
        
        for stat, point_value in points_values.items():
            proj_key = stat_mapping.get(stat, stat.lower())
            stat_value = proj.get(proj_key, 0)
            player_points += stat_value * point_value * games_per_week
        
        total_points += player_points
        
        player_breakdown.append({
            'player_name': proj.get('player_name', 'Unknown'),
            'fantasy_points': round(player_points, 1)
        })
    
    # Sort by points
    player_breakdown.sort(key=lambda x: x['fantasy_points'], reverse=True)
    
    return {
        'total_fantasy_points': round(total_points, 1),
        'player_breakdown': player_breakdown,
        'average_per_player': round(total_points / len(roster_projections), 1) if roster_projections else 0
    }


def calculate_category_total(
    projections: List[Dict[str, Any]], 
    category: str, 
    games_per_week: float
) -> float:
    """
    Helper function to calculate total for a category
    
    Args:
        projections: List of player projections
        category: Category name
        games_per_week: Average games per week
        
    Returns:
        Total value for category
    """
    
    if category.endswith('_PCT'):
        # Handle percentages
        key_mapping = {
            'FG_PCT': ('field_goals_made', 'field_goals_attempted'),
            'FT_PCT': ('free_throws_made', 'free_throws_attempted'),
            'THREE_PCT': ('three_pointers_made', 'three_pointers_attempted'),
            '3P_PCT': ('three_pointers_made', 'three_pointers_attempted')
        }
        
        if category in key_mapping:
            makes_key, attempts_key = key_mapping[category]
            
            total_makes = sum(p.get(makes_key, 0) * games_per_week for p in projections)
            total_attempts = sum(p.get(attempts_key, 0) * games_per_week for p in projections)
            
            return (total_makes / total_attempts) if total_attempts > 0 else 0.0
    
    else:
        # Regular stats
        key_mapping = {
            'PTS': 'points_per_game',
            'REB': 'rebounds_per_game',
            'AST': 'assists_per_game',
            'STL': 'steals_per_game',
            'BLK': 'blocks_per_game',
            'TO': 'turnovers_per_game',
            '3PM': 'three_pointers_made',
            'FGM': 'field_goals_made',
            'FTM': 'free_throws_made'
        }
        
        proj_key = key_mapping.get(category, category.lower())
        return sum(p.get(proj_key, 0) * games_per_week for p in projections)
    
    return 0.0


def get_gap_analysis(
    category_results: Dict[str, Any],
    roster_size: int
) -> Dict[str, Any]:
    """
    Analyze gaps and provide recommendations
    
    Args:
        category_results: Results from calculate_roto_score
        roster_size: Number of players on roster
        
    Returns:
        Gap analysis with recommendations
    """
    
    needs_help = []
    doing_well = []
    
    for cat, result in category_results.items():
        if result['status'] == 'behind':
            per_player_needed = result['gap'] / roster_size if roster_size > 0 else 0
            needs_help.append({
                'category': cat,
                'gap': result['gap'],
                'target': result['target'],
                'actual': result['actual'],
                'per_player_needed': round(per_player_needed, 2)
            })
        elif result['status'] == 'ahead':
            surplus = abs(result['gap'])
            doing_well.append({
                'category': cat,
                'surplus': surplus,
                'target': result['target'],
                'actual': result['actual']
            })
    
    # Sort by gap size
    needs_help.sort(key=lambda x: abs(x['gap']), reverse=True)
    doing_well.sort(key=lambda x: x['surplus'], reverse=True)
    
    # Generate recommendations
    recommendations = []
    
    if needs_help:
        top_needs = [n['category'] for n in needs_help[:3]]
        recommendations.append(f"Priority categories: {', '.join(top_needs)}")
    
    if doing_well:
        top_strengths = [d['category'] for d in doing_well[:2]]
        recommendations.append(f"Strong in: {', '.join(top_strengths)}")
    
    return {
        'needs_help': needs_help,
        'doing_well': doing_well,
        'recommendations': recommendations
    }
