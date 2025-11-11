"""
NBA Fantasy Basketball Platform - League Database Operations
CRUD operations for leagues, rosters, and related data
"""

from typing import Dict, Any, List, Optional
import uuid
import logging
import dbb2_database as db

logger = logging.getLogger(__name__)


def create_league(
    customer_id: str,
    league_name: str,
    scoring_type: str,
    categories: List[str],
    **kwargs
) -> Dict[str, Any]:
    """
    Create a new fantasy league
    
    Args:
        customer_id: Customer ID
        league_name: Name of the league
        scoring_type: 'roto', 'h2h_categories', or 'h2h_points'
        categories: List of category names
        **kwargs: Additional league settings
        
    Returns:
        Created league details
    """
    
    league_id = str(uuid.uuid4())[:8]
    
    query = """
        INSERT INTO leagues (
            league_id, customer_id, league_name, platform, scoring_type,
            categories, category_display_names, weekly_targets, points_values,
            roster_size, games_per_week, position_requirements
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING *
    """
    
    import json
    
    params = (
        league_id,
        customer_id,
        league_name,
        kwargs.get('platform'),
        scoring_type,
        categories,
        json.dumps(kwargs.get('category_display_names', {})),
        json.dumps(kwargs.get('weekly_targets', {})),
        json.dumps(kwargs.get('points_values', {})),
        kwargs.get('roster_size', 13),
        kwargs.get('games_per_week', 3.33),
        json.dumps(kwargs.get('position_requirements', {
            'PG': 1, 'SG': 1, 'SF': 1, 'PF': 1, 'C': 1,
            'G': 1, 'F': 1, 'UTIL': 2, 'BE': 3
        }))
    )
    
    results = db.execute_query(query, params)
    
    if results and len(results) > 0:
        logger.info(f"✅ Created league {league_id} for customer {customer_id}")
        return results[0]
    
    return None


def get_customer_leagues(customer_id: str) -> List[Dict[str, Any]]:
    """
    Get all leagues for a customer
    
    Args:
        customer_id: Customer ID
        
    Returns:
        List of league dictionaries
    """
    
    query = """
        SELECT * FROM leagues
        WHERE customer_id = %s
        AND is_active = TRUE
        ORDER BY created_at DESC
    """
    
    results = db.execute_query(query, (customer_id,))
    return results if results else []


def get_league(league_id: str, customer_id: str) -> Optional[Dict[str, Any]]:
    """
    Get league details
    
    Args:
        league_id: League ID
        customer_id: Customer ID (for security)
        
    Returns:
        League dictionary or None
    """
    
    query = """
        SELECT * FROM leagues
        WHERE league_id = %s
        AND customer_id = %s
        AND is_active = TRUE
    """
    
    results = db.execute_query(query, (league_id, customer_id))
    
    if results and len(results) > 0:
        return results[0]
    
    return None


def update_league(
    league_id: str,
    customer_id: str,
    updates: Dict[str, Any]
) -> Optional[Dict[str, Any]]:
    """
    Update league settings
    
    Args:
        league_id: League ID
        customer_id: Customer ID (for security)
        updates: Dictionary of fields to update
        
    Returns:
        Updated league or None
    """
    
    import json
    
    # Build dynamic update query
    update_fields = []
    params = []
    
    allowed_fields = [
        'league_name', 'weekly_targets', 'points_values', 
        'roster_size', 'games_per_week', 'position_requirements'
    ]
    
    for field, value in updates.items():
        if field in allowed_fields:
            if field in ['weekly_targets', 'points_values', 'position_requirements']:
                update_fields.append(f"{field} = %s")
                params.append(json.dumps(value))
            else:
                update_fields.append(f"{field} = %s")
                params.append(value)
    
    if not update_fields:
        return None
    
    update_fields.append("updated_at = CURRENT_TIMESTAMP")
    
    query = f"""
        UPDATE leagues
        SET {', '.join(update_fields)}
        WHERE league_id = %s
        AND customer_id = %s
        RETURNING *
    """
    
    params.extend([league_id, customer_id])
    
    results = db.execute_query(query, tuple(params))
    
    if results and len(results) > 0:
        logger.info(f"✅ Updated league {league_id}")
        return results[0]
    
    return None


def delete_league(league_id: str, customer_id: str) -> bool:
    """
    Delete (deactivate) a league
    
    Args:
        league_id: League ID
        customer_id: Customer ID (for security)
        
    Returns:
        True if deleted successfully
    """
    
    query = """
        UPDATE leagues
        SET is_active = FALSE
        WHERE league_id = %s
        AND customer_id = %s
    """
    
    try:
        db.execute_query(query, (league_id, customer_id), fetch=False)
        logger.info(f"✅ Deleted league {league_id}")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to delete league: {e}")
        return False


def add_roster_player(
    league_id: str,
    customer_id: str,
    player_id: int,
    player_name: str,
    **kwargs
) -> Dict[str, Any]:
    """
    Add player to roster
    
    Args:
        league_id: League ID
        customer_id: Customer ID
        player_id: Player ID
        player_name: Player name
        **kwargs: Additional player details
        
    Returns:
        Roster entry
    """
    
    query = """
        INSERT INTO rosters (
            league_id, customer_id, player_id, player_name,
            player_team, player_position, roster_slot
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (league_id, player_id, is_active)
        DO UPDATE SET is_active = TRUE
        RETURNING *
    """
    
    params = (
        league_id,
        customer_id,
        player_id,
        player_name,
        kwargs.get('player_team'),
        kwargs.get('player_position'),
        kwargs.get('roster_slot')
    )
    
    results = db.execute_query(query, params)
    
    # Log transaction
    log_transaction(league_id, customer_id, 'add', player_id, player_name)
    
    if results and len(results) > 0:
        logger.info(f"✅ Added player {player_id} to roster")
        return results[0]
    
    return None


