import aiohttp
import asyncio
import logging
import numpy as np
from datetime import datetime, timedelta
import time

from config import BYBIT_API_BASE

logger = logging.getLogger(__name__)


class BybitService:
    def __init__(self):
        self.base_url = BYBIT_API_BASE
        self.session = None

    async def get_session(self):
        if self.session is None:
            self.session = aiohttp.ClientSession()
        return self.session

    async def close_session(self):
        if self.session:
            await self.session.close()
            self.session = None

    async def make_request(self, endpoint: str, params: dict = None):
        try:
            session = await self.get_session()
            url = f"{self.base_url}{endpoint}"

            async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=15)) as response:
                if response.status == 200:
                    data = await response.json()
                    return data
                else:
                    logger.error(f"API error {response.status}")
                    return None

        except asyncio.TimeoutError:
            logger.error(f"Timeout")
            return None
        except Exception as e:
            logger.error(f"Request error: {e}")
            return None

    async def search_cryptocurrencies(self, query: str):
        try:
            data = await self.make_request("/v5/market/tickers", {"category": "spot"})

            if not data or 'result' not in data or 'list' not in data['result']:
                return []

            all_symbols = data['result']['list']
            query = query.upper()

            results = []
            for symbol_data in all_symbols:
                symbol = symbol_data.get('symbol', '')
                if query in symbol and symbol.endswith('USDT'):
                    results.append({
                        'symbol': symbol,
                        'last_price': float(symbol_data.get('lastPrice', 0)),
                        'change_24h': float(symbol_data.get('price24hPcnt', 0)) * 100,
                        'high_24h': float(symbol_data.get('highPrice24h', 0)),
                        'low_24h': float(symbol_data.get('lowPrice24h', 0)),
                        'volume_24h': float(symbol_data.get('volume24h', 0)),
                        'turnover_24h': float(symbol_data.get('turnover24h', 0))
                    })

                    if len(results) >= 20:
                        break

            return results

        except Exception as e:
            logger.error(f"Search error: {e}")
            return []

    async def get_current_price(self, symbol: str):
        try:
            data = await self.make_request("/v5/market/tickers", {
                "category": "spot",
                "symbol": symbol
            })

            if not data or 'result' not in data or 'list' not in data['result']:
                return None

            ticker_data = data['result']['list'][0] if data['result']['list'] else None

            if not ticker_data:
                return None

            return {
                'symbol': symbol,
                'last_price': float(ticker_data.get('lastPrice', 0)),
                'change_24h': float(ticker_data.get('price24hPcnt', 0)) * 100,
                'high_24h': float(ticker_data.get('highPrice24h', 0)),
                'low_24h': float(ticker_data.get('lowPrice24h', 0)),
                'volume_24h': float(ticker_data.get('volume24h', 0)),
                'turnover_24h': float(ticker_data.get('turnover24h', 0))
            }

        except Exception as e:
            logger.error(f"Price error: {e}")
            return None

    async def get_kline_data(self, symbol: str, interval: str = "60", limit: int = 200):
        try:
            data = await self.make_request("/v5/market/kline", {
                "category": "spot",
                "symbol": symbol,
                "interval": interval,
                "limit": limit
            })

            if not data or 'result' not in data or 'list' not in data['result']:
                return None

            return data['result']['list']

        except Exception as e:
            logger.error(f"Kline error: {e}")
            return None

    async def get_price_history(self, symbol: str, days: int = 90):
        try:
            limit = min(days * 2, 1000)

            klines = await self.get_kline_data(symbol, "D", limit)

            if not klines:
                return None

            prices = []
            timestamps = []

            for kline in reversed(klines):
                try:
                    timestamp = int(kline[0])
                    close_price = float(kline[4])

                    prices.append(close_price)
                    timestamps.append(timestamp)

                except (IndexError, ValueError) as e:
                    continue

            return {
                'prices': prices,
                'timestamps': timestamps
            }

        except Exception as e:
            logger.error(f"History error: {e}")
            return None

    async def calculate_technical_indicators(self, prices: list):
        try:
            if len(prices) < 2:
                return {
                    'sma_20': prices[-1] if prices else 0,
                    'ema_12': prices[-1] if prices else 0,
                    'rsi': 50,
                    'macd': 0,
                    'signal': 0,
                    'histogram': 0
                }

            prices_array = np.array(prices, dtype=float)

            sma_20 = np.mean(prices_array[-20:]) if len(prices_array) >= 20 else np.mean(prices_array)
            ema_12 = self.calculate_ema(prices_array, 12)
            rsi = self.calculate_rsi(prices_array)
            macd, signal, histogram = self.calculate_macd(prices_array)

            return {
                'sma_20': float(sma_20),
                'ema_12': float(ema_12),
                'rsi': float(rsi),
                'macd': float(macd),
                'signal': float(signal),
                'histogram': float(histogram)
            }

        except Exception as e:
            logger.error(f"Indicators error: {e}")
            return {
                'sma_20': prices[-1] if prices else 0,
                'ema_12': prices[-1] if prices else 0,
                'rsi': 50,
                'macd': 0,
                'signal': 0,
                'histogram': 0
            }

    def calculate_ema(self, prices: np.ndarray, period: int) -> float:
        if len(prices) < period:
            return float(prices[-1]) if len(prices) > 0 else 0

        weights = np.exp(np.linspace(-1, 0, period))
        weights /= weights.sum()

        return float(np.convolve(prices, weights, mode='valid')[-1])

    def calculate_rsi(self, prices: np.ndarray, period: int = 14) -> float:
        if len(prices) < period + 1:
            return 50.0

        deltas = np.diff(prices)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)

        avg_gain = np.mean(gains[-period:])
        avg_loss = np.mean(losses[-period:])

        if avg_loss == 0:
            return 100.0 if avg_gain > 0 else 50.0

        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))

        return float(rsi)

    def calculate_macd(self, prices: np.ndarray) -> tuple:
        if len(prices) < 26:
            return 0, 0, 0

        ema_12 = self.calculate_ema(prices, 12)
        ema_26 = self.calculate_ema(prices, 26)

        macd_line = ema_12 - ema_26

        macd_values = []
        for i in range(min(9, len(prices))):
            start_idx = max(0, len(prices) - 26 - i)
            end_idx = len(prices) - i
            if end_idx - start_idx >= 26:
                window_prices = prices[start_idx:end_idx]
                window_ema_12 = self.calculate_ema(window_prices, 12)
                window_ema_26 = self.calculate_ema(window_prices, 26)
                macd_values.append(window_ema_12 - window_ema_26)

        if macd_values:
            signal_line = np.mean(macd_values)
        else:
            signal_line = macd_line

        histogram = macd_line - signal_line

        return macd_line, signal_line, histogram


bybit_service = BybitService()