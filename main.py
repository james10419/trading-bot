# ==============================================================================
#  File: main.py
#  Description: Modular Trading Bot Orchestrator
#  Features:
#    - Multi-Strategy Support (Dual EMA, Volatility Breakout, RSI)
#    - Risk Management (Stop Loss, Take Profit, Daily Loss Limit)
#    - Automated Logging & Telegram Notifications
# ==============================================================================

import ccxt.async_support as ccxt
import asyncio
import os
import logging
import random
from datetime import datetime
from dotenv import load_dotenv

# Import Custom Modules
from logger import PerformanceLogger
from notification import NotificationManager
from risk_manager import RiskManager
from strategy import DualMovingAverageStrategy, VolatilityBreakoutStrategy, RSIStrategy
from market_intelligence import MarketIntelligence

# Load Environment Variables
load_dotenv()

# --- Configuration ---
PAPER_TRADING = True         # Set to False for REAL TRADING
EXCHANGE_NAME = 'upbit'
SYMBOL = 'BTC/KRW'
BUDGET = 500000          # Total Trading Budget (KRW)
STRATEGY_NAME = 'DualEMA' # Options: 'DualEMA', 'VolatilityBreakout', 'RSI'

# Risk Configuration
RISK_CONFIG = {
    'budget': BUDGET,
    'stop_loss_pct': 0.02,       # 2% Stop Loss
    'take_profit_pct': 0.05,     # 5% Take Profit
    'max_daily_loss_pct': 0.05   # Halt if daily loss > 5%
}

# Logging Setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("trading_bot.log"),
        logging.StreamHandler()
    ]
)

class MockExchange:
    """Simulates exchange operations for Paper Trading."""
    def __init__(self, exchange_real):
        self.exchange = exchange_real # Use real exchange for data fetching
        self.orders = {}

    async def load_markets(self):
        return await self.exchange.load_markets()

    async def fetch_ohlcv(self, symbol, timeframe='1h', limit=100):
        # Pass through to real exchange for data
        return await self.exchange.fetch_ohlcv(symbol, timeframe, limit)

    async def fetch_ticker(self, symbol):
        # Pass through to real exchange for data
        return await self.exchange.fetch_ticker(symbol)

    async def create_market_buy_order(self, symbol, amount):
        ticker = await self.fetch_ticker(symbol)
        price = ticker['last']
        logging.info(f"[PAPER] Simulating BUY {symbol}: {amount} @ {price}")
        
        # Simulate order response
        return {
            'id': f'sim-buy-{int(datetime.now().timestamp())}',
            'symbol': symbol,
            'type': 'market',
            'side': 'buy',
            'amount': amount,
            'price': price,
            'average': price,
            'filled': amount,
            'timestamp': int(datetime.now().timestamp() * 1000)
        }

    async def create_market_sell_order(self, symbol, amount):
        ticker = await self.fetch_ticker(symbol)
        price = ticker['last']
        logging.info(f"[PAPER] Simulating SELL {symbol}: {amount} @ {price}")
        
        return {
            'id': f'sim-sell-{int(datetime.now().timestamp())}',
            'symbol': symbol,
            'type': 'market',
            'side': 'sell',
            'amount': amount,
            'price': price,
            'average': price,
            'filled': amount,
            'timestamp': int(datetime.now().timestamp() * 1000)
        }
        
    async def close(self):
        await self.exchange.close()

