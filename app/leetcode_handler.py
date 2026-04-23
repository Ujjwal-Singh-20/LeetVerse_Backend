"""
LeetCode API Handler Functions
Provides high-level functions to fetch and process LeetCode data.
"""

from typing import Optional, Dict, Any, List
import graphql_queries as queries
from leetcode_service import execute_graphql_with_retry

class FetchOptions:
    def __init__(self, retries: int = 3, delay_ms: int = 1000):
        self.retries = retries
        self.delay_ms = delay_ms

async def fetch_user_profile(username: str, options: Optional[FetchOptions] = None):
    """Fetch user profile summary"""
    opt = options or FetchOptions()
    return await execute_graphql_with_retry(
        queries.USER_PROFILE_QUERY,
        {"username": username},
        opt.retries,
        opt.delay_ms
    )

async def fetch_user_badges(username: str, options: Optional[FetchOptions] = None):
    """Fetch user badges"""
    opt = options or FetchOptions()
    return await execute_graphql_with_retry(
        queries.USER_PROFILE_QUERY,
        {"username": username},
        opt.retries,
        opt.delay_ms
    )

async def fetch_solved_problems(username: str, options: Optional[FetchOptions] = None):
    """Fetch solved problems count"""
    opt = options or FetchOptions()
    return await execute_graphql_with_retry(
        queries.USER_PROFILE_QUERY,
        {"username": username},
        opt.retries,
        opt.delay_ms
    )

async def fetch_user_contest(username: str, options: Optional[FetchOptions] = None):
    """Fetch user contest details"""
    opt = options or FetchOptions()
    return await execute_graphql_with_retry(
        queries.CONTEST_QUERY,
        {"username": username},
        opt.retries,
        opt.delay_ms
    )

async def fetch_contest_history(username: str, options: Optional[FetchOptions] = None):
    """Fetch user contest history"""
    opt = options or FetchOptions()
    return await execute_graphql_with_retry(
        queries.CONTEST_QUERY,
        {"username": username},
        opt.retries,
        opt.delay_ms
    )

async def fetch_recent_submissions(username: str, limit: int = 20, options: Optional[FetchOptions] = None):
    """Fetch recent submissions"""
    opt = options or FetchOptions()
    return await execute_graphql_with_retry(
        queries.SUBMISSION_QUERY,
        {"username": username, "limit": limit},
        opt.retries,
        opt.delay_ms
    )

async def fetch_recent_accepted_submissions(username: str, limit: int = 20, options: Optional[FetchOptions] = None):
    """Fetch recent accepted submissions"""
    opt = options or FetchOptions()
    return await execute_graphql_with_retry(
        queries.AC_SUBMISSION_QUERY,
        {"username": username, "limit": limit},
        opt.retries,
        opt.delay_ms
    )

async def fetch_submission_calendar(username: str, year: Optional[int] = None, options: Optional[FetchOptions] = None):
    """Fetch submission calendar"""
    opt = options or FetchOptions()
    import datetime
    current_year = year or datetime.datetime.now().year
    return await execute_graphql_with_retry(
        queries.USER_PROFILE_CALENDAR_QUERY,
        {"username": username, "year": current_year},
        opt.retries,
        opt.delay_ms
    )

async def fetch_language_stats(username: str, options: Optional[FetchOptions] = None):
    """Fetch language statistics"""
    opt = options or FetchOptions()
    return await execute_graphql_with_retry(
        queries.LANGUAGE_STATS_QUERY,
        {"username": username},
        opt.retries,
        opt.delay_ms
    )

async def fetch_skill_stats(username: str, options: Optional[FetchOptions] = None):
    """Fetch skill statistics"""
    opt = options or FetchOptions()
    return await execute_graphql_with_retry(
        queries.SKILL_STATS_QUERY,
        {"username": username},
        opt.retries,
        opt.delay_ms
    )

async def fetch_question_progress(username: str, options: Optional[FetchOptions] = None):
    """Fetch question progress"""
    opt = options or FetchOptions()
    return await execute_graphql_with_retry(
        queries.USER_QUESTION_PROGRESS_QUERY,
        {"username": username},
        opt.retries,
        opt.delay_ms
    )

