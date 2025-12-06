import logging
import pandas as pd

class RiskManager:
    """
    Manages trading risks including Stop Loss, Take Profit, and Daily Loss Limits.
    """
    def __init__(self, config):
        """
        :param config: Dictionary containing risk parameters
                       (stop_loss_pct, take_profit_pct, max_daily_loss_pct, etc.)
        """
        self.stop_loss_pct = config.get('stop_loss_pct', 0.02) # Default 2%
        self.take_profit_pct = config.get('take_profit_pct', 0.05) # Default 5%
        self.max_daily_loss_pct = config.get('max_daily_loss_pct', 0.05) # Default 5% of total budget
        
        self.initial_budget = config.get('budget', 50000)
        self.daily_loss = 0.0
        self.is_trading_halted = False

    def check_exit_conditions(self, entry_price, current_price, position_duration_mins=0):
        """
        Checks if the current price triggers a Stop Loss or Take Profit.
        :return: 'STOP_LOSS', 'TAKE_PROFIT', or None
        """
        if entry_price <= 0:
            return None

        # Calculate percentage change
        pct_change = (current_price - entry_price) / entry_price

        # Stop Loss Check
        if pct_change <= -self.stop_loss_pct:
            logging.warning(f"RiskManager: Stop Loss triggered! Change: {pct_change*100:.2f}%")
            return 'STOP_LOSS'

        # Take Profit Check
        if pct_change >= self.take_profit_pct:
            logging.info(f"RiskManager: Take Profit triggered! Change: {pct_change*100:.2f}%")
            return 'TAKE_PROFIT'

        return None

    def calculate_position_size(self, total_budget, current_price, volatility_atr=None):
        """
        Calculates safe position size.
        Simple version: uses fixed percentage of budget (e.g., 99% to leave room for fees).
        Advanced version: could use Kelly Criterion or volatility-based sizing.
        """
        if self.is_trading_halted:
            logging.warning("RiskManager: Trading is halted due to max daily loss.")
            return 0

        # Simple fixed allocation for now (can be enhanced to use ATR)
        safe_budget = total_budget * 0.99
        amount = safe_budget / current_price
        return amount

    def update_daily_loss(self, profit_loss_krw):
        """
        Updates daily loss tracker and halts trading if limit exceeded.
        """
        if profit_loss_krw < 0:
            self.daily_loss += abs(profit_loss_krw)
        
        # Check if max daily loss is exceeded
        max_loss_krw = self.initial_budget * self.max_daily_loss_pct
        if self.daily_loss >= max_loss_krw:
            self.is_trading_halted = True
            logging.critical(f"RiskManager: MAX DAILY LOSS EXCEEDED ({self.daily_loss} KRW). Trading Halted.")
            return True
        return False

    def reset_daily_stats(self):
        """Resets daily stats (called at market reset time)."""
        self.daily_loss = 0.0
        self.is_trading_halted = False
        logging.info("RiskManager: Daily stats reset.")
