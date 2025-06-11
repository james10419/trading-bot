# ==============================================================================
#  파일: trading_framework.py
#  설명: 다중 전략, 성과 로깅, 텔레그램 알림 기능을 포함한 모듈식 자동매매 프레임워크
#  기반 아티팩트: trading_bot_volatility_breakout_py
#  주요 개선사항:
#    - 전략 추상화: 새로운 거래 전략을 쉽게 추가할 수 있는 구조.
#    - 성과 로깅: 모든 거래 내역을 CSV 파일로 기록하여 분석 용이성 증대.
#    - 실시간 알림: 텔레그램을 통해 매매 체결 및 주요 오류 발생 시 알림 수신.
# ==============================================================================

# ------------------------------------------------------------------------------
#  1. 환경 설정 가이드
# ------------------------------------------------------------------------------
#
# (1) 아래 내용을 `requirements.txt` 파일로 저장하고, 터미널에서 `pip install -r requirements.txt` 명령어를 실행하세요.
#
# requirements.txt:
# -----------------
# ccxt
# pandas
# python-dotenv
# requests
# pandas-ta
#
# (2) 아래 내용을 `.env` 파일로 프로젝트 루트에 저장하고, 자신의 정보를 입력하세요.
#     텔레그램 봇 토큰과 채팅 ID는 봇 생성 후 @BotFather 와 @userinfobot 을 통해 얻을 수 있습니다.
#
# .env:
# -----
# UPBIT_ACCESS_KEY="YOUR_UPBIT_ACCESS_KEY"
# UPBIT_SECRET_KEY="YOUR_UPBIT_SECRET_KEY"
#
# # 텔레그램 알림을 사용하려면 아래 두 줄의 주석을 해제하고 값을 입력하세요.
# # TELEGRAM_BOT_TOKEN="YOUR_TELEGRAM_BOT_TOKEN"
# # TELEGRAM_CHAT_ID="YOUR_TELEGRAM_CHAT_ID"
#
# ------------------------------------------------------------------------------

import ccxt.async_support as ccxt
import asyncio
import os
import logging
from datetime import datetime
import pandas as pd
import pandas_ta as ta
import requests
from dotenv import load_dotenv
from abc import ABC, abstractmethod

# .env 파일에서 환경 변수 로드
load_dotenv()

# --- 로깅 설정 ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("trading_framework.log"),
        logging.StreamHandler()
    ]
)

# --- 기본 설정 ---
EXCHANGE_NAME = 'upbit'
TARGET_SYMBOL = 'BTC/KRW'
TRADE_BUDGET_KRW = 5000         # 1회 거래 예산 (거래소 최소 주문 금액 이상)
MARKET_RESET_HOUR = 9           # 시장 리셋 시간 (Upbit 기준 오전 9시)
SELECTED_STRATEGY = 'VolatilityBreakout' # 사용할 전략 선택: 'VolatilityBreakout' 또는 'RSI'

# ==============================================================================
#  2. 모듈 구현 (알림, 성과 로깅, 전략)
# ==============================================================================

class NotificationManager:
    """텔레그램 알림을 관리하는 클래스."""
    def __init__(self):
        self.token = os.getenv("TELEGRAM_BOT_TOKEN")
        self.chat_id = os.getenv("TELEGRAM_CHAT_ID")
        if self.token and self.chat_id:
            logging.info("텔레그램 알림 기능이 활성화되었습니다.")
        else:
            logging.warning("텔레그램 토큰 또는 채팅 ID가 설정되지 않아 알림 기능이 비활성화됩니다.")

    def send_message(self, message):
        """텔레그램으로 메시지를 보냅니다."""
        if not self.token or not self.chat_id:
            return

        url = f"https://api.telegram.org/bot{self.token}/sendMessage"
        params = {'chat_id': self.chat_id, 'text': message}
        try:
            response = requests.get(url, params=params, timeout=5)
            response.raise_for_status()
            logging.info("텔레그램 메시지 발송 성공.")
        except requests.exceptions.RequestException as e:
            logging.error(f"텔레그램 메시지 발송 실패: {e}")

