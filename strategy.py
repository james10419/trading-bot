import logging
from abc import ABC, abstractmethod
import pandas as pd
import pandas_ta as ta

class BaseStrategy(ABC):
    """Abstract base class for all trading strategies."""
    def __init__(self, exchange, symbol, params):
        self.exchange = exchange
        self.symbol = symbol
        self.params = params
        logging.info(f"Strategy Initialized: {self.__class__.__name__} with params: {params}")

    @abstractmethod
    async def get_signal(self):
        """Returns 'BUY', 'SELL', or 'HOLD'."""
        pass
    
    async def prepare_data(self):
        """Optional hook for data preparation (e.g., daily reset)."""
        pass

    def reset(self):
        """Optional hook for state reset."""
        pass


class DualMovingAverageStrategy(BaseStrategy):
    """
    Dual Moving Average Crossover Strategy.
    Buys when Short EMA > Long EMA (Golden Cross).
    Sells when Short EMA < Long EMA (Dead Cross).
    """
    def __init__(self, exchange, symbol, params=None):
        if params is None:
            params = {'short_window': 10, 'long_window': 50, 'timeframe': '1h'}
        super().__init__(exchange, symbol, params)
        self.short_window = self.params.get('short_window', 10)
        self.long_window = self.params.get('long_window', 50)
        self.timeframe = self.params.get('timeframe', '1h')

    async def get_signal(self):
        try:
            # Fetch enough data to calculate EMAs
            limit = self.long_window + 10
            ohlcv = await self.exchange.fetch_ohlcv(self.symbol, timeframe=self.timeframe, limit=limit)
            if len(ohlcv) < limit:
                logging.warning("DualEMA: Not enough data for EMA calculation.")
                return 'HOLD'

            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            
            # Calculate EMAs
            short_ema = df.ta.ema(length=self.short_window)
            long_ema = df.ta.ema(length=self.long_window)
            
            if short_ema is None or long_ema is None:
                return 'HOLD'

            current_short = short_ema.iloc[-1]
            current_long = long_ema.iloc[-1]
            prev_short = short_ema.iloc[-2]
            prev_long = long_ema.iloc[-2]

            # logging.info(f"DualEMA: Short={current_short:.2f}, Long={current_long:.2f}")

            # Golden Cross: Short crosses above Long
            if prev_short <= prev_long and current_short > current_long:
                logging.info(f"*** GOLDEN CROSS: Short({current_short:.2f}) > Long({current_long:.2f}) ***")
                return 'BUY'
            
            # Dead Cross: Short crosses below Long
            if prev_short >= prev_long and current_short < current_long:
                logging.info(f"*** DEAD CROSS: Short({current_short:.2f}) < Long({current_long:.2f}) ***")
                return 'SELL'

        except Exception as e:
            logging.error(f"DualEMA Error: {e}")
        
        return 'HOLD'


class VolatilityBreakoutStrategy(BaseStrategy):
    """Ported Volatility Breakout Strategy."""
    def __init__(self, exchange, symbol, params=None):
        if params is None:
            params = {'k_value': 0.5}
        super().__init__(exchange, symbol, params)
        self.target_price = None
        self.bought = False

    async def prepare_data(self):
        try:
            ohlcv = await self.exchange.fetch_ohlcv(self.symbol, '1d', limit=2)
            if len(ohlcv) < 2:
                self.target_price = None
                return

            yesterday = ohlcv[-2]
            high = yesterday[2]
            low = yesterday[3]
            today_open = ohlcv[-1][1]

            volatility = high - low
            self.target_price = today_open + (volatility * self.params.get('k_value', 0.5))
            logging.info(f"VolatilityBreakout: Target Price = {self.target_price:,.2f} KRW")
        except Exception as e:
            logging.error(f"VolatilityBreakout prepare_data error: {e}")

    async def get_signal(self):
        if self.bought or self.target_price is None:
            return 'HOLD'

        try:
            ticker = await self.exchange.fetch_ticker(self.symbol)
            current_price = ticker['last']

            if current_price > self.target_price:
                logging.info(f"*** Volatility Breakout Buy: {current_price} > {self.target_price} ***")
                self.bought = True
                return 'BUY'
        except Exception as e:
            logging.error(f"VolatilityBreakout get_signal error: {e}")

        return 'HOLD'

    def reset(self):
        self.bought = False
        self.target_price = None
        logging.info("VolatilityBreakout state reset.")


class RSIStrategy(BaseStrategy):
    """Ported RSI Strategy."""
    def __init__(self, exchange, symbol, params=None):
        if params is None:
            params = {'rsi_period': 14, 'oversold': 30, 'overbought': 70}
        super().__init__(exchange, symbol, params)
        self.timeframe = '1h'

    async def get_signal(self):
        try:
            ohlcv = await self.exchange.fetch_ohlcv(self.symbol, timeframe=self.timeframe, limit=100)
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            
            rsi_period = self.params.get('rsi_period', 14)
            rsi = df.ta.rsi(length=rsi_period)
            
            if rsi is None or rsi.empty:
                return 'HOLD'
            
            last_rsi = rsi.iloc[-1]
            oversold = self.params.get('oversold', 30)
            overbought = self.params.get('overbought', 70)

            # logging.info(f"RSI: {last_rsi:.2f}")

            if last_rsi < oversold:
                logging.info(f"*** RSI Oversold Buy: {last_rsi:.2f} < {oversold} ***")
                return 'BUY'
            elif last_rsi > overbought:
                logging.info(f"*** RSI Overbought Sell: {last_rsi:.2f} > {overbought} ***")
                return 'SELL'
        except Exception as e:
            logging.error(f"RSI Error: {e}")

        return 'HOLD'
