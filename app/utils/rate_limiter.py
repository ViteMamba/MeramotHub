"""
Simple in-memory rate limiter for the chatbot endpoint.
Uses a sliding window approach per user ID.
"""
import time
from collections import defaultdict
from typing import Dict, List
from fastapi import HTTPException, status


class RateLimiter:
    def __init__(self, max_requests: int = 10, window_seconds: int = 60):
        """
        Args:
            max_requests: Maximum number of requests allowed per window.
            window_seconds: Time window in seconds.
        """
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._requests: Dict[str, List[float]] = defaultdict(list)

    def check(self, user_id: str) -> None:
        """
        Check if the user has exceeded the rate limit.
        Raises HTTPException 429 if limit exceeded.
        """
        now = time.time()
        window_start = now - self.window_seconds

        # Clean up old timestamps
        self._requests[user_id] = [
            ts for ts in self._requests[user_id] if ts > window_start
        ]

        if len(self._requests[user_id]) >= self.max_requests:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded. Maximum {self.max_requests} requests per {self.window_seconds} seconds."
            )

        self._requests[user_id].append(now)


# Global chatbot rate limiter instance
chatbot_limiter = RateLimiter(max_requests=10, window_seconds=60)