class PerformanceLogger:
    """거래 성과를 CSV 파일로 기록하는 클래스."""
    def __init__(self, filename='trade_log.csv'):
        self.filename = filename
        self.log_file_exists = os.path.exists(filename)
        self._initialize_file()

    def _initialize_file(self):
        """로그 파일이 없으면 헤더를 포함하여 새로 생성합니다."""
        if not self.log_file_exists:
            with open(self.filename, 'w', encoding='utf-8') as f:
                f.write("entry_time,exit_time,symbol,entry_price,exit_price,amount,profit_krw,profit_percent\n")
            logging.info(f"'{self.filename}' 파일이 생성되었습니다.")

    def log_trade(self, trade_details):
        """완료된 거래 내역을 파일에 기록합니다."""
        try:
            with open(self.filename, 'a', encoding='utf-8') as f:
                f.write(
                    f"{trade_details['entry_time']},{trade_details['exit_time']},"
                    f"{trade_details['symbol']},{trade_details['entry_price']},"
                    f"{trade_details['exit_price']},{trade_details['amount']},"
                    f"{trade_details['profit_krw']},{trade_details['profit_percent']}\n"
                )
            logging.info(f"거래 내역 기록 완료: {trade_details['symbol']}")
        except Exception as e:
            logging.error(f"거래 내역 기록 중 오류 발생: {e}")

# --- 전략 패턴 구현 ---
class BaseStrategy(ABC):
    """모든 거래 전략의 기반이 되는 추상 클래스."""
    def __init__(self, exchange, symbol, params):
        self.exchange = exchange
        self.symbol = symbol
        self.params = params
        logging.info(f"전략 초기화: {self.__class__.__name__} with params: {params}")

    @abstractmethod
    async def get_signal(self):
        """매수/매도 신호를 반환합니다. ('BUY', 'SELL', 'HOLD')"""
        pass

class VolatilityBreakoutStrategy(BaseStrategy):
    """변동성 돌파 전략 클래스."""
    def __init__(self, exchange, symbol, params={'k_value': 0.5}):
        super().__init__(exchange, symbol, params)
        self.target_price = None
        self.bought = False

    async def prepare_data(self):
        """매일 아침 목표가를 계산합니다."""
        try:
            ohlcv = await self.exchange.fetch_ohlcv(self.symbol, '1d', limit=2)
            if len(ohlcv) < 2:
                logging.warning("목표가 계산을 위한 충분한 데이터가 없습니다.")
                self.target_price = None
                return

            yesterday = ohlcv[-2]
            _, _, high, low, _, _ = yesterday
            today_open = ohlcv[-1][1]

            volatility = high - low
            self.target_price = today_open + (volatility * self.params.get('k_value', 0.5))
            logging.info(f"새로운 목표가 계산 완료: {self.target_price:,.2f} KRW")
        except Exception as e:
            logging.error(f"목표가 계산 중 오류 발생: {e}")
            self.target_price = None

    async def get_signal(self):
        if self.bought or self.target_price is None:
            return 'HOLD'

        try:
            ticker = await self.exchange.fetch_ticker(self.symbol)
            current_price = ticker['last']

            if current_price > self.target_price:
                logging.info(f"*** 매수 신호 (변동성 돌파): 현재가({current_price:,.2f}) > 목표가({self.target_price:,.2f}) ***")
                self.bought = True # 신호 발생 후 다시 발생하지 않도록 플래그 설정
                return 'BUY'
        except Exception as e:
            logging.error(f"변동성 돌파 전략 신호 확인 중 오류: {e}")

        return 'HOLD'

    def reset(self):
        """하루가 지나면 상태를 리셋합니다."""
        self.bought = False
        self.target_price = None
        logging.info("변동성 돌파 전략 상태가 리셋되었습니다.")