class TradingBot:
    def __init__(self):
        self.symbol = SYMBOL
        self.budget = BUDGET
        self.position = {} # {'entry_price', 'amount', 'timestamp'}
        
        # Initialize Modules
        self.notifier = NotificationManager()
        self.perf_logger = PerformanceLogger()
        self.risk_manager = RiskManager(RISK_CONFIG)
        self.market_intel = MarketIntelligence()
        
        # Initialize Exchange
        self._real_exchange = self._init_exchange_connection()
        
        if PAPER_TRADING:
            logging.warning("⚠️ STARTING IN PAPER TRADING MODE ⚠️")
            self.exchange = MockExchange(self._real_exchange)
            self.notifier.send_message(f"🧪 Paper Trading Bot Started\n- Symbol: {self.symbol}")
        else:
            logging.warning("🚨 STARTING IN REAL TRADING MODE 🚨")
            self.exchange = self._real_exchange
            
        self.strategy = self._init_strategy()

    def _init_exchange_connection(self):
        api_key = os.getenv(f'{EXCHANGE_NAME.upper()}_ACCESS_KEY')
        secret_key = os.getenv(f'{EXCHANGE_NAME.upper()}_SECRET_KEY')
        
        # For Paper Trading, allow missing keys if we only need public data (though CCXT often needs keys for private endpoints, fetching OHLCV is usually public)
        # However, to keep it simple, we'll still require keys or use placeholders if totally public.
        # But user likely wants to test WITH their keys eventually. 
        # Let's keep logic: if keys missing and PAPER_TRADING is True, maybe warn but proceed?
        # Actually safer to enforce keys or use a public-only instance if possible, but CCXT structure desires keys.
        
        if not api_key or not secret_key:
             if PAPER_TRADING:
                 logging.warning("API Keys missing! Using public-only mode for Paper Trading data.")
                 # Initialize without keys
                 exchange_class = getattr(ccxt, EXCHANGE_NAME)
                 return exchange_class()
             else:
                raise ValueError("API Keys missing in .env for Real Trading")
        
        exchange_class = getattr(ccxt, EXCHANGE_NAME)
        return exchange_class({'apiKey': api_key, 'secret': secret_key})

    # _init_exchange removed in favor of _init_exchange_connection logic above

    def _init_strategy(self):
        if STRATEGY_NAME == 'DualEMA':
            return DualMovingAverageStrategy(self.exchange, self.symbol)
        elif STRATEGY_NAME == 'VolatilityBreakout':
            return VolatilityBreakoutStrategy(self.exchange, self.symbol)
        elif STRATEGY_NAME == 'RSI':
            return RSIStrategy(self.exchange, self.symbol)
        else:
            raise ValueError(f"Unknown Strategy: {STRATEGY_NAME}")

    async def initialize(self):
        try:
            await self.exchange.load_markets()
            await self.exchange.load_markets()
            mode = "🧪 PAPER TRADING" if PAPER_TRADING else "💸 REAL TRADING"
            self.notifier.send_message(f"🚀 Bot Initialized ({mode})\n- Strategy: {STRATEGY_NAME}\n- Symbol: {self.symbol}")
            return True
        except Exception as e:
            logging.error(f"Initialization Failed: {e}")
            return False

    async def execute_buy(self):
        try:
            current_price = (await self.exchange.fetch_ticker(self.symbol))['last']
            
            # Market Intelligence: Check Sentiment
            fng_data = self.market_intel.get_fear_and_greed_index()
            # self.market_intel.get_seeking_alpha_sentiment(self.symbol) # Optional Integration

            # Adjust Risk Config based on Sentiment
            adjusted_risk = self.market_intel.adjust_risk_parameters(RISK_CONFIG, fng_data)
            size_multiplier = adjusted_risk.get('position_size_multiplier', 1.0) # Default 1.0

            # Risk Manager: Calculate Safe Position Size
            # For simplicity in this demo, we use close to full budget but check daily limits
            base_amount = self.risk_manager.calculate_position_size(self.budget, current_price)
            amount = base_amount * size_multiplier
            
            if amount <= 0:
                logging.warning("Buy skipped due to Risk Manager (Zero Amount).")
                return

            logging.info(f"Attempting to Buy {self.symbol} at ~{current_price} (Multiplier: {size_multiplier})")
            
            # Execute Order (Market Buy)
            # In production, use limit orders or check order book
            order = await self.exchange.create_market_buy_order(self.symbol, amount)
            
            entry_price = order.get('average') or order.get('price') or current_price
            filled_amount = order.get('filled') or amount

            self.position = {
                'entry_price': entry_price,
                'amount': filled_amount,
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }

            msg = f"🟢 BUY Executed\nPrice: {entry_price:,.2f}\nAmount: {filled_amount:.6f}"
            self.notifier.send_message(msg)
            logging.info(msg)

        except Exception as e:
            logging.error(f"Buy Order Failed: {e}")
            self.notifier.send_message(f"⚠️ Buy Failed: {e}")

    async def execute_sell(self, reason):
        if not self.position:
            return

        try:
            amount = self.position['amount']
            logging.info(f"Attempting to Sell {self.symbol} ({reason})")
            
            order = await self.exchange.create_market_sell_order(self.symbol, amount)
            
            # Post-Trade Logic
            current_price = (await self.exchange.fetch_ticker(self.symbol))['last']
            exit_price = order.get('average') or order.get('price') or current_price
            
            entry_price = self.position['entry_price']
            profit_krw = (exit_price - entry_price) * amount
            profit_pct = (profit_krw / (entry_price * amount)) * 100

            # Update Risk Manager
            halted = self.risk_manager.update_daily_loss(profit_krw)
            
            # Log Trade
            trade_details = {
                'entry_time': self.position['timestamp'],
                'exit_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'symbol': self.symbol,
                'entry_price': entry_price,
                'exit_price': exit_price,
                'amount': amount,
                'profit_krw': round(profit_krw, 2),
                'profit_percent': round(profit_pct, 2)
            }
            self.perf_logger.log_trade(trade_details)

            # Notify
            icon = "💰" if profit_krw > 0 else "📉"
            msg = (f"{icon} SELL Executed ({reason})\n"
                   f"Profit: {profit_krw:,.2f} KRW ({profit_pct:.2f}%)")
            
            if halted:
                msg += "\n🛑 Trading Halted: Max Daily Loss Exceeded."
            
            self.notifier.send_message(msg)
            logging.info(msg)

            self.position = {} # Clear position

        except Exception as e:
            logging.error(f"Sell Order Failed: {e}")
            self.notifier.send_message(f"⚠️ Sell Failed: {e}")

    async def run(self):
        # Initial Data Prep
        await self.strategy.prepare_data()

        while True:
            try:
                # 1. Daily Reset Check (e.g., 09:00 KST)
                now = datetime.now()
                if now.hour == 9 and now.minute == 0 and now.second < 10:
                    self.risk_manager.reset_daily_stats()
                    self.strategy.reset()
                    await self.strategy.prepare_data()
                    await asyncio.sleep(60)
                    continue

                if self.risk_manager.is_trading_halted:
                    logging.info("Trading halted due to risk limits. Waiting...")
                    await asyncio.sleep(600) # Check every 10 mins
                    continue

                # 2. Strategy Logic
                signal = await self.strategy.get_signal()
                
                # 3. Risk Management Checks (Stop Loss / Take Profit)
                if self.position:
                    ticker = await self.exchange.fetch_ticker(self.symbol)
                    current_price = ticker['last']
                    
                    risk_signal = self.risk_manager.check_exit_conditions(
                        self.position['entry_price'], current_price
                    )
                    
                    if risk_signal == 'STOP_LOSS':
                        await self.execute_sell(reason="Stop Loss")
                        continue
                    elif risk_signal == 'TAKE_PROFIT':
                        await self.execute_sell(reason="Take Profit")
                        continue

                # 4. Signal Execution
                if signal == 'BUY' and not self.position:
                    await self.execute_buy()
                elif signal == 'SELL' and self.position:
                    await self.execute_sell(reason="Strategy Signal")

            except Exception as e:
                logging.error(f"Main Loop Error: {e}")
                self.notifier.send_message(f"🚨 Bot Error: {e}")
            
            await asyncio.sleep(2)

    async def close(self):
        if self.exchange:
            await self.exchange.close()
            logging.info("Exchange connection closed.")
            self.notifier.send_message("💤 Bot Stopped.")

async def main():
    bot = TradingBot()
    if await bot.initialize():
        try:
            await bot.run()
        except KeyboardInterrupt:
            logging.info("Bot stopped by user.")
        finally:
            await bot.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"Critical Error: {e}")
