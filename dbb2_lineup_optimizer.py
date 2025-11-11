"""
NBA Fantasy Basketball Platform - Lineup Optimizer
Optimize starting lineup based on position requirements
"""

from typing import Dict, Any, List
import logging

logger = logging.getLogger(__name__)


def optimize_lineup(
    roster_with_projections: List[Dict[str, Any]],
    position_requirements: Dict[str, int],
    scoring_type: str = 'roto'
) -> Dict[str, Any]:
    """
    Optimize lineup to maximize value
    
    Args:
        roster_with_projections: Roster players with projections
        position_requirements: Position slots (PG, SG, SF, PF, C, G, F, UTIL, BE)
        scoring_type: League scoring type
        
    Returns:
        Optimized lineup with suggestions
    """
    
    # Calculate value for each player
    for player in roster_with_projections:
        player['value'] = calculate_player_value(player, scoring_type)
    
    # Sort by value (highest first)
    roster_with_projections.sort(key=lambda x: x['value'], reverse=True)
    
    # Initialize lineup structure
    lineup = {pos: [] for pos in position_requirements.keys()}
    assigned_players = set()
    
    # Fill specific positions first (PG, SG, SF, PF, C)
    specific_positions = ['PG', 'SG', 'SF', 'PF', 'C']
    
    for pos in specific_positions:
        if pos not in position_requirements or position_requirements[pos] == 0:
            continue
        
        slots_needed = position_requirements[pos]
        
        # Find eligible players
        for player in roster_with_projections:
            if player['player_id'] in assigned_players:
                continue
            
            positions = player.get('player_position', '').split(',')
            positions = [p.strip() for p in positions]
            
            if pos in positions:
                lineup[pos].append(player)
                assigned_players.add(player['player_id'])
                
                if len(lineup[pos]) >= slots_needed:
                    break
    
    # Fill flex positions (G, F)
    if 'G' in position_requirements:
        for _ in range(position_requirements['G']):
            for player in roster_with_projections:
                if player['player_id'] in assigned_players:
                    continue
                
                positions = player.get('player_position', '').split(',')
                positions = [p.strip() for p in positions]
                
                if any(p in ['PG', 'SG'] for p in positions):
                    lineup['G'].append(player)
                    assigned_players.add(player['player_id'])
                    break
    
    if 'F' in position_requirements:
        for _ in range(position_requirements['F']):
            for player in roster_with_projections:
                if player['player_id'] in assigned_players:
                    continue
                
                positions = player.get('player_position', '').split(',')
                positions = [p.strip() for p in positions]
                
                if any(p in ['SF', 'PF'] for p in positions):
                    lineup['F'].append(player)
                    assigned_players.add(player['player_id'])
                    break
    
    # Fill UTIL spots (any position)
    if 'UTIL' in position_requirements:
        for _ in range(position_requirements['UTIL']):
            for player in roster_with_projections:
                if player['player_id'] in assigned_players:
                    continue
                
                lineup['UTIL'].append(player)
                assigned_players.add(player['player_id'])
                break
    
    # Remaining players go to bench
    bench = []
    for player in roster_with_projections:
        if player['player_id'] not in assigned_players:
            bench.append(player)
    
    lineup['BE'] = bench
    
    # Generate suggestions
    suggestions = generate_lineup_suggestions(lineup, bench, position_requirements)
    
    # Calculate totals
    starting_count = sum(len(players) for pos, players in lineup.items() if pos != 'BE')
    total_value = sum(p['value'] for p in roster_with_projections if p['player_id'] in assigned_players)
    
    return {
        'lineup': lineup,
        'bench': bench,
        'total_value': round(total_value, 1),
        'starting_count': starting_count,
        'bench_count': len(bench),
        'lineup_suggestions': suggestions
    }


def calculate_player_value(player: Dict[str, Any], scoring_type: str) -> float:
    """
    Calculate player's fantasy value
    
    Args:
        player: Player with projections
        scoring_type: League scoring type
        
    Returns:
        Value score
    """
    
    proj = player
    
    if scoring_type == 'h2h_points':
        # Simple point values for demo
        value = (
            proj.get('points_per_game', 0) * 1.0 +
            proj.get('rebounds_per_game', 0) * 1.2 +
            proj.get('assists_per_game', 0) * 1.5 +
            proj.get('steals_per_game', 0) * 3.0 +
            proj.get('blocks_per_game', 0) * 3.0 +
            proj.get('three_pointers_made', 0) * 3.0 -
            proj.get('turnovers_per_game', 0) * 1.0
        )
    else:
        # Roto/H2H Categories: sum of per-game stats
        value = (
            proj.get('points_per_game', 0) * 0.5 +
            proj.get('rebounds_per_game', 0) * 1.5 +
            proj.get('assists_per_game', 0) * 1.5 +
            proj.get('steals_per_game', 0) * 4.0 +
            proj.get('blocks_per_game', 0) * 4.0 +
            proj.get('three_pointers_made', 0) * 3.0 +
            proj.get('field_goal_percentage', 0) * 50 +
            proj.get('free_throw_percentage', 0) * 30
        )
    
    return value


def generate_lineup_suggestions(
    lineup: Dict[str, List[Dict[str, Any]]],
    bench: List[Dict[str, Any]],
    position_requirements: Dict[str, int]
) -> List[Dict[str, Any]]:
    """
    Generate suggestions for lineup improvements
    
    Args:
        lineup: Current lineup
        bench: Bench players
        position_requirements: Position requirements
        
    Returns:
        List of suggestions
    """
    
    suggestions = []
    
    # Check if any bench player has higher value than starters
    for bench_player in bench:
        bench_positions = bench_player.get('player_position', '').split(',')
        bench_positions = [p.strip() for p in bench_positions]
        bench_value = bench_player['value']
        
        # Check each position the bench player is eligible for
        for pos in bench_positions:
            if pos not in lineup or len(lineup[pos]) == 0:
                continue
            
            # Find lowest value starter at this position
            for starter in lineup[pos]:
                starter_value = starter['value']
                
                if bench_value > starter_value * 1.1:  # 10% better
                    suggestions.append({
                        'type': 'swap',
                        'bench_out': starter['player_name'],
                        'bench_in': bench_player['player_name'],
                        'slot': pos,
                        'value_improvement': round(bench_value - starter_value, 1),
                        'reason': f"Bench player has higher value ({bench_value:.1f} vs {starter_value:.1f})"
                    })
    
    # Check for unfilled slots
    for pos, required in position_requirements.items():
        if pos == 'BE':
            continue
        
        filled = len(lineup.get(pos, []))
        
        if filled < required:
            suggestions.append({
                'type': 'fill_slot',
                'slot': pos,
                'slots_empty': required - filled,
                'reason': f"Position {pos} has {required - filled} empty slot(s)"
            })
    
    return suggestions
