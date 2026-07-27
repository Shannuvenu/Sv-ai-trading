"""
Upstox instrument mapping for NSE equities.
instrument_key format: NSE_EQ|<symbol>
"""

UPSTOX_INSTRUMENTS = [
    {"symbol": "RELIANCE", "name": "Reliance Industries Ltd", "sector": "Oil & Gas",
     "instrument_key": "NSE_EQ|INE002A01018", "exchange": "NSE", "lot_size": 1},
    {"symbol": "TCS", "name": "Tata Consultancy Services Ltd", "sector": "IT",
     "instrument_key": "NSE_EQ|INE467B01029", "exchange": "NSE", "lot_size": 1},
    {"symbol": "INFY", "name": "Infosys Ltd", "sector": "IT",
     "instrument_key": "NSE_EQ|INE009A01021", "exchange": "NSE", "lot_size": 1},
    {"symbol": "HDFCBANK", "name": "HDFC Bank Ltd", "sector": "Banking",
     "instrument_key": "NSE_EQ|INE040A01034", "exchange": "NSE", "lot_size": 1},
    {"symbol": "ICICIBANK", "name": "ICICI Bank Ltd", "sector": "Banking",
     "instrument_key": "NSE_EQ|INE090A01021", "exchange": "NSE", "lot_size": 1},
    {"symbol": "SBIN", "name": "State Bank of India", "sector": "Banking",
     "instrument_key": "NSE_EQ|INE062A01020", "exchange": "NSE", "lot_size": 1},
    {"symbol": "ITC", "name": "ITC Ltd", "sector": "FMCG",
     "instrument_key": "NSE_EQ|INE154A01025", "exchange": "NSE", "lot_size": 1},
    {"symbol": "LT", "name": "Larsen & Toubro Ltd", "sector": "Infrastructure",
     "instrument_key": "NSE_EQ|INE018A01030", "exchange": "NSE", "lot_size": 1},
    {"symbol": "BHARTIARTL", "name": "Bharti Airtel Ltd", "sector": "Telecom",
     "instrument_key": "NSE_EQ|INE397D01024", "exchange": "NSE", "lot_size": 1},
    {"symbol": "AXISBANK", "name": "Axis Bank Ltd", "sector": "Banking",
     "instrument_key": "NSE_EQ|INE238A01034", "exchange": "NSE", "lot_size": 1},
]

SYMBOL_TO_KEY = {i["symbol"]: i["instrument_key"] for i in UPSTOX_INSTRUMENTS}
KEY_TO_SYMBOL = {i["instrument_key"]: i["symbol"] for i in UPSTOX_INSTRUMENTS}
