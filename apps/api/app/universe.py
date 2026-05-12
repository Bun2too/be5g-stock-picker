MEGA_CAPS = [
    "AAPL","MSFT","NVDA","AMZN","GOOGL","META","TSLA","BRK.B","LLY","JPM",
    "V","UNH","XOM","AVGO","MA","COST","HD","PG","ORCL","KO",
    "PEP","ABBV","MRK","CVX","WMT","BAC","ADBE","CRM","NFLX","TMO"
]

NASDAQ100_LIKE = [
    "AAPL","MSFT","NVDA","AMZN","GOOGL","META","TSLA","AVGO","COST","ADBE","NFLX","ORCL"
]

SP500_LIKE = [
    "AAPL","MSFT","NVDA","AMZN","GOOGL","META","BRK.B","LLY","JPM","XOM","UNH","V","PG","HD","KO"
]

def get_universe(name: str):
    name = (name or "").lower()
    if name == "nasdaq100_like":
        return NASDAQ100_LIKE
    if name == "sp500_like":
        return SP500_LIKE
    return MEGA_CAPS
