import sys
from data_fetcher import DataFetcher



# read strm from command line
# strm = int(sys.argv[1])

strm = 1258
database_path = f"data_{strm}.db"
table_name = "sessions"

# Rate limiting configuration - Conservative settings to ensure we get all pages
num_pages_in_batch = 50    # This is now just a legacy parameter
rate_limit_config = {
    "requests_per_minute": 20,  # Conservative: 20 requests per minute
    "delay_between_requests": (2.0, 4.0),  # Longer delays between requests
    "delay_between_batches": (20, 40),  # Longer delays between batches
    "max_retries": 8,  # More retries for reliability
    "backoff_multiplier": 2,  # Exponential backoff multiplier
    "use_proxy_rotation": False,  # Enable if you have proxy list
    "session_timeout": 600,  # Longer session timeout (10 minutes)
}

# fetch data, update db
fetcher = DataFetcher(
    database_path, 
    table_name, 
    strm, 
    num_pages_in_batch,
    rate_limit_config
)
fetcher.run()

# generate json files
# json_gen = JSONGenerator(database_path, table_name, strm)
# json_gen.generate()
