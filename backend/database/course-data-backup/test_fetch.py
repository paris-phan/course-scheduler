#!/usr/bin/env python3
"""
Test script to verify the improved data fetching logic.
This will fetch a small number of pages to test the rate limiting and pagination.
"""

import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from data_fetcher import DataFetcher

async def test_fetch():
    """Test the improved fetching logic with a small number of pages"""
    
    # Test configuration
    strm = 1258  # Current semester
    database_path = "test_data.db"
    table_name = "test_sessions"
    
    # Very conservative rate limiting for testing
    rate_limit_config = {
        "requests_per_minute": 10,  # Very conservative
        "delay_between_requests": (3.0, 6.0),  # Longer delays
        "delay_between_batches": (30, 60),  # Much longer delays
        "max_retries": 3,  # Fewer retries for testing
        "backoff_multiplier": 2,
        "use_proxy_rotation": False,
        "session_timeout": 300,
    }
    
    print("🧪 Testing improved data fetching logic...")
    print(f"📚 Semester: {strm}")
    print(f"⚙️ Rate limit: {rate_limit_config['requests_per_minute']} requests/minute")
    print(f"⏱️ Delays: {rate_limit_config['delay_between_requests']} seconds between requests")
    print()
    
    # Create fetcher
    fetcher = DataFetcher(
        database_path, 
        table_name, 
        strm, 
        num_pages_in_batch=10,  # Small batch for testing
        rate_limit_config=rate_limit_config
    )
    
    try:
        # Test fetching (this will stop after 3 consecutive empty pages)
        await fetcher.get_all_courses_in_semester()
        
        print(f"\n✅ Test completed!")
        print(f"📊 Total courses fetched: {len(fetcher.courses)}")
        
        if fetcher.courses:
            print(f"📝 Sample course: {fetcher.courses[0].get('subject', 'N/A')} {fetcher.courses[0].get('catalog_nbr', 'N/A')}")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(test_fetch()) 