class RSIStrategy(BaseStrategy):
    """RSI 지표 기반 매매 전략 클래스."""
    def __init__(self, exchange, symbol, params={'rsi_period': 14, 'oversold': 30, 'overbought': 70}):
        super().__init__(exchange, symbol, params)
        self.timeframe = '1h' # RSI 계산을 위한 시간봉

    async def get_signal(self):
        try:
            ohlcv = await self.exchange.fetch_ohlcv(self.symbol, timeframe=self.timeframe, limit=100)
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            
            rsi_period = self.params.get('rsi_period', 14)
            rsi = df.ta.rsi(length=rsi_period)
            
            if rsi is None or rsi.empty:
                logging.warning("RSI 계산 실패. 데이터가 부족할 수 있습니다.")
                return 'HOLD'
            
            last_rsi = rsi.iloc[-1]
            oversold_threshold = self.params.get('oversold', 30)
            overbought_threshold = self.params.get('overbought', 70)

            logging.info(f"현재 {self.symbol}의 RSI({rsi_period}): {last_rsi:.2f}")

            if last_rsi < oversold_threshold:
                logging.info(f"*** 매수 신호 (RSI 과매도): {last_rsi:.2f} < {oversold_threshold} ***")
                return 'BUY'
            elif last_rsi > overbought_threshold:
                logging.info(f"*** 매도 신호 (RSI 과매수): {last_rsi:.2f} > {overbought_threshold} ***")
                return 'SELL'

        except Exception as e:
            logging.error(f"RSI 전략 신호 확인 중 오류: {e}")

        return 'HOLD'

# ==============================================================================
#  3. 메인 트레이딩 봇 클래스
# ==============================================================================

