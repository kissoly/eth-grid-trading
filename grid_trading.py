import ccxt
from loguru import logger
import time

class GridTrading:
    def __init__(self, symbol, api_key, api_secret, quantity):
        self.symbol = symbol
        self.exchange = ccxt.binance({
            'apiKey': api_key,
            'secret': api_secret,
            'enableRateLimit': True
        })
        self.quantity = quantity
        self.last_price = None
        self.grid_orders = []

    def get_current_price(self):
        """获取当前价格"""
        try:
            ticker = self.exchange.fetch_ticker(self.symbol)
            return ticker['last']
        except Exception as e:
            logger.error(f"获取{self.symbol}价格失败：{str(e)}")
            raise

    def place_grid_orders(self):
        """放置网格订单"""
        try:
            current_price = self.get_current_price()
            if not self.last_price:
                self.last_price = current_price
                return

            price_change = ((current_price - self.last_price) / self.last_price) * 100

            # 价格下跌超过阈值，开多单
            if price_change <= -self.price_drop:
                order = self.exchange.create_market_buy_order(
                    self.symbol,
                    self.quantity
                )
                logger.info(f"价格下跌{abs(price_change):.2f}%，开多单：{order}")
                self.grid_orders.append({
                    'type': 'long',
                    'price': current_price,
                    'quantity': self.quantity,
                    'order': order
                })
                self.last_price = current_price

            # 价格上涨超过阈值，开空单
            elif price_change >= self.price_rise:
                order = self.exchange.create_market_sell_order(
                    self.symbol,
                    self.quantity
                )
                logger.info(f"价格上涨{price_change:.2f}%，开空单：{order}")
                self.grid_orders.append({
                    'type': 'short',
                    'price': current_price,
                    'quantity': self.quantity,
                    'order': order
                })
                self.last_price = current_price

        except Exception as e:
            logger.error(f"放置网格订单失败：{str(e)}")
            raise

    def check_and_close_positions(self):
        """检查并平仓获利订单"""
        try:
            current_price = self.get_current_price()
            orders_to_remove = []

            for i, order in enumerate(self.grid_orders):
                entry_price = order['price']
                profit = 0

                if order['type'] == 'long':
                    profit = ((current_price - entry_price) / entry_price) * 100
                    if profit >= self.long_profit:
                        close_order = self.exchange.create_market_sell_order(
                            self.symbol,
                            order['quantity']
                        )
                        logger.info(f"多单获利{profit:.2f}%，平仓：{close_order}")
                        orders_to_remove.append(i)

                elif order['type'] == 'short':
                    profit = ((entry_price - current_price) / entry_price) * 100
                    if profit >= self.short_profit:
                        close_order = self.exchange.create_market_buy_order(
                            self.symbol,
                            order['quantity']
                        )
                        logger.info(f"空单获利{profit:.2f}%，平仓：{close_order}")
                        orders_to_remove.append(i)

            # 从后往前移除已平仓的订单
            for i in sorted(orders_to_remove, reverse=True):
                self.grid_orders.pop(i)

        except Exception as e:
            logger.error(f"检查和平仓订单失败：{str(e)}")
            raise

    def run(self):
        """运行网格交易"""
        try:
            self.place_grid_orders()
            self.check_and_close_positions()
        except Exception as e:
            logger.error(f"网格交易运行失败：{str(e)}")
            raise