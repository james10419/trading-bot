import logging
import requests
import os
from datetime import datetime

class MarketIntelligence:
    """
    Fetches market sentiment data to inform trading decisions.
    Sources:
    1. Crypto Fear & Greed Index (alternative.me) - Free, reliable sentiment gauge.
    2. Seeking Alpha (RapidAPI/Apify) - Structural placeholders for news/sentiment.
    """
    def __init__(self):
        self.fng_url = "https://api.alternative.me/fng/?limit=1"
        self.sa_api_key = os.getenv("RAPIDAPI_KEY") # Placeholder for Seeking Alpha via RapidAPI
        
    def get_fear_and_greed_index(self):
        """
        Fetches the latest Crypto Fear & Greed Index.
        Returns:
            dict: {'value': int, 'classification': str} or None
        """
        try:
            response = requests.get(self.fng_url, timeout=5)
            response.raise_for_status()
            data = response.json()
            
            if data['data']:
                item = data['data'][0]
                value = int(item['value'])
                classification = item['value_classification']
                logging.info(f"Market Intelligence: Fear & Greed Index = {value} ({classification})")
                return {'value': value, 'classification': classification}
                
        except Exception as e:
            logging.error(f"Failed to fetch Fear & Greed Index: {e}")
            
        return None

    def get_seeking_alpha_sentiment(self, symbol):
        """
        Placeholder for fetching Seeking Alpha sentiment/news.
        Requires a valid API key (e.g., RapidAPI unofficial API).
        """
        if not self.sa_api_key:
            logging.debug("Seeking Alpha API Key not set. Skipping SA sentiment check.")
            return None

        # Example implementation for RapidAPI (Seeking Alpha Unofficial)
        # url = "https://seeking-alpha.p.rapidapi.com/analysis/v2/list"
        # querystring = {"id": symbol.split('/')[0].lower(), "size": "5", "number": "1"}
        # headers = {
        # 	"X-RapidAPI-Key": self.sa_api_key,
        # 	"X-RapidAPI-Host": "seeking-alpha.p.rapidapi.com"
        # }
        # ... request logic ...
        
        logging.info(f"Seeking Alpha sentiment check for {symbol} not fully implemented (requires API key).")
        return None

    def adjust_risk_parameters(self, base_risk_config, fng_data):
        """
        Adjusts risk parameters based on market sentiment.
        
        Logic:
        - Extreme Fear (<25): High risk. Reduce position size, tighten stop loss.
        - Fear (26-46): Moderate risk. Standard parameters.
        - Neutral (47-54): Standard parameters.
        - Greed (55-75): Bullish. Standard parameters.
        - Extreme Greed (>75): High risk of correction. Tighten trailing stops (if implemented) or reduce size.
        """
        if not fng_data:
            return base_risk_config

        adjusted_config = base_risk_config.copy()
        score = fng_data['value']
        classification = fng_data['classification']

        if score < 25: # Extreme Fear
            logging.warning(f"Market is in {classification}! Reducing risk exposure.")
            adjusted_config['position_size_multiplier'] = 0.5 # Buy only half usual amount
            adjusted_config['stop_loss_pct'] = 0.015 # Tighten SL to 1.5%

        elif score > 75: # Extreme Greed
            logging.warning(f"Market is in {classification}! Exercise caution for corrections.")
            adjusted_config['position_size_multiplier'] = 0.8 
        
        else:
            adjusted_config['position_size_multiplier'] = 1.0

        return adjusted_config
