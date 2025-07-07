import ccxt
import time
from loguru import logger
from database import Database
import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

def setup_logger(symbol):
    """为每个交易对配置独立的日志"""
    # 将交易对符号中的'/'替换为'_'以用于文件名
    symbol_str = symbol.replace('/', '_')
    logger.add(
        f"{symbol_str}_grid_trading_{{time}}.log",
        rotation="500 MB",
        retention="10 days",
        level="INFO"
    )

class CryptoGridTrading(GridTrading):
    def __init__(self, symbol='ETH/USDT', trade_amount=0.1):
        """初始化交易参数
        Args:
            symbol: 交易对，如'ETH/USDT', 'BTC/USDT'等
            trade_amount: 每次交易数量
        """
        super().__init__(exchange_id='binance', symbol=symbol)
        
        # 设置交易对特定的日志
        setup_logger(symbol)
        
        # 设置交易所特定选项
        self.exchange.options.update({
            'defaultType': 'future',
            'hedgeMode': True
        })
        
        # 设置代理（如果需要）
        self.exchange.proxies = {
            'http': 'socks5://localhost:7897',
            'https': 'socks5://localhost:7897'
        }
        
        # 设置交易参数
        self.trade_amount = trade_amount  # 每次交易数量
        # 设置默认阈值
        self.set_thresholds()
        
    def set_thresholds(self, price_drop=10, price_rise=10, long_profit=50, short_profit=50):
        """设置交易阈值参数
        Args:
            price_drop: 跌多少开多单
            price_rise: 涨多少开空单
            long_profit: 多单获利平仓阈值
            short_profit: 空单获利平仓阈值
        """
        self.price_drop_threshold = price_drop
        self.price_rise_threshold = price_rise
        self.long_profit_threshold = long_profit
        self.short_profit_threshold = short_profit
        
        logger.info(f"{self.symbol}交易阈值设置：")
        logger.info(f"开多单阈值：跌{self.price_drop_threshold}")
        logger.info(f"开空单阈值：涨{self.price_rise_threshold}")
        logger.info(f"多单获利平仓阈值：{self.long_profit_threshold}")
        logger.info(f"空单获利平仓阈值：{self.short_profit_threshold}")
        
        # 初始化数据库连接
        self.db = Database()
        
        # 记录上次检查K线的时间
        self.last_kline_check = 0
        
        # 初始化检查
        self._initialize()
    
    def _initialize(self):
        """初始化检查"""
        try:
            # 测试API连接
            self.exchange.fetch_balance()
            logger.info("API连接成功")
            
            # 检查交易对是否存在
            markets = self.exchange.load_markets()
            if self.symbol not in markets:
                raise Exception(f"交易对 {self.symbol} 不存在")
            logger.info(f"交易对 {self.symbol} 验证成功")
            
        except Exception as e:
            logger.error(f"初始化失败：{str(e)}")
            raise
    
    def check_balance(self):
        """检查账户余额"""
        try:
            balance = self.exchange.fetch_balance()
            usdt_balance = balance['USDT']['free']
            
            logger.info(f"当前余额：")
            logger.info(f"USDT：{usdt_balance}")
            
            min_usdt = self.trade_amount * self.get_current_price()
            if usdt_balance < min_usdt:
                logger.warning(f"USDT余额不足：{usdt_balance} < {min_usdt}")
            
        except Exception as e:
            logger.error(f"检查余额失败：{str(e)}")
    
    def get_current_price(self):
        """获取当前价格"""
        try:
            ticker = self.exchange.fetch_ticker(self.symbol)
            return ticker['last']
        except Exception as e:
            logger.error(f"获取价格失败：{str(e)}")
            return None
    
    def get_hourly_kline(self):
        """获取1小时K线数据"""
        try:
            # 获取最近的1小时K线数据
            klines = self.exchange.fetch_ohlcv(
                self.symbol,
                timeframe='1h',
                limit=1
            )
            
            if klines and len(klines) > 0:
                kline = klines[0]
                return {
                    'timestamp': kline[0],
                    'open': kline[1],
                    'high': kline[2],
                    'low': kline[3],
                    'close': kline[4],
                    'volume': kline[5]
                }
            return None
            
        except Exception as e:
            logger.error(f"获取K线数据失败：{str(e)}")
            return None
    
    def should_check_positions(self):
        """判断是否需要检查持仓"""
        current_time = time.time()
        # 每5分钟检查一次
        if current_time - self.last_kline_check >= 300:  # 5分钟 = 300秒
            self.last_kline_check = current_time
            return True
        return False
    
    def place_long_order(self, price):
        """开多单"""
        try:
            # 创建市价买单
            order = self.exchange.create_market_buy_order(
                self.symbol,
                self.trade_amount,
                params={
                    'type': 'market',
                    'positionSide': 'LONG'
                }
            )
            
            # 记录持仓
            position_id = self.db.record_position(
                symbol=self.symbol,
                position_type='long',
                amount=self.trade_amount,
                price=price,
                order_id=order['id']
            )
            
            logger.info(f"开多单成功：价格={price}, 数量={self.trade_amount}, 订单ID={order['id']}")
            return position_id
            
        except ccxt.InsufficientFunds as e:
            logger.error(f"资金不足：{str(e)}")
        except ccxt.ExchangeError as e:
            logger.error(f"交易所错误：{str(e)}")
        except Exception as e:
            logger.error(f"下多单失败：{str(e)}")
        return None
    
    def place_short_order(self, price):
        """开空单"""
        try:
            # 创建市价卖单
            order = self.exchange.create_market_sell_order(
                self.symbol,
                self.trade_amount,
                params={
                    'type': 'market',
                    'positionSide': 'SHORT'
                }
            )
            
            # 记录持仓
            position_id = self.db.record_position(
                symbol=self.symbol,
                position_type='short',
                amount=self.trade_amount,
                price=price,
                order_id=order['id']
            )
            
            logger.info(f"开空单成功：价格={price}, 数量={self.trade_amount}, 订单ID={order['id']}")
            return position_id
            
        except ccxt.InsufficientFunds as e:
            logger.error(f"资金不足：{str(e)}")
        except ccxt.ExchangeError as e:
            logger.error(f"交易所错误：{str(e)}")
        except Exception as e:
            logger.error(f"下空单失败：{str(e)}")
        return None
    
    def close_long_position(self, position_id, current_price):
        """平多单"""
        try:
            # 获取持仓信息
            positions = self.db.get_open_positions(self.symbol)
            position = next((p for p in positions if p[0] == position_id), None)
            
            if not position:
                logger.error(f"未找到持仓ID：{position_id}")
                return False
            
            # 创建市价卖单
            order = self.exchange.create_market_sell_order(
                self.symbol,
                position[3],  # amount
                params={
                    'type': 'market',
                    'positionSide': 'LONG'
                }
            )
            
            # 计算盈利
            buy_value = position[4] * position[3]  # entry_price * amount
            sell_value = current_price * position[3]
            profit = sell_value - buy_value
            
            # 获取手续费
            fee = order.get('fee', {}).get('cost', 0)
            
            # 更新数据库
            self.db.close_position(
                position_id=position_id,
                close_price=current_price,
                close_order_id=order['id'],
                profit=profit,
                fee=fee
            )
            
            logger.info(f"平多单成功：开仓价={position[4]}, 平仓价={current_price}, ")
            logger.info(f"毛利润={profit}, 手续费={fee}, 净利润={profit-fee}")
            
            return True
            
        except Exception as e:
            logger.error(f"平多单失败：{str(e)}")
            return False
    
    def close_short_position(self, position_id, current_price):
        """平空单"""
        try:
            # 获取持仓信息
            positions = self.db.get_open_positions(self.symbol)
            position = next((p for p in positions if p[0] == position_id), None)
            
            if not position:
                logger.error(f"未找到持仓ID：{position_id}")
                return False
            
            # 创建市价买单
            order = self.exchange.create_market_buy_order(
                self.symbol,
                position[3],  # amount
                params={
                    'type': 'market',
                    'positionSide': 'SHORT'
                }
            )
            
            # 计算盈利
            sell_value = position[4] * position[3]  # entry_price * amount
            buy_value = current_price * position[3]
            profit = sell_value - buy_value
            
            # 获取手续费
            fee = order.get('fee', {}).get('cost', 0)
            
            # 更新数据库
            self.db.close_position(
                position_id=position_id,
                close_price=current_price,
                close_order_id=order['id'],
                profit=profit,
                fee=fee
            )
            
            logger.info(f"平空单成功：开仓价={position[4]}, 平仓价={current_price}, ")
            logger.info(f"毛利润={profit}, 手续费={fee}, 净利润={profit-fee}")
            
            return True
            
        except Exception as e:
            logger.error(f"平空单失败：{str(e)}")
            return False
    
    def run(self):
        """运行交易策略"""
        logger.info(f"开始运行{self.symbol}网格交易策略...")
        logger.info(f"交易参数：")
        logger.info(f"交易对：{self.symbol}")
        logger.info(f"单次交易数量：{self.trade_amount} {self.symbol.split('/')[0]}")
        logger.info(f"开多单阈值：跌{self.price_drop_threshold}")
        logger.info(f"开空单阈值：涨{self.price_rise_threshold}")
        logger.info(f"多单获利平仓阈值：{self.long_profit_threshold}")
        logger.info(f"空单获利平仓阈值：{self.short_profit_threshold}")
        
        last_price = self.get_current_price()
        if last_price is None:
            return
        
        while True:
            try:
                # 获取当前价格
                current_price = self.get_current_price()
                if current_price is None:
                    time.sleep(5)
                    continue
                
                price_change = current_price - last_price
                
                # 检查是否需要开多单（价格下跌）
                if price_change <= -self.price_drop_threshold:
                    self.place_long_order(current_price)
                    last_price = current_price
                
                # 检查是否需要开空单（价格上涨）
                elif price_change >= self.price_rise_threshold:
                    self.place_short_order(current_price)
                    last_price = current_price
                
                # 获取当前持仓
                open_positions = self.db.get_open_positions(self.symbol)
                
                # 检查多空持仓情况
                long_positions = sum(1 for p in open_positions if p[2] == 'long')
                short_positions = sum(1 for p in open_positions if p[2] == 'short')
                
                # 如果没有多仓，开一个多单
                if long_positions == 0:
                    logger.info("当前无多仓，开启多单")
                    self.place_long_order(current_price)
                    last_price = current_price
                
                # 如果没有空仓，开一个空单
                if short_positions == 0:
                    logger.info("当前无空仓，开启空单")
                    self.place_short_order(current_price)
                    last_price = current_price
                
                # 检查是否到达整点
                if self.should_check_positions():
                    # 获取1小时K线数据
                    kline = self.get_hourly_kline()
                    if kline:
                        close_price = kline['close']
                        logger.info(f"1小时K线收盘价：{close_price}")
                        
                        # 检查持仓是否需要平仓
                        for position in open_positions:
                            position_id = position[0]
                            position_type = position[2]
                            entry_price = float(position[4])  # 转换为float类型
                            
                            # 使用1小时K线收盘价检查是否需要平仓
                            if position_type == 'long' and close_price - entry_price >= self.long_profit_threshold:
                                self.close_long_position(position_id, close_price)
                            elif position_type == 'short' and entry_price - close_price >= self.short_profit_threshold:
                                self.close_short_position(position_id, close_price)
                
                # 输出当前持仓信息
                if open_positions:
                    long_positions = sum(1 for p in open_positions if p[2] == 'long')
                    short_positions = sum(1 for p in open_positions if p[2] == 'short')
                    logger.info(f"当前持仓情况：")
                    logger.info(f"多单数量：{long_positions}")
                    logger.info(f"空单数量：{short_positions}")
                
                # 添加适当的延迟，避免触发币安API限制
                time.sleep(5)
                
            except ccxt.NetworkError as e:
                logger.error(f"网络错误：{str(e)}")
                time.sleep(10)  # 网络错误时等待更长时间
            except ccxt.ExchangeError as e:
                logger.error(f"交易所错误：{str(e)}")
                time.sleep(5)
            except Exception as e:
                logger.error(f"运行错误：{str(e)}")
                time.sleep(5)

