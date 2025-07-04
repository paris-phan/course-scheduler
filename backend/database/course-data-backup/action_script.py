import sys
from data_fetcher import DataFetcher
import json


# read strm from command line
# strm = int(sys.argv[1])

# Optional: read start_page from command line (defaults to 1 if not provided)
if len(sys.argv) > 1:
    start_page = int(sys.argv[1])
else:
    start_page = 1

strm = 1258
table_name = "courses" 

num_pages_in_batch = 90-start_page   # make sure this is more than number of pages in sis

print(f"Starting fetch for semester {strm} from page {start_page}")

# fetch data, update db
fetcher = DataFetcher(table_name, strm, num_pages_in_batch, start_page)
fetcher.run()

