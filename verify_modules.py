import asyncio
import logging
from risk_manager import RiskManager
from market_intelligence import MarketIntelligence
from strategy import DualMovingAverageStrategy
from unittest.mock import MagicMock

# Configure basic logging
logging.basicConfig(level=logging.INFO)

async def test_risk_manager():
    print("\n--- Testing RiskManager ---")
    config = {'budget': 10000, 'stop_loss_pct': 0.02, 'max_daily_loss_pct': 0.05}
    rm = RiskManager(config)
    
    # Test 1: Stop Loss
    entry_price = 100
    current_price = 97 # -3%
    signal = rm.check_exit_conditions(entry_price, current_price)
    print(f"Stop Loss Test: Expected 'STOP_LOSS', Got '{signal}'")
    
    # Test 2: Daily Loss Limit
    rm.update_daily_loss(-600) # Loss > 5% of 10000
    print(f"Daily Loss Halt Test: Expected True, Got {rm.is_trading_halted}")

async def test_market_intelligence():
    print("\n--- Testing MarketIntelligence ---")
    mi = MarketIntelligence()
    
    # Test 1: Fear & Greed Fetch
    data = mi.get_fear_and_greed_index()
    if data:
        print(f"Fear & Greed Data: {data}")
        start_risk = {'position_size_multiplier': 1.0}
        
        # Test 2: Risk Adjustment (Simulate Extreme Fear)
        fake_fear_data = {'value': 10, 'classification': 'Extreme Fear'}
        adjusted = mi.adjust_risk_parameters(start_risk, fake_fear_data)
        print(f"Risk Adjustment Test: Input 1.0 -> Output {adjusted['position_size_multiplier']} (Expected 0.5)")
    else:
        print("Fear & Greed Fetch Failed (Network issue?)")

async def main():
    await test_risk_manager()
    await test_market_intelligence()
    print("\nVerification Complete.")

if __name__ == "__main__":
    asyncio.run(main())
