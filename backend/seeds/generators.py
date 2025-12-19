"""
Helper functions for generating deterministic data.
"""

import uuid
from datetime import datetime, timedelta
import random

# Use a fixed namespace for all seed data to ensure determinism
# UUID v5 generates the same UUID for the same namespace + name
SEED_NAMESPACE = uuid.uuid5(uuid.NAMESPACE_DNS, "contriverse.demo")

def generate_deterministic_id(name: str) -> str:
    """
    Generate a deterministic UUID v5 based on a name string.
    """
    return str(uuid.uuid5(SEED_NAMESPACE, name))

def generate_timestamps(start_date: datetime, count: int, variance_hours: int = 48) -> list[datetime]:
    """
    Generate a list of increasing timestamps starting from start_date.
    Uses a pseudo-random seed to ensure the same sequence.
    """
    # Initialize random with a fixed seed
    rng = random.Random(42)
    
    timestamps = []
    current_time = start_date
    
    for _ in range(count):
        # Advance time by 1-5 days + random variance
        days_delta = rng.randint(1, 5)
        hours_delta = rng.randint(-variance_hours, variance_hours)
        
        current_time += timedelta(days=days_delta, hours=hours_delta)
        timestamps.append(current_time)
        
    return timestamps

def get_demo_avatar(username: str) -> str:
    """Generate a consistent avatar URL."""
    return f"https://api.dicebear.com/7.x/avataaars/svg?seed={username}"
