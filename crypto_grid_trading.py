import os
import ccxt
import time
from datetime import datetime
from loguru import logger
from grid_trading import GridTrading

def setup_logger(symbol):
    """为每个交易对设置独立的日志文件"""
    symbol_name = symbol.replace('/', '_')
    log_file = f"grid_trading_{symbol_name}.log"
    logger.add(log_file, rotation="500 MB")
    return logger

class CryptoGridTrading(GridTrading):
    def __init__(self, symbol='ETH/USDT', trade_amount=0.1):
        super().__init__(exchange_id='binance', symbol=symbol)
        self.trade_amount = trade_amount
        self.logger = setup_logger(symbol)
        self.set_thresholds()

    def set_thresholds(self, long_threshold=0.02, short_threshold=0.02,
                      long_profit_threshold=0.015, short_profit_threshold=0.015):
        """设置交易阈值参数"""
        self.long_threshold = long_threshold  # 开多单阈值
        self.short_threshold = short_threshold  # 开空单阈值
        self.long_profit_threshold = long_profit_threshold  # 多单获利平仓阈值
        self.short_profit_threshold = short_profit_threshold  # 空单获利平仓阈值
        
        self.logger.info(f"交易阈值设置：\n开多阈值：{self.long_threshold}\n开空阈值：{self.short_threshold}\n"
                        f"多单平仓阈值：{self.long_profit_threshold}\n空单平仓阈值：{self.short_profit_threshold}")

    def check_balance(self):
        """检查账户余额"""
        try:
            balance = self.exchange.fetch_balance()
            base_currency = self.symbol.split('/')[0]
            quote_currency = self.symbol.split('/')[1]
            
            self.logger.info(f"账户余额：\n{base_currency}: {balance[base_currency]['free']}\n"
                            f"{quote_currency}: {balance[quote_currency]['free']}")
            
            return balance
        except Exception as e:
            self.logger.error(f"获取余额失败：{str(e)}")
            return None

    def get_price(self):
        """获取当前价格"""
        try:
            ticker = self.exchange.fetch_ticker(self.symbol)
            return float(ticker['last'])
        except Exception as e:
            self.logger.error(f"获取价格失败：{str(e)}")
            return None

    def get_klines(self, timeframe='1h', limit=24):
        """获取K线数据"""
        try:
            klines = self.exchange.fetch_ohlcv(self.symbol, timeframe=timeframe, limit=limit)
            return klines
        except Exception as e:
            self.logger.error(f"获取K线数据失败：{str(e)}")
            return None

    def open_long(self, price):
        """开多单"""
        try:
            order = self.exchange.create_market_buy_order(
                self.symbol,
                self.trade_amount
            )
            self.logger.info(f"开多单成功：数量 {self.trade_amount}, 价格 {price}")
            return order
        except Exception as e:
            self.logger.error(f"开多单失败：{str(e)}")
            return None

    def open_short(self, price):
        """开空单"""
        try:
            order = self.exchange.create_market_sell_order(
                self.symbol,
                self.trade_amount
            )
            self.logger.info(f"开空单成功：数量 {self.trade_amount}, 价格 {price}")
            return order
        except Exception as e:
            self.logger.error(f"开空单失败：{str(e)}")
            return None

    def close_long_position(self, price, open_price):
        """平多单"""
        try:
            order = self.exchange.create_market_sell_order(
                self.symbol,
                self.trade_amount
            )
            profit = (price - open_price) * self.trade_amount
            profit_rate = (price - open_price) / open_price
            self.logger.info(f"平多单成功：数量 {self.trade_amount}, 价格 {price}, "
                            f"盈亏 {profit:.4f} USDT ({profit_rate:.2%})")
            return order, profit, profit_rate
        except Exception as e:
            self.logger.error(f"平多单失败：{str(e)}")
            return None, 0, 0

    def close_short_position(self, price, open_price):
        """平空单"""
        try:
            order = self.exchange.create_market_buy_order(
                self.symbol,
                self.trade_amount
            )
            profit = (open_price - price) * self.trade_amount
            profit_rate = (open_price - price) / open_price
            self.logger.info(f"平空单成功：数量 {self.trade_amount}, 价格 {price}, "
                            f"盈亏 {profit:.4f} USDT ({profit_rate:.2%})")
            return order, profit, profit_rate
        except Exception as e:
            self.logger.error(f"平空单失败：{str(e)}")
            return None, 0, 0

    def run(self):
        """运行网格交易策略"""
        self.logger.info(f"开始运行 {self.symbol} 网格交易策略，交易数量：{self.trade_amount}")
        
        long_position = False
        short_position = False
        open_price = 0
        
        while True:
            try:
                current_price = self.get_price()
                if not current_price:
                    time.sleep(5)
                    continue
                
                # 检查是否需要开仓
                if not long_position and not short_position:
                    klines = self.get_klines()
                    if not klines:
                        time.sleep(5)
                        continue
                    
                    # 计算24小时价格变化
                    price_24h_ago = klines[0][4]  # 24小时前的收盘价
                    price_change = (current_price - price_24h_ago) / price_24h_ago
                    
                    if price_change <= -self.long_threshold:
                        if self.open_long(current_price):
                            long_position = True
                            open_price = current_price
                    elif price_change >= self.short_threshold:
                        if self.open_short(current_price):
                            short_position = True
                            open_price = current_price
                
                # 检查是否需要平仓
                elif long_position:
                    profit_rate = (current_price - open_price) / open_price
                    if profit_rate >= self.long_profit_threshold:
                        order, profit, actual_profit_rate = self.close_long_position(current_price, open_price)
                        if order:
                            long_position = False
                            open_price = 0
                
                elif short_position:
                    profit_rate = (open_price - current_price) / open_price
                    if profit_rate >= self.short_profit_threshold:
                        order, profit, actual_profit_rate = self.close_short_position(current_price, open_price)
                        if order:
                            short_position = False
                            open_price = 0
                
                time.sleep(5)
                
            except ccxt.NetworkError as e:
                self.logger.error(f"网络错误：{str(e)}")
                time.sleep(10)
            except ccxt.ExchangeError as e:
                self.logger.error(f"交易所错误：{str(e)}")
                time.sleep(10)
            except Exception as e:
                self.logger.error(f"未知错误：{str(e)}")
                time.sleep(10)

if __name__ == '__main__':
    # 定义交易对及其交易量
    trading_pairs = [
        {'symbol': 'ETH/USDT', 'amount': 0.1, 'thresholds': {
            'long': 0.02, 'short': 0.02,
            'long_profit': 0.015, 'short_profit': 0.015
        }},
        {'symbol': 'BTC/USDT', 'amount': 0.01, 'thresholds': {
            'long': 0.015, 'short': 0.015,
            'long_profit': 0.01, 'short_profit': 0.01
        }}
    ]
    
    # 为每个交易对创建并运行网格交易实例
    for pair in trading_pairs:
        trader = CryptoGridTrading(symbol=pair['symbol'], trade_amount=pair['amount'])
        trader.set_thresholds(
            long_threshold=pair['thresholds']['long'],
            short_threshold=pair['thresholds']['short'],
            long_profit_threshold=pair['thresholds']['long_profit'],
            short_profit_threshold=pair['thresholds']['short_profit']
        )
        trader.run()