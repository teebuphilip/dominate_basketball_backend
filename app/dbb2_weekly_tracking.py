"""
NBA Fantasy Basketball Platform - Weekly Performance Tracking
Track historical performance and analyze trends
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import json
import logging
import dbb2_database as db

logger = logging.getLogger(__name__)


def save_week_performance(
    league_id: str,
    customer_id: str,
    week_number: int,
    category_totals: Dict[str, Any],
    roster_snapshot: List[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Save weekly performance snapshot
    
    Args:
        league_id: League ID
        customer_id: Customer ID
        week_number: Week number
        category_totals: Category totals for the week
        roster_snapshot: Roster at time of save
        
    Returns:
        Saved performance record
    """
    
    # Calculate week dates
    today = datetime.now().date()
    week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=6)
    
    query = """
        INSERT INTO weekly_performance (
            league_id, customer_id, week_number, week_start, week_end,
            season_year, category_totals, roster_snapshot, is_complete
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (league_id, season_year, week_number)
        DO UPDATE SET
            category_totals = EXCLUDED.category_totals,
            roster_snapshot = EXCLUDED.roster_snapshot,
            is_complete = EXCLUDED.is_complete,
            saved_at = CURRENT_TIMESTAMP
        RETURNING *
    """
    
    params = (
        league_id,
        customer_id,
        week_number,
        week_start,
        week_end,
        datetime.now().year,
        json.dumps(category_totals),
        json.dumps(roster_snapshot) if roster_snapshot else None,
        True
    )
    
    results = db.execute_query(query, params)
    
    if results and len(results) > 0:
        logger.info(f"✅ Saved week {week_number} performance for league {league_id}")
        return results[0]
    
    return None


def get_performance_history(
    league_id: str,
    customer_id: str,
    weeks: int = 10
) -> List[Dict[str, Any]]:
    """
    Get historical performance data
    
    Args:
        league_id: League ID
        customer_id: Customer ID
        weeks: Number of weeks to retrieve
        
    Returns:
        List of weekly performance records
    """
    
    query = """
        SELECT * FROM weekly_performance
        WHERE league_id = %s
        AND customer_id = %s
        ORDER BY season_year DESC, week_number DESC
        LIMIT %s
    """
    
    results = db.execute_query(query, (league_id, customer_id, weeks))
    
    if results:
        # Parse JSON fields
        for record in results:
            if record.get('category_totals'):
                record['category_totals'] = json.loads(record['category_totals']) \
                    if isinstance(record['category_totals'], str) else record['category_totals']
            if record.get('roster_snapshot'):
                record['roster_snapshot'] = json.loads(record['roster_snapshot']) \
                    if isinstance(record['roster_snapshot'], str) else record['roster_snapshot']
    
    return results if results else []


def get_category_trend(
    league_id: str,
    customer_id: str,
    category: str,
    weeks: int = 10
) -> Dict[str, Any]:
    """
    Analyze trend for a specific category
    
    Args:
        league_id: League ID
        customer_id: Customer ID
        category: Category name
        weeks: Number of weeks to analyze
        
    Returns:
        Trend analysis
    """
    
    history = get_performance_history(league_id, customer_id, weeks)
    
    if not history:
        return {
            'category': category,
            'weeks_tracked': 0,
            'trend': 'insufficient_data',
            'data': []
        }
    
    # Extract category values
    data_points = []
    
    for record in reversed(history):  # Chronological order
        category_totals = record.get('category_totals', {})
        
        if category in category_totals:
            value = category_totals[category].get('actual', 0)
            data_points.append({
                'week': record['week_number'],
                'value': value,
                'date': str(record['week_start'])
            })
    
    if len(data_points) < 2:
        return {
            'category': category,
            'weeks_tracked': len(data_points),
            'trend': 'insufficient_data',
            'data': data_points
        }
    
    # Calculate averages
    values = [d['value'] for d in data_points]
    overall_avg = sum(values) / len(values)
    
    # Recent average (last 3 weeks)
    recent_values = values[-3:] if len(values) >= 3 else values
    recent_avg = sum(recent_values) / len(recent_values)
    
    # Determine trend
    if recent_avg > overall_avg * 1.05:
        trend = 'improving'
    elif recent_avg < overall_avg * 0.95:
        trend = 'declining'
    else:
        trend = 'stable'
    
    return {
        'category': category,
        'weeks_tracked': len(data_points),
        'average': round(overall_avg, 2),
        'recent_average': round(recent_avg, 2),
        'trend': trend,
        'percent_change': round(((recent_avg - overall_avg) / overall_avg * 100), 1) if overall_avg > 0 else 0,
        'data': data_points
    }


def compare_weeks(
    league_id: str,
    customer_id: str,
    week1: int,
    week2: int
) -> Dict[str, Any]:
    """
    Compare performance between two weeks
    
    Args:
        league_id: League ID
        customer_id: Customer ID
        week1: First week number
        week2: Second week number
        
    Returns:
        Comparison analysis
    """
    
    query = """
        SELECT * FROM weekly_performance
        WHERE league_id = %s
        AND customer_id = %s
        AND week_number IN (%s, %s)
        ORDER BY week_number
    """
    
    results = db.execute_query(query, (league_id, customer_id, week1, week2))
    
    if not results or len(results) < 2:
        return {
            'error': 'Insufficient data for comparison',
            'weeks_found': len(results) if results else 0
        }
    
    week1_data = results[0] if results[0]['week_number'] == week1 else results[1]
    week2_data = results[1] if results[1]['week_number'] == week2 else results[0]
    
    # Parse JSON
    week1_totals = json.loads(week1_data['category_totals']) \
        if isinstance(week1_data['category_totals'], str) else week1_data['category_totals']
    week2_totals = json.loads(week2_data['category_totals']) \
        if isinstance(week2_data['category_totals'], str) else week2_data['category_totals']
    
    # Compare categories
    comparisons = []
    
    for category in week1_totals.keys():
        if category in week2_totals:
            week1_val = week1_totals[category].get('actual', 0)
            week2_val = week2_totals[category].get('actual', 0)
            diff = week2_val - week1_val
            
            comparisons.append({
                'category': category,
                'week1_value': round(week1_val, 2),
                'week2_value': round(week2_val, 2),
                'difference': round(diff, 2),
                'percent_change': round((diff / week1_val * 100), 1) if week1_val > 0 else 0,
                'trend': 'improved' if diff > 0 else 'declined' if diff < 0 else 'stable'
            })
    
    return {
        'league_id': league_id,
        'week1': week1,
        'week2': week2,
        'comparisons': comparisons,
        'improved_categories': [c['category'] for c in comparisons if c['trend'] == 'improved'],
        'declined_categories': [c['category'] for c in comparisons if c['trend'] == 'declined']
    }


def get_performance_summary(
    league_id: str,
    customer_id: str
) -> Dict[str, Any]:
    """
    Get overall performance summary
    
    Args:
        league_id: League ID
        customer_id: Customer ID
        
    Returns:
        Performance summary
    """
    
    query = """
        SELECT 
            COUNT(*) as weeks_tracked,
            MAX(week_number) as latest_week,
            MIN(week_start) as first_week_start,
            MAX(week_end) as latest_week_end
        FROM weekly_performance
        WHERE league_id = %s
        AND customer_id = %s
        AND is_complete = TRUE
    """
    
    results = db.execute_query(query, (league_id, customer_id))
    
    if results and len(results) > 0:
        return results[0]
    
    return {
        'weeks_tracked': 0,
        'latest_week': None,
        'first_week_start': None,
        'latest_week_end': None
    }
