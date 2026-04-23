import httpx
import asyncio
from typing import Dict, Any, Optional

GRAPHQL_ENDPOINT = "https://leetcode.com/graphql"

class LeetCodeServiceError(Exception):
    """Base exception for LeetCode service errors"""
    pass

async def execute_graphql(query: str, variables: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Execute a GraphQL query against the LeetCode API.
    """
    headers = {
        "Content-Type": "application/json",
        "Referer": "https://leetcode.com",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    
    payload = {
        "query": query,
        "variables": variables or {}
    }
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(GRAPHQL_ENDPOINT, json=payload, headers=headers, timeout=10.0)
            response.raise_for_status()
            
            result = response.json()
            
            if "errors" in result:
                error_msg = result["errors"][0].get("message", "Unknown GraphQL error")
                raise LeetCodeServiceError(f"GraphQL error: {error_msg}")
            
            if "data" not in result:
                raise LeetCodeServiceError("No data returned from GraphQL query")
            
            return result["data"]
            
        except httpx.HTTPStatusError as e:
            raise LeetCodeServiceError(f"HTTP error! status: {e.response.status_code}")
        except httpx.RequestError as e:
            raise LeetCodeServiceError(f"Request error: {str(e)}")
        except Exception as e:
            raise LeetCodeServiceError(f"Unexpected error: {str(e)}")

async def execute_graphql_with_retry(
    query: str, 
    variables: Dict[str, Any] = None, 
    retries: int = 3, 
    delay_ms: int = 1000
) -> Dict[str, Any]:
    """
    Execute GraphQL with error handling and retry logic.
    """
    last_error = None
    
    for attempt in range(1, retries + 1):
        try:
            return await execute_graphql(query, variables)
        except LeetCodeServiceError as e:
            last_error = e
            if attempt < retries:
                delay = (delay_ms / 1000.0) * (2 ** (attempt - 1))
                await asyncio.sleep(delay)
    
    raise last_error or LeetCodeServiceError("GraphQL request failed after retries")
