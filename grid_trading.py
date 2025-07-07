import os
import ccxt
import time
from dotenv import load_dotenv
from loguru import logger

class GridTrading:
    def __init__(self, exchange_id='binance', symbol='BTC/USDT'):
        # 加载环境变量
        load_dotenv()
        
        # 初始化交易所
        self.exchange = getattr(ccxt, exchange_id)({
            'apiKey': os.getenv('API_KEY'),
            'secret': os.getenv('API_SECRET'),
            'enableRateLimit': True
        })
        
        self.symbol = symbol
        self.grid_levels = []
        self.orders = {}
        
        # 设置日志
        logger.add("grid_trading.log")
    
    def setup_grid(self, upper_price, lower_price, grid_num, total_investment):
        """设置网格参数"""
        self.upper_price = float(upper_price)
        self.lower_price = float(lower_price)
        self.grid_num = int(grid_num)
        self.total_investment = float(total_investment)
        
        # 计算网格价格间隔
        self.grid_interval = (self.upper_price - self.lower_price) / self.grid_num
        
        # 生成网格价格水平
        self.grid_levels = [self.lower_price + i * self.grid_interval for i in range(self.grid_num + 1)]
        
        # 计算每个网格的投资额
        self.per_grid_investment = self.total_investment / self.grid_num
        
        logger.info(f"网格设置完成：\n价格区间：{self.lower_price}-{self.upper_price}\n网格数量：{self.grid_num}\n每格投资额：{self.per_grid_investment}")
    
    def get_current_price(self):
        """获取当前市场价格"""
        ticker = self.exchange.fetch_ticker(self.symbol)
        return float(ticker['last'])
    
    def place_grid_orders(self):
        """放置网格订单"""
        current_price = self.get_current_price()
        
        for i, price in enumerate(self.grid_levels):
            if price < current_price:  # 当前价格以下放买单
                try:
                    order = self.exchange.create_limit_buy_order(
                        self.symbol,
                        self.per_grid_investment / price,
                        price
                    )
                    self.orders[order['id']] = {
                        'price': price,
                        'side': 'buy',
                        'status': 'open'
                    }
                    logger.info(f"在价格 {price} 放置买单")
                except Exception as e:
                    logger.error(f"下单错误：{str(e)}")
            
            elif price > current_price:  # 当前价格以上放卖单
                try:
                    order = self.exchange.create_limit_sell_order(
                        self.symbol,
                        self.per_grid_investment / price,
                        price
                    )
                    self.orders[order['id']] = {
                        'price': price,
                        'side': 'sell',
                        'status': 'open'
                    }
                    logger.info(f"在价格 {price} 放置卖单")
                except Exception as e:
                    logger.error(f"下单错误：{str(e)}")
    
    def monitor_and_update(self):
        """监控订单状态并更新"""
        while True:
            try:
                # 获取所有未完成订单
                open_orders = self.exchange.fetch_open_orders(self.symbol)
                filled_orders = [order_id for order_id in self.orders 
                               if order_id not in [o['id'] for o in open_orders]]
                
                # 处理已成交订单
                for order_id in filled_orders:
                    order_info = self.orders[order_id]
                    logger.info(f"订单成交：{order_info['side']} @ {order_info['price']}")
                    
                    # 根据成交方向放置对应的反向订单
                    if order_info['side'] == 'buy':
                        try:
                            new_order = self.exchange.create_limit_sell_order(
                                self.symbol,
                                self.per_grid_investment / order_info['price'],
                                order_info['price'] + self.grid_interval
                            )
                            self.orders[new_order['id']] = {
                                'price': order_info['price'] + self.grid_interval,
                                'side': 'sell',
                                'status': 'open'
                            }
                        except Exception as e:
                            logger.error(f"下单错误：{str(e)}")
                    else:
                        try:
                            new_order = self.exchange.create_limit_buy_order(
                                self.symbol,
                                self.per_grid_investment / order_info['price'],
                                order_info['price'] - self.grid_interval
                            )
                            self.orders[new_order['id']] = {
                                'price': order_info['price'] - self.grid_interval,
                                'side': 'buy',
                                'status': 'open'
                            }
                        except Exception as e:
                            logger.error(f"下单错误：{str(e)}")
                    
                    # 删除已成交订单的记录
                    del self.orders[order_id]
                
                time.sleep(5)  # 每5秒检查一次
                
            except Exception as e:
                logger.error(f"监控更新错误：{str(e)}")
                time.sleep(5)
    
    def start(self, upper_price, lower_price, grid_num, total_investment):
        """启动网格交易"""
        try:
            # 设置网格参数
            self.setup_grid(upper_price, lower_price, grid_num, total_investment)
            
            # 放置初始订单
            self.place_grid_orders()
            
            # 开始监控和更新订单
            self.monitor_and_update()
            
        except Exception as e:
            logger.error(f"启动错误：{str(e)}")

if __name__ == '__main__':
    # 创建网格交易实例
    grid_trader = GridTrading()
    
    # 设置网格参数
    upper_price = 45000  # 上限价格
    lower_price = 40000  # 下限价格
    grid_num = 10        # 网格数量
    total_investment = 1000  # 总投资额（USDT）
    
    # 启动交易
    grid_trader.start(upper_price, lower_price, grid_num, total_investment)