class TradingBot:
    """
    전략, 알림, 로깅 모듈을 사용하여 자동매매를 실행하는 메인 클래스.
    """
    def __init__(self, exchange_name, symbol, budget, strategy_name):
        self.symbol = symbol
        self.budget = budget
        self.position = {} # {'entry_price': float, 'amount': float, 'timestamp': datetime}
        self.exchange = self._create_exchange_instance(exchange_name)
        
        self.notifier = NotificationManager()
        self.perf_logger = PerformanceLogger()
        self.strategy = self._create_strategy_instance(strategy_name)

    def _create_exchange_instance(self, exchange_name):
        """거래소 인스턴스를 생성하고 인증합니다."""
        api_key = os.getenv(f'{exchange_name.upper()}_ACCESS_KEY')
        secret_key = os.getenv(f'{exchange_name.upper()}_SECRET_KEY')
        if not api_key or not secret_key:
            raise ValueError("API 키가 .env 파일에 설정되지 않았습니다.")
        
        exchange_class = getattr(ccxt, exchange_name)
        return exchange_class({'apiKey': api_key, 'secret': secret_key})

    def _create_strategy_instance(self, strategy_name):
        """선택된 이름에 따라 전략 인스턴스를 생성합니다."""
        if strategy_name == 'VolatilityBreakout':
            return VolatilityBreakoutStrategy(self.exchange, self.symbol)
        elif strategy_name == 'RSI':
            return RSIStrategy(self.exchange, self.symbol)
        else:
            raise ValueError(f"지원하지 않는 전략입니다: {strategy_name}")

    async def initialize(self):
        """거래소 마켓 정보를 로드합니다."""
        try:
            await self.exchange.load_markets()
            logging.info(f"{self.exchange.id} 마켓 정보 로드 완료.")
            self.notifier.send_message(f"✅ 자동매매 봇 시작\n- 전략: {SELECTED_STRATEGY}\n- 종목: {self.symbol}")
            return True
        except Exception as e:
            logging.error(f"마켓 정보 로드 실패: {e}")
            self.notifier.send_message(f"❌ 자동매매 봇 시작 실패: {e}")
            await self.close()
            return False

    async def sell_position(self, reason=""):
        """보유 중인 포지션을 시장가로 매도하고 성과를 기록합니다."""
        if not self.position:
            logging.info("매도할 포지션이 없습니다.")
            return

        try:
            amount_to_sell = self.position.get('amount')
            if not amount_to_sell:
                logging.warning("매도할 수량을 알 수 없어 매도를 건너뜁니다.")
                return

            logging.info(f"{self.symbol} 전량 매도를 시도합니다. 사유: {reason}")
            order = await self.exchange.create_market_sell_order(self.symbol, amount_to_sell)
            
            exit_price = order.get('average') or order.get('price')
            if not exit_price:
                 ticker = await self.exchange.fetch_ticker(self.symbol)
                 exit_price = ticker['last']
                 
            profit_krw = (exit_price - self.position['entry_price']) * amount_to_sell
            profit_percent = (profit_krw / self.budget) * 100
            
            trade_details = {
                'entry_time': self.position['timestamp'],
                'exit_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'symbol': self.symbol,
                'entry_price': self.position['entry_price'],
                'exit_price': exit_price,
                'amount': amount_to_sell,
                'profit_krw': round(profit_krw, 2),
                'profit_percent': round(profit_percent, 2)
            }
            self.perf_logger.log_trade(trade_details)

            msg = (f"💰 매도 체결 ({reason})\n"
                   f"- 종목: {self.symbol}\n"
                   f"- 수익: {profit_krw:,.2f} KRW ({profit_percent:.2f}%)")
            self.notifier.send_message(msg)

            self.position = {}

        except Exception as e:
            logging.error(f"매도 주문 중 오류 발생: {e}")
            self.notifier.send_message(f"❌ 매도 주문 실패: {e}")


    async def buy_position(self):
        """설정된 예산만큼 시장가로 매수합니다."""
        if self.position:
            logging.info("이미 포지션을 보유 중이므로 추가 매수하지 않습니다.")
            return

        try:
            logging.info(f"{self.symbol} 매수를 시도합니다. 예산: {self.budget:,.2f} KRW")
            
            ticker = await self.exchange.fetch_ticker(self.symbol)
            current_price = ticker['last']
            amount = (self.budget * 0.9995) / current_price

            order = await self.exchange.create_market_buy_order(self.symbol, amount)
            
            entry_price = order.get('average') or order.get('price')
            if not entry_price:
                 entry_price = current_price
            
            self.position = {
                'entry_price': entry_price,
                'amount': order.get('filled', amount),
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }

            msg = (f"🛒 매수 체결\n"
                   f"- 종목: {self.symbol}\n"
                   f"- 가격: {entry_price:,.2f} KRW\n"
                   f"- 수량: {self.position['amount']:.6f}")
            self.notifier.send_message(msg)

        except Exception as e:
            logging.error(f"매수 주문 중 오류 발생: {e}")
            self.notifier.send_message(f"❌ 매수 주문 실패: {e}")

    async def run(self):
        """봇의 메인 루프를 실행합니다."""
        
        if isinstance(self.strategy, VolatilityBreakoutStrategy):
            await self.strategy.prepare_data()

        while True:
            now = datetime.now()
            
            if now.hour == MARKET_RESET_HOUR and now.minute == 0 and now.second < 10:
                logging.info(f"시장 리셋 시간입니다. ({now.strftime('%Y-%m-%d %H:%M:%S')})")
                
                await self.sell_position(reason="정기 매도")
                
                if hasattr(self.strategy, 'reset'):
                    self.strategy.reset()
                if hasattr(self.strategy, 'prepare_data'):
                    await self.strategy.prepare_data()
                
                logging.info("="*30)
                await asyncio.sleep(60)
                continue

            try:
                signal = await self.strategy.get_signal()
                
                if signal == 'BUY' and not self.position:
                    await self.buy_position()
                elif signal == 'SELL' and self.position:
                    await self.sell_position(reason="전략 매도 신호")
                    
            except Exception as e:
                logging.error(f"메인 루프 중 오류 발생: {e}")
                self.notifier.send_message(f"🚨 봇 메인 루프 오류: {e}")

            sleep_duration = 5 if isinstance(self.strategy, RSIStrategy) else 2
            await asyncio.sleep(sleep_duration)

    async def close(self):
        """봇 종료 시 거래소 세션을 닫습니다."""
        if self.exchange:
            await self.exchange.close()
            logging.info("거래소 연결이 종료되었습니다.")
            self.notifier.send_message("💤 자동매매 봇이 종료되었습니다.")

# ==============================================================================
#  4. 실행
# ==============================================================================
async def main():
    bot = TradingBot(
        exchange_name=EXCHANGE_NAME,
        symbol=TARGET_SYMBOL,
        budget=TRADE_BUDGET_KRW,
        strategy_name=SELECTED_STRATEGY
    )

    if not await bot.initialize():
        return

    try:
        await bot.run()
    except KeyboardInterrupt:
        logging.info("사용자에 의해 프로그램이 중단되었습니다.")
    finally:
        await bot.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        logging.critical(f"메인 실행 중 심각한 오류 발생: {e}")
