import os
import logging
from datetime import datetime

class PerformanceLogger:
    """Class to log trading performance to a CSV file."""
    def __init__(self, filename='trade_log.csv'):
        self.filename = filename
        self.log_file_exists = os.path.exists(filename)
        self._initialize_file()

    def _initialize_file(self):
        """Creates the file with header if it doesn't exist."""
        if not self.log_file_exists:
            with open(self.filename, 'w', encoding='utf-8') as f:
                f.write("entry_time,exit_time,symbol,entry_price,exit_price,amount,profit_krw,profit_percent\n")
            logging.info(f"File '{self.filename}' created.")

    def log_trade(self, trade_details):
        """Logs completed trade details to the file."""
        try:
            with open(self.filename, 'a', encoding='utf-8') as f:
                f.write(
                    f"{trade_details['entry_time']},{trade_details['exit_time']},"
                    f"{trade_details['symbol']},{trade_details['entry_price']},"
                    f"{trade_details['exit_price']},{trade_details['amount']},"
                    f"{trade_details['profit_krw']},{trade_details['profit_percent']}\n"
                )
            logging.info(f"Trade logged: {trade_details['symbol']}")
        except Exception as e:
            logging.error(f"Error logging trade: {e}")