def get_roster(league_id: str, customer_id: str) -> List[Dict[str, Any]]:
    """
    Get league roster
    
    Args:
        league_id: League ID
        customer_id: Customer ID
        
    Returns:
        List of roster players
    """
    
    query = """
        SELECT * FROM rosters
        WHERE league_id = %s
        AND customer_id = %s
        AND is_active = TRUE
        ORDER BY roster_slot, added_at
    """
    
    results = db.execute_query(query, (league_id, customer_id))
    return results if results else []


def remove_roster_player(
    league_id: str,
    customer_id: str,
    player_id: int
) -> bool:
    """
    Remove player from roster
    
    Args:
        league_id: League ID
        customer_id: Customer ID
        player_id: Player ID
        
    Returns:
        True if removed successfully
    """
    
    # Get player name for transaction log
    query = "SELECT player_name FROM rosters WHERE league_id = %s AND player_id = %s AND is_active = TRUE"
    results = db.execute_query(query, (league_id, player_id))
    player_name = results[0]['player_name'] if results else 'Unknown'
    
    query = """
        UPDATE rosters
        SET is_active = FALSE
        WHERE league_id = %s
        AND customer_id = %s
        AND player_id = %s
    """
    
    try:
        db.execute_query(query, (league_id, customer_id, player_id), fetch=False)
        
        # Log transaction
        log_transaction(league_id, customer_id, 'drop', player_id, player_name)
        
        logger.info(f"✅ Removed player {player_id} from roster")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to remove player: {e}")
        return False


def log_transaction(
    league_id: str,
    customer_id: str,
    transaction_type: str,
    player_id: int,
    player_name: str,
    notes: str = None
) -> None:
    """
    Log player transaction
    
    Args:
        league_id: League ID
        customer_id: Customer ID
        transaction_type: 'add', 'drop', or 'trade'
        player_id: Player ID
        player_name: Player name
        notes: Optional notes
    """
    
    query = """
        INSERT INTO player_transactions (
            league_id, customer_id, transaction_type,
            player_id, player_name, notes
        )
        VALUES (%s, %s, %s, %s, %s, %s)
    """
    
    try:
        db.execute_query(
            query, 
            (league_id, customer_id, transaction_type, player_id, player_name, notes),
            fetch=False
        )
    except Exception as e:
        logger.warning(f"⚠️ Failed to log transaction: {e}")


def add_to_watchlist(
    league_id: str,
    customer_id: str,
    player_id: int,
    player_name: str,
    **kwargs
) -> Dict[str, Any]:
    """
    Add player to watchlist
    
    Args:
        league_id: League ID
        customer_id: Customer ID
        player_id: Player ID
        player_name: Player name
        **kwargs: Additional fields (notes, priority)
        
    Returns:
        Watchlist entry
    """
    
    query = """
        INSERT INTO watchlist (
            league_id, customer_id, player_id, player_name, notes, priority
        )
        VALUES (%s, %s, %s, %s, %s, %s)
        ON CONFLICT (league_id, player_id)
        DO UPDATE SET notes = EXCLUDED.notes, priority = EXCLUDED.priority
        RETURNING *
    """
    
    params = (
        league_id,
        customer_id,
        player_id,
        player_name,
        kwargs.get('notes'),
        kwargs.get('priority', 'medium')
    )
    
    results = db.execute_query(query, params)
    
    if results and len(results) > 0:
        return results[0]
    
    return None


def get_watchlist(league_id: str, customer_id: str) -> List[Dict[str, Any]]:
    """
    Get watchlist for league
    
    Args:
        league_id: League ID
        customer_id: Customer ID
        
    Returns:
        List of watched players
    """
    
    query = """
        SELECT * FROM watchlist
        WHERE league_id = %s
        AND customer_id = %s
        ORDER BY priority DESC, added_at DESC
    """
    
    results = db.execute_query(query, (league_id, customer_id))
    return results if results else []


def remove_from_watchlist(
    league_id: str,
    customer_id: str,
    player_id: int
) -> bool:
    """
    Remove player from watchlist
    
    Args:
        league_id: League ID
        customer_id: Customer ID
        player_id: Player ID
        
    Returns:
        True if removed successfully
    """
    
    query = """
        DELETE FROM watchlist
        WHERE league_id = %s
        AND customer_id = %s
        AND player_id = %s
    """
    
    try:
        db.execute_query(query, (league_id, customer_id, player_id), fetch=False)
        return True
    except Exception as e:
        logger.error(f"❌ Failed to remove from watchlist: {e}")
        return False


def get_category_presets() -> List[Dict[str, Any]]:
    """
    Get all category presets
    
    Returns:
        List of preset configurations
    """
    
    query = "SELECT * FROM category_presets ORDER BY is_default DESC, preset_name"
    
    results = db.execute_query(query)
    return results if results else []
