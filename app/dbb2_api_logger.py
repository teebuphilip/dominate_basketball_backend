"""
NBA Fantasy Basketball Platform - API Logger
Comprehensive request/response logging for debugging
"""

from typing import Dict, Any, Optional, List
import json
import logging
from datetime import datetime
import dbb2_database as db

logger = logging.getLogger(__name__)


def sanitize_sensitive_data(data: Any) -> Any:
    """
    Remove sensitive data from logs
    
    Args:
        data: Data to sanitize
        
    Returns:
        Sanitized data
    """
    
    if isinstance(data, dict):
        sanitized = {}
        sensitive_keys = ['password', 'api_key', 'secret', 'token', 'credit_card', 'ssn']
        
        for key, value in data.items():
            if any(sensitive in key.lower() for sensitive in sensitive_keys):
                sanitized[key] = '***REDACTED***'
            else:
                sanitized[key] = sanitize_sensitive_data(value)
        
        return sanitized
    
    elif isinstance(data, list):
        return [sanitize_sensitive_data(item) for item in data]
    
    else:
        return data


def sanitize_headers(headers: Dict[str, str]) -> Dict[str, str]:
    """
    Sanitize request headers
    
    Args:
        headers: Request headers
        
    Returns:
        Sanitized headers
    """
    
    sanitized = {}
    sensitive_headers = ['authorization', 'cookie', 'x-api-key']
    
    for key, value in headers.items():
        if key.lower() in sensitive_headers:
            # Keep first 10 chars for debugging
            sanitized[key] = value[:10] + '***' if len(value) > 10 else '***'
        else:
            sanitized[key] = value
    
    return sanitized


