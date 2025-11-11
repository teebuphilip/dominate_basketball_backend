"""
NBA Fantasy Basketball Platform - Database Module
Multi-tenant database connections with connection pooling
"""

import os
import psycopg2
from psycopg2.extras import RealDictCursor
from psycopg2 import pool
from typing import Optional, Dict, Any
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database connection pool
connection_pool: Optional[pool.SimpleConnectionPool] = None


def init_connection_pool(minconn: int = 1, maxconn: int = 20) -> None:
    """
    Initialize the database connection pool
    
    Args:
        minconn: Minimum number of connections
        maxconn: Maximum number of connections
    """
    global connection_pool
    
    database_url = os.getenv('DATABASE_URL', 'postgresql://localhost/nba_projections')
    
    try:
        connection_pool = psycopg2.pool.SimpleConnectionPool(
            minconn,
            maxconn,
            database_url
        )
        logger.info(f"✅ Database connection pool initialized (min={minconn}, max={maxconn})")
    except Exception as e:
        logger.error(f"❌ Failed to initialize connection pool: {e}")
        raise


def get_connection():
    """
    Get a connection from the pool
    
    Returns:
        Database connection
    """
    global connection_pool
    
    if connection_pool is None:
        init_connection_pool()
    
    try:
        conn = connection_pool.getconn()
        return conn
    except Exception as e:
        logger.error(f"❌ Failed to get connection from pool: {e}")
        raise


def return_connection(conn) -> None:
    """
    Return a connection to the pool
    
    Args:
        conn: Database connection to return
    """
    global connection_pool
    
    if connection_pool is not None and conn is not None:
        connection_pool.putconn(conn)


def close_all_connections() -> None:
    """Close all connections in the pool"""
    global connection_pool
    
    if connection_pool is not None:
        connection_pool.closeall()
        logger.info("✅ All database connections closed")


def execute_query(query: str, params: tuple = None, fetch: bool = True) -> Optional[list]:
    """
    Execute a database query
    
    Args:
        query: SQL query string
        params: Query parameters
        fetch: Whether to fetch results
        
    Returns:
        Query results (if fetch=True) or None
    """
    conn = None
    cursor = None
    
    try:
        conn = get_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        cursor.execute(query, params)
        
        if fetch:
            results = cursor.fetchall()
            return [dict(row) for row in results]
        else:
            conn.commit()
            return None
            
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"❌ Database query error: {e}")
        logger.error(f"Query: {query}")
        logger.error(f"Params: {params}")
        raise
        
    finally:
        if cursor:
            cursor.close()
        if conn:
            return_connection(conn)


def execute_many(query: str, data: list) -> None:
    """
    Execute a query with multiple parameter sets
    
    Args:
        query: SQL query string
        data: List of parameter tuples
    """
    conn = None
    cursor = None
    
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.executemany(query, data)
        conn.commit()
        
        logger.info(f"✅ Batch insert completed: {len(data)} rows")
        
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"❌ Batch insert error: {e}")
        raise
        
    finally:
        if cursor:
            cursor.close()
        if conn:
            return_connection(conn)


def get_customer_by_api_key(api_key: str) -> Optional[Dict[str, Any]]:
    """
    Get customer details by API key
    
    Args:
        api_key: API key string
        
    Returns:
        Customer details dictionary or None
    """
    query = """
        SELECT 
            c.customer_id,
            c.email,
            c.company_name,
            c.tier,
            c.is_active,
            c.custom_override_limit,
            c.can_access_current_season,
            c.can_train_models,
            ak.rate_limit_per_hour,
            ak.requests_used_this_hour,
            ak.rate_limit_reset_at
        FROM api_keys ak
        JOIN customers c ON ak.customer_id = c.customer_id
        WHERE ak.api_key = %s
        AND ak.is_active = TRUE
        AND c.is_active = TRUE
    """
    
    results = execute_query(query, (api_key,))
    
    if results and len(results) > 0:
        return results[0]
    return None