async def fetch_daily_problem(options: Optional[FetchOptions] = None):
    """Fetch daily problem"""
    opt = options or FetchOptions()
    return await execute_graphql_with_retry(
        queries.DAILY_PROBLEM_QUERY,
        {},
        opt.retries,
        opt.delay_ms
    )

async def fetch_problem(title_slug: str, options: Optional[FetchOptions] = None):
    """Fetch specific problem by title slug"""
    opt = options or FetchOptions()
    return await execute_graphql_with_retry(
        queries.SELECT_PROBLEM_QUERY,
        {"titleSlug": title_slug},
        opt.retries,
        opt.delay_ms
    )

async def fetch_problems(
    limit: int = 20,
    skip: int = 0,
    tags: List[str] = None,
    difficulty: Optional[str] = None,
    options: Optional[FetchOptions] = None
):
    """Fetch problems list with filters"""
    opt = options or FetchOptions()
    return await execute_graphql_with_retry(
        queries.PROBLEM_LIST_QUERY,
        {
            "categorySlug": "",
            "limit": limit,
            "skip": skip,
            "filters": {
                "tags": tags or [],
                "difficulty": difficulty
            }
        },
        opt.retries,
        opt.delay_ms
    )

async def fetch_official_solution(title_slug: str, options: Optional[FetchOptions] = None):
    """Fetch official solution for a problem"""
    opt = options or FetchOptions()
    return await execute_graphql_with_retry(
        queries.OFFICIAL_SOLUTION_QUERY,
        {"titleSlug": title_slug},
        opt.retries,
        opt.delay_ms
    )

async def fetch_all_contests(options: Optional[FetchOptions] = None):
    """Fetch all contests"""
    opt = options or FetchOptions()
    return await execute_graphql_with_retry(
        queries.ALL_CONTEST_QUERY,
        {},
        opt.retries,
        opt.delay_ms
    )

async def fetch_upcoming_contests(options: Optional[FetchOptions] = None):
    """Fetch upcoming contests"""
    import time
    data = await fetch_all_contests(options)
    now = int(time.time())
    
    all_contests = data.get("allContests", [])
    upcoming = [c for c in all_contests if c.get("startTime", 0) > now]
    
    return {**data, "allContests": upcoming}

async def fetch_trending_discussions(first: int = 20, options: Optional[FetchOptions] = None):
    """Fetch trending discussions"""
    opt = options or FetchOptions()
    return await execute_graphql_with_retry(
        queries.TRENDING_DISCUSS_QUERY,
        {"first": first},
        opt.retries,
        opt.delay_ms
    )

async def fetch_discussion_topic(topic_id: int, options: Optional[FetchOptions] = None):
    """Fetch specific discussion topic"""
    opt = options or FetchOptions()
    return await execute_graphql_with_retry(
        queries.DISCUSS_TOPIC_QUERY,
        {"topicId": topic_id},
        opt.retries,
        opt.delay_ms
    )

async def fetch_discussion_comments(
    topic_id: int,
    order_by: str = "newest_to_oldest",
    page_no: int = 1,
    num_per_page: int = 10,
    options: Optional[FetchOptions] = None
):
    """Fetch discussion comments"""
    opt = options or FetchOptions()
    return await execute_graphql_with_retry(
        queries.DISCUSS_COMMENTS_QUERY,
        {"topicId": topic_id, "orderBy": order_by, "pageNo": page_no, "numPerPage": num_per_page},
        opt.retries,
        opt.delay_ms
    )

async def fetch_contest_ranking_info(username: str, options: Optional[FetchOptions] = None):
    """Fetch user contest ranking info"""
    opt = options or FetchOptions()
    return await execute_graphql_with_retry(
        queries.USER_CONTEST_RANKING_INFO_QUERY,
        {"username": username},
        opt.retries,
        opt.delay_ms
    )

async def fetch_aggregated_user_profile(username: str, options: Optional[FetchOptions] = None):
    """Fetch aggregated user profile (full profile)"""
    opt = options or FetchOptions()
    return await execute_graphql_with_retry(
        queries.GET_USER_PROFILE_QUERY,
        {"username": username},
        opt.retries,
        opt.delay_ms
    )
