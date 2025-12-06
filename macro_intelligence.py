import yfinance as yf
import pandas as pd
import pandas_ta as ta
import logging

class MacroIntelligence:
    """
    Fetches macroeconomic data and advanced technical indicators.
    Sources: Yahoo Finance (yfinance)
    """
    def __init__(self):
        self.tickers = {
            'VIX': '^VIX',          # Volatility Index
            'US10Y': '^TNX',        # US 10-Year Treasury Yield
            'KRWUSD': 'KRW=X',      # KRW/USD Exchange Rate
            'SP500': '^GSPC',       # S&P 500
            'NASDAQ': '^IXIC'       # NASDAQ Composite
        }

    def fetch_macro_data(self):
        """
        Fetches latest macro indicators.
        Returns: Dict of {indicator_name: value}
        """
        data = {}
        try:
            # Fetch all at once for efficiency
            symbols = list(self.tickers.values())
            tickers = yf.Tickers(' '.join(symbols))
            
            for name, symbol in self.tickers.items():
                try:
                    hist = tickers.tickers[symbol].history(period="1d")
                    if not hist.empty:
                        data[name] = hist['Close'].iloc[-1]
                    else:
                        logging.warning(f"No data for {name}")
                except Exception as e:
                    logging.warning(f"Error fetching {name}: {e}")
                    
            logging.info(f"Macro Data Fetched: {data}")
            return data
            
        except Exception as e:
            logging.error(f"Macro Fetch Critical Error: {e}")
            return {}

    def fetch_technical_indicators(self, symbol, timeframe='1d', period='1y'):
        """
        Calculates advanced technicals: Fibonacci, Bollinger, RSI, MA.
        Note: Yahoo Finance data is often delayed 15-20 mins.
        """
        try:
            # Map timeframe to yfinance interval
            interval_map = {'1d': '1d', '1h': '1h', '15m': '15m'}
            interval = interval_map.get(timeframe, '1d')
            
            df = yf.download(symbol, period=period, interval=interval, progress=False)
            if df.empty:
                return None

            # Ensure columns are flat if MultiIndex
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)

            # 1. Moving Averages
            df['SMA_20'] = ta.sma(df['Close'], length=20)
            df['SMA_60'] = ta.sma(df['Close'], length=60)
            df['SMA_120'] = ta.sma(df['Close'], length=120)

            # 2. RSI
            df['RSI'] = ta.rsi(df['Close'], length=14)

            # 3. Bollinger Bands
            bbands = ta.bbands(df['Close'], length=20, std=2)
            if bbands is not None:
                # Rename for clarity (panads-ta returns specific names like BBL_20_2.0)
                df = pd.concat([df, bbands], axis=1)

            # 4. Fibonacci Retracement (Based on recent High/Low)
            # Find recent High/Low over last 100 periods
            recent_high = df['High'].rolling(window=100).max()
            recent_low = df['Low'].rolling(window=100).min()
            
            diff = recent_high - recent_low
            df['Fib_0.236'] = recent_high - (diff * 0.236)
            df['Fib_0.382'] = recent_high - (diff * 0.382)
            df['Fib_0.500'] = recent_high - (diff * 0.5)
            df['Fib_0.618'] = recent_high - (diff * 0.618)

            return df.iloc[-1] # Return latest row
            
        except Exception as e:
            logging.error(f"Technical Calc Error for {symbol}: {e}")
            return None

    def analyze_market_regime(self, macro_data):
        """
        Determines market regime (Risk-On / Risk-Off).
        """
        if not macro_data: return "NEUTRAL"
        
        vix = macro_data.get('VIX', 0)
        us10y = macro_data.get('US10Y', 0)
        
        # Simple Heuristic
        if vix > 30:
            return "EXTREME_FEAR" # Risk-Off
        elif vix > 20:
             return "FEAR"
        elif us10y > 4.5:
             # High yields might pressure tech stocks
             return "HIGH_YIELD_CAUTION"
             
        return "NORMAL"