def log_api_request(
    customer_id: Optional[str],
    customer_email: Optional[str],
    customer_tier: Optional[str],
    endpoint: str,
    http_method: str,
    full_url: str,
    query_params: Optional[Dict[str, Any]],
    request_body: Optional[Dict[str, Any]],
    request_headers: Optional[Dict[str, str]],
    response_status_code: int,
    response_body: Optional[Any],
    response_time_ms: int,
    error_message: Optional[str] = None,
    error_stack_trace: Optional[str] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    league_id: Optional[str] = None,
    player_ids: Optional[List[int]] = None
) -> None:
    """
    Log complete API request/response
    
    Args:
        customer_id: Customer ID
        customer_email: Customer email
        customer_tier: Customer tier
        endpoint: API endpoint
        http_method: HTTP method
        full_url: Full URL with query params
        query_params: Query parameters
        request_body: Request body
        request_headers: Request headers
        response_status_code: Response status code
        response_body: Response body (for errors)
        response_time_ms: Response time in milliseconds
        error_message: Error message if any
        error_stack_trace: Stack trace if any
        ip_address: Client IP
        user_agent: User agent
        league_id: League ID if applicable
        player_ids: Player IDs if applicable
    """
    
    try:
        # Sanitize sensitive data
        sanitized_body = sanitize_sensitive_data(request_body) if request_body else None
        sanitized_headers = sanitize_headers(request_headers) if request_headers else None
        sanitized_response = sanitize_sensitive_data(response_body) if response_body and response_status_code >= 400 else None
        
        query = """
            INSERT INTO api_debug_log (
                customer_id, customer_email, customer_tier,
                endpoint, http_method, full_url, query_params,
                request_body, request_headers,
                response_status_code, response_body, response_time_ms,
                error_message, error_stack_trace,
                ip_address, user_agent, league_id, player_ids
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        params = (
            customer_id,
            customer_email,
            customer_tier,
            endpoint,
            http_method,
            full_url,
            json.dumps(query_params) if query_params else None,
            json.dumps(sanitized_body) if sanitized_body else None,
            json.dumps(sanitized_headers) if sanitized_headers else None,
            response_status_code,
            json.dumps(sanitized_response) if sanitized_response else None,
            response_time_ms,
            error_message,
            error_stack_trace,
            ip_address,
            user_agent,
            league_id,
            player_ids
        )
        
        db.execute_query(query, params, fetch=False)
        
        # If error, update error aggregation
        if response_status_code >= 400 and error_message:
            aggregate_error(endpoint, error_message, customer_id)
        
    except Exception as e:
        logger.error(f"❌ Failed to log API request: {e}")


def aggregate_error(endpoint: str, error_message: str, customer_id: Optional[str]) -> None:
    """
    Aggregate recurring errors
    
    Args:
        endpoint: API endpoint
        error_message: Error message
        customer_id: Customer ID
    """
    
    try:
        # Check if error exists
        query = """
            SELECT error_id, occurrence_count, affected_customers
            FROM api_errors
            WHERE endpoint = %s
            AND error_message = %s
            AND status = 'active'
        """
        
        results = db.execute_query(query, (endpoint, error_message))
        
        if results and len(results) > 0:
            # Update existing error
            error = results[0]
            affected_customers = error.get('affected_customers', [])
            
            if customer_id and customer_id not in affected_customers:
                affected_customers.append(customer_id)
            
            update_query = """
                UPDATE api_errors
                SET occurrence_count = occurrence_count + 1,
                    last_occurrence = CURRENT_TIMESTAMP,
                    customer_count = %s,
                    affected_customers = %s
                WHERE error_id = %s
            """
            
            db.execute_query(
                update_query,
                (len(affected_customers), affected_customers, error['error_id']),
                fetch=False
            )
        
        else:
            # Create new error entry
            insert_query = """
                INSERT INTO api_errors (
                    endpoint, error_message, affected_customers, customer_count
                )
                VALUES (%s, %s, %s, %s)
            """
            
            affected = [customer_id] if customer_id else []
            
            db.execute_query(
                insert_query,
                (endpoint, error_message, affected, len(affected)),
                fetch=False
            )
    
    except Exception as e:
        logger.warning(f"⚠️ Failed to aggregate error: {e}")


def get_customer_logs(
    customer_id: str,
    hours: int = 24,
    limit: int = 100
) -> List[Dict[str, Any]]:
    """
    Get API logs for a customer
    
    Args:
        customer_id: Customer ID
        hours: Number of hours to look back
        limit: Maximum number of logs
        
    Returns:
        List of log entries
    """
    
    query = """
        SELECT 
            log_id, request_timestamp, endpoint, http_method,
            query_params, request_body, response_status_code,
            response_time_ms, error_message, league_id, player_ids
        FROM api_debug_log
        WHERE customer_id = %s
        AND request_timestamp > NOW() - INTERVAL '%s hours'
        ORDER BY request_timestamp DESC
        LIMIT %s
    """
    
    results = db.execute_query(query, (customer_id, hours, limit))
    
    # Parse JSON fields
    if results:
        for log in results:
            if log.get('query_params'):
                log['query_params'] = json.loads(log['query_params']) \
                    if isinstance(log['query_params'], str) else log['query_params']
            if log.get('request_body'):
                log['request_body'] = json.loads(log['request_body']) \
                    if isinstance(log['request_body'], str) else log['request_body']
    
    return results if results else []


def get_customer_errors(
    customer_id: str,
    hours: int = 24,
    limit: int = 50
) -> List[Dict[str, Any]]:
    """
    Get error logs for a customer
    
    Args:
        customer_id: Customer ID
        hours: Number of hours to look back
        limit: Maximum number of errors
        
    Returns:
        List of error entries
    """
    
    query = """
        SELECT *
        FROM api_debug_log
        WHERE customer_id = %s
        AND response_status_code >= 400
        AND request_timestamp > NOW() - INTERVAL '%s hours'
        ORDER BY request_timestamp DESC
        LIMIT %s
    """
    
    results = db.execute_query(query, (customer_id, hours, limit))
    return results if results else []


def get_slow_requests(
    customer_id: str,
    threshold_ms: int = 1000,
    limit: int = 50
) -> List[Dict[str, Any]]:
    """
    Get slow requests for a customer
    
    Args:
        customer_id: Customer ID
        threshold_ms: Response time threshold
        limit: Maximum number of results
        
    Returns:
        List of slow requests
    """
    
    query = """
        SELECT *
        FROM api_debug_log
        WHERE customer_id = %s
        AND response_time_ms > %s
        ORDER BY response_time_ms DESC
        LIMIT %s
    """
    
    results = db.execute_query(query, (customer_id, threshold_ms, limit))
    return results if results else []


def get_endpoint_stats(
    endpoint: str,
    hours: int = 24
) -> Dict[str, Any]:
    """
    Get statistics for an endpoint
    
    Args:
        endpoint: Endpoint path
        hours: Number of hours to analyze
        
    Returns:
        Endpoint statistics
    """
    
    query = """
        SELECT 
            COUNT(*) as total_requests,
            COUNT(*) FILTER (WHERE response_status_code < 400) as successful_requests,
            COUNT(*) FILTER (WHERE response_status_code >= 400) as failed_requests,
            AVG(response_time_ms) as avg_response_time,
            MIN(response_time_ms) as min_response_time,
            MAX(response_time_ms) as max_response_time,
            PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY response_time_ms) as p95_response_time,
            PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY response_time_ms) as p99_response_time,
            COUNT(DISTINCT customer_id) as unique_customers
        FROM api_debug_log
        WHERE endpoint = %s
        AND request_timestamp > NOW() - INTERVAL '%s hours'
    """
    
    results = db.execute_query(query, (endpoint, hours))
    
    if results and len(results) > 0:
        return results[0]
    
    return {}


def search_logs(
    customer_id: str,
    search_query: str,
    limit: int = 100
) -> List[Dict[str, Any]]:
    """
    Search logs for a customer
    
    Args:
        customer_id: Customer ID
        search_query: Search term
        limit: Maximum results
        
    Returns:
        Matching log entries
    """
    
    query = """
        SELECT *
        FROM api_debug_log
        WHERE customer_id = %s
        AND (
            endpoint ILIKE %s OR
            error_message ILIKE %s OR
            full_url ILIKE %s
        )
        ORDER BY request_timestamp DESC
        LIMIT %s
    """
    
    search_pattern = f"%{search_query}%"
    
    results = db.execute_query(
        query,
        (customer_id, search_pattern, search_pattern, search_pattern, limit)
    )
    
    return results if results else []


def cleanup_old_logs(days: int = 30) -> Dict[str, int]:
    """
    Clean up old debug logs
    
    Args:
        days: Days to keep
        
    Returns:
        Cleanup statistics
    """
    
    # Delete successful requests older than days
    query1 = """
        DELETE FROM api_debug_log
        WHERE request_timestamp < NOW() - INTERVAL '%s days'
        AND response_status_code < 400
    """
    
    db.execute_query(query1, (days,), fetch=False)
    
    # Delete error requests older than 90 days
    query2 = """
        DELETE FROM api_debug_log
        WHERE request_timestamp < NOW() - INTERVAL '90 days'
        AND response_status_code >= 400
    """
    
    db.execute_query(query2, fetch=False)
    
    return {
        'successful_requests_deleted': 'completed',
        'error_requests_deleted': 'completed'
    }
