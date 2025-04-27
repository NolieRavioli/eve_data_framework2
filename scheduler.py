import schedule, time
from fetchers import market, wallet, contracts  # etc.
from auth import token_store

def job_update_markets():
    tokens = token_store.load_all()  # load or get tokens from memory
    market.update_markets(tokens, db)

# Set up intervals
schedule.every(30).minutes.do(job_update_markets)
schedule.every(60).minutes.do(job_update_wallets)
# ... other jobs

while True:
    schedule.run_pending()
    time.sleep(60)