def update_rate_limit(api_key: str) -> None:
    """
    Increment request counter for rate limiting
    
    Args:
        api_key: API key string
    """
    from datetime import datetime, timedelta
    
    # Check if rate limit needs reset
    reset_query = """
        UPDATE api_keys
        SET requests_used_this_hour = 0,
            rate_limit_reset_at = NOW()
        WHERE api_key = %s
        AND rate_limit_reset_at < NOW() - INTERVAL '1 hour'
    """
    execute_query(reset_query, (api_key,), fetch=False)
    
    # Increment counter
    increment_query = """
        UPDATE api_keys
        SET requests_used_this_hour = requests_used_this_hour + 1,
            last_used_at = NOW()
        WHERE api_key = %s
    """
    execute_query(increment_query, (api_key,), fetch=False)


def check_rate_limit(api_key: str) -> tuple[bool, int, int]:
    """
    Check if API key has exceeded rate limit
    
    Args:
        api_key: API key string
        
    Returns:
        Tuple of (is_within_limit, requests_used, rate_limit)
    """
    query = """
        SELECT 
            requests_used_this_hour,
            rate_limit_per_hour,
            rate_limit_reset_at
        FROM api_keys
        WHERE api_key = %s
    """
    
    results = execute_query(query, (api_key,))
    
    if results and len(results) > 0:
        row = results[0]
        requests_used = row['requests_used_this_hour']
        rate_limit = row['rate_limit_per_hour']
        
        is_within_limit = requests_used < rate_limit
        return is_within_limit, requests_used, rate_limit
    
    return False, 0, 0


def log_usage(customer_id: str, endpoint: str) -> None:
    """
    Log API usage for billing/analytics
    
    Args:
        customer_id: Customer ID
        endpoint: API endpoint called
    """
    from datetime import datetime
    
    query = """
        INSERT INTO usage_tracking (
            customer_id, 
            date, 
            hour, 
            total_requests,
            projection_requests,
            league_requests
        )
        VALUES (%s, CURRENT_DATE, EXTRACT(HOUR FROM NOW()), 1, 
                CASE WHEN %s LIKE '%%projection%%' THEN 1 ELSE 0 END,
                CASE WHEN %s LIKE '%%league%%' THEN 1 ELSE 0 END)
        ON CONFLICT (customer_id, date, hour)
        DO UPDATE SET
            total_requests = usage_tracking.total_requests + 1,
            projection_requests = usage_tracking.projection_requests + 
                CASE WHEN %s LIKE '%%projection%%' THEN 1 ELSE 0 END,
            league_requests = usage_tracking.league_requests + 
                CASE WHEN %s LIKE '%%league%%' THEN 1 ELSE 0 END
    """
    
    try:
        execute_query(query, (customer_id, endpoint, endpoint, endpoint, endpoint), fetch=False)
    except Exception as e:
        # Don't fail the request if usage logging fails
        logger.warning(f"⚠️ Failed to log usage: {e}")


def get_customer_usage(customer_id: str, days: int = 30) -> Dict[str, Any]:
    """
    Get customer usage statistics
    
    Args:
        customer_id: Customer ID
        days: Number of days to look back
        
    Returns:
        Usage statistics dictionary
    """
    query = """
        SELECT 
            SUM(total_requests) as total_requests,
            SUM(projection_requests) as projection_requests,
            SUM(league_requests) as league_requests,
            MAX(date) as last_usage_date
        FROM usage_tracking
        WHERE customer_id = %s
        AND date >= CURRENT_DATE - INTERVAL '%s days'
    """
    
    results = execute_query(query, (customer_id, days))
    
    if results and len(results) > 0:
        return results[0]
    
    return {
        'total_requests': 0,
        'projection_requests': 0,
        'league_requests': 0,
        'last_usage_date': None
    }


def health_check() -> bool:
    """
    Check database connection health
    
    Returns:
        True if database is accessible
    """
    try:
        results = execute_query("SELECT 1 as health")
        return results is not None and len(results) > 0
    except Exception as e:
        logger.error(f"❌ Database health check failed: {e}")
        return False


# Initialize connection pool on module import
try:
    init_connection_pool()
except Exception as e:
    logger.error(f"❌ Failed to initialize database module: {e}")
