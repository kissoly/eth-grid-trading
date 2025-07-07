import ccxt
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from loguru import logger

class GridBacktest:
    def __init__(self, exchange_id='binance', symbol='BTC/USDT'):
        self.exchange = getattr(ccxt, exchange_id)()
        self.symbol = symbol
        logger.add("backtest.log")
    
    def fetch_historical_data(self, days=30):
        """获取历史数据"""
        try:
            end_time = datetime.now()
            start_time = end_time - timedelta(days=days)
            
            # 获取K线数据
            ohlcv = self.exchange.fetch_ohlcv(
                self.symbol,
                timeframe='1h',
                since=int(start_time.timestamp() * 1000),
                limit=1000
            )
            
            # 转换为DataFrame
            df = pd.DataFrame(
                ohlcv,
                columns=['timestamp', 'open', 'high', 'low', 'close', 'volume']
            )
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            
            return df
            
        except Exception as e:
            logger.error(f"获取历史数据失败：{str(e)}")
            return None
    
    def run_backtest(self, upper_price, lower_price, grid_num, investment):
        """运行回测"""
        try:
            # 获取历史数据
            df = self.fetch_historical_data()
            if df is None:
                return
            
            # 计算网格参数
            grid_interval = (upper_price - lower_price) / grid_num
            grid_levels = [lower_price + i * grid_interval for i in range(grid_num + 1)]
            per_grid_investment = investment / grid_num
            
            # 回测结果
            trades = []
            position = 0
            cash = investment
            initial_price = df.iloc[0]['close']
            
            # 遍历历史数据
            for index, row in df.iterrows():
                price = row['close']
                
                # 检查是否触发网格
                for level in grid_levels:
                    # 买入信号
                    if price <= level and cash >= per_grid_investment:
                        quantity = per_grid_investment / price
                        trades.append({
                            'timestamp': index,
                            'type': 'buy',
                            'price': price,
                            'quantity': quantity,
                            'value': per_grid_investment
                        })
                        position += quantity
                        cash -= per_grid_investment
                        logger.info(f"买入：价格={price}, 数量={quantity}")
                    
                    # 卖出信号
                    elif price >= level and position > 0:
                        quantity = min(position, per_grid_investment / price)
                        value = quantity * price
                        trades.append({
                            'timestamp': index,
                            'type': 'sell',
                            'price': price,
                            'quantity': quantity,
                            'value': value
                        })
                        position -= quantity
                        cash += value
                        logger.info(f"卖出：价格={price}, 数量={quantity}")
            
            # 计算回测结果
            trades_df = pd.DataFrame(trades)
            if len(trades_df) > 0:
                total_profit = sum(trades_df[trades_df['type'] == 'sell']['value']) - \
                              sum(trades_df[trades_df['type'] == 'buy']['value'])
                total_trades = len(trades_df)
                win_trades = len(trades_df[trades_df['type'] == 'sell'])
                
                # 计算最终持仓价值
                final_price = df.iloc[-1]['close']
                position_value = position * final_price
                total_value = cash + position_value
                total_return = (total_value - investment) / investment * 100
                
                # 输出回测结果
                logger.info("\n回测结果汇总：")
                logger.info(f"初始资金：{investment} USDT")
                logger.info(f"回测周期：{df.index[0]} 至 {df.index[-1]}")
                logger.info(f"网格区间：{lower_price} - {upper_price} USDT")
                logger.info(f"网格数量：{grid_num}")
                logger.info(f"总交易次数：{total_trades}")
                logger.info(f"网格交易利润：{total_profit:.2f} USDT")
                logger.info(f"最终持仓：{position:.8f} BTC")
                logger.info(f"持仓市值：{position_value:.2f} USDT")
                logger.info(f"可用现金：{cash:.2f} USDT")
                logger.info(f"总资产：{total_value:.2f} USDT")
                logger.info(f"总收益率：{total_return:.2f}%")
                
                return {
                    'total_profit': total_profit,
                    'total_trades': total_trades,
                    'win_trades': win_trades,
                    'final_position': position,
                    'final_cash': cash,
                    'total_value': total_value,
                    'total_return': total_return
                }
            
            else:
                logger.warning("回测期间没有产生交易")
                return None
            
        except Exception as e:
            logger.error(f"回测过程出错：{str(e)}")
            return None

if __name__ == '__main__':
    # 创建回测实例
    backtest = GridBacktest()
    
    # 设置回测参数
    upper_price = 45000  # 网格上限价格
    lower_price = 40000  # 网格下限价格
    grid_num = 10        # 网格数量
    investment = 1000    # 初始投资额（USDT）
    
    # 运行回测
    results = backtest.run_backtest(upper_price, lower_price, grid_num, investment)