if __name__ == '__main__':
    try:
        # 支持多个交易对，可以为每个交易对设置不同的参数
        trading_pairs = [
            {
                'symbol': 'ETH/USDT',
                'trade_amount': 0.1,
                'thresholds': {
                    'price_drop': 10,
                    'price_rise': 10,
                    'long_profit': 50,
                    'short_profit': 50
                }
            },
            {
                'symbol': 'BTC/USDT',
                'trade_amount': 0.01,
                'thresholds': {
                    'price_drop': 15,
                    'price_rise': 15,
                    'long_profit': 75,
                    'short_profit': 75
                }
            },
            # 可以添加更多交易对
        ]
        
        # 创建多个交易实例
        traders = []
        for pair in trading_pairs:
            # 创建交易实例
            trader = CryptoGridTrading(
                symbol=pair['symbol'],
                trade_amount=pair['trade_amount']
            )
            
            # 设置交易对特定的阈值
            if 'thresholds' in pair:
                trader.set_thresholds(**pair['thresholds'])
            
            traders.append(trader)
        
        # 运行所有交易实例
        for trader in traders:
            logger.info(f"启动{trader.symbol}网格交易...")
            trader.run()
            
    except KeyboardInterrupt:
        logger.info("程序被用户中断")
    except Exception as e:
        logger.error(f"程序异常退出：{str(e)}")
