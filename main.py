# ==============================================================================
#  File: main.py
#  Description: Kiwoom + Macro Trading Bot Orchestrator
# ==============================================================================

import asyncio
import os
import logging
from datetime import datetime
from dotenv import load_dotenv

# Import Modules
from logger import PerformanceLogger
from notification import NotificationManager
from risk_manager import RiskManager
from kiwoom_client import KiwoomClient
from macro_intelligence import MacroIntelligence

# Load Config
load_dotenv()

# --- Configuration ---
PAPER_TRADING = True  # If True, won't send real orders (simulated in bot logic or bridge)
TARGET_CONDITION_NAME = "Bullish_Breakout_GoldenCross" # Must match HTS Name
ACC_NO = os.getenv("KIWOOM_ACC_NO", "8888888811") 
SCREEN_NO = "1000"

RISK_CONFIG = {
    'budget': 1000000, # 1 Million KRW
    'stop_loss_pct': 0.03,
    'take_profit_pct': 0.07,
    'max_daily_loss_pct': 0.05
}

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("trading_bot.log"),
        logging.StreamHandler()
    ]
)

class TradingBot:
    def __init__(self):
        self.notifier = NotificationManager()
        self.perf_logger = PerformanceLogger()
        self.risk_manager = RiskManager(RISK_CONFIG)
        self.kiwoom = KiwoomClient()
        self.macro = MacroIntelligence()
        
        self.active_positions = {} # {code: {entry_price, qty}}
        self.is_running = True

    async def initialize(self):
        # 1. Check Bridge Connection
        if not self.kiwoom.get_status():
            logging.critical("❌ Kiwoom REST Bridge is NOT running! Start 'kiwoom_bridge.py' (32-bit) first.")
            self.notifier.send_message("❌ Bridge Connection Failed. Please check server.")
            return False

        # 2. Analyze Macro Conditions
        logging.info("🌍 Analyzing Macro Data...")
        macro_data = self.macro.fetch_macro_data()
        regime = self.macro.analyze_market_regime(macro_data)
        
        msg = f"🚀 System Initialized\n- Regime: {regime}\n- VIX: {macro_data.get('VIX', 'N/A')}\n- US10Y: {macro_data.get('US10Y', 'N/A')}"
        logging.info(msg)
        self.notifier.send_message(msg)
        
        if regime == "EXTREME_FEAR":
            logging.warning("⚠️ Market in Extreme Fear. Trading might be limited.")
            # Could adjust risk config here
        
        return True

    async def execute_strategy(self):
        # 1. Trigger Conditional Search
        # In a real scenario, we might query 'get_conditions' first to find the index
        conditions = self.kiwoom.get_conditions()
        cond_idx = conditions.get(TARGET_CONDITION_NAME)
        
        if cond_idx is None:
            logging.warning(f"Condition '{TARGET_CONDITION_NAME}' not found in HTS. Skipping search.")
            return

        logging.info(f"🔎 Scanning Cond: {TARGET_CONDITION_NAME} (Idx: {cond_idx})")
        resp = self.kiwoom.start_condition(SCREEN_NO, TARGET_CONDITION_NAME, cond_idx)
        
        # --- Simulation / Demonstration Logic ---
        # Since we cannot easily get immediate results from the async bridge in this V1 script,
        # we will simulate finding a stock (e.g., Samsung Electronics '005930') to demonstrate
        # the Technical Analysis features requested by the user.
        target_code = "005930.KS" # Samsung Electronics (Yahoo Ticker)
        
        logging.info(f"🧐 Analyzing Target: {target_code}")
        tech_data = self.macro.fetch_technical_indicators(target_code)
        
        if tech_data is not None:
            price = tech_data['Close']
            ma20 = tech_data['SMA_20']
            fib618 = tech_data['Fib_0.618']
            rsi = tech_data['RSI']
            
            logging.info(f"📊 Tech Analysis [{target_code}]")
            logging.info(f"   Price: {price:.0f} | MA20: {ma20:.0f} | RSI: {rsi:.1f}")
            logging.info(f"   Fib(0.618): {tech_data['Fib_0.618']:.0f} | Fib(0.382): {tech_data['Fib_0.382']:.0f}")
            
            # Simple Strategy Example
            if price > ma20 and rsi < 70:
                logging.info(f"✅ BUY SIGNAL: Price > MA20 & RSI({rsi:.1f}) < 70")
                # self.kiwoom.send_order(...) # Would send real order here
            else:
                logging.info("⏸️ HOLD: Conditions not met.")
        else:
            logging.warning("Failed to fetch technical data.")

    async def check_exit_conditions(self):
        # Check all active positions against Risk Manager
        pass

    async def run(self):
        while self.is_running:
            try:
                # 1. Check Macro / Time
                now = datetime.now()
                if now.hour < 9 or now.hour > 15: # KOSPI Market Hours
                     # logging.info("Waiting for market open...")
                     await asyncio.sleep(60)
                     continue

                # 2. Execute Strategy
                await self.execute_strategy()
                
                # 3. Manage Positions
                await self.check_exit_conditions()
                
                await asyncio.sleep(10) # Loop interval
                
            except Exception as e:
                logging.error(f"Loop Error: {e}")
                await asyncio.sleep(5)

if __name__ == "__main__":
    bot = TradingBot()
    loop = asyncio.get_event_loop()
    if loop.run_until_complete(bot.initialize()):
        try:
            loop.run_until_complete(bot.run())
        except KeyboardInterrupt:
            logging.info("Bot Stopped.")
