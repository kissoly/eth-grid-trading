from grid_trading import GridTrading
from database import Database
from loguru import logger
import time
import os

class CryptoGridTrading(GridTrading):
    def __init__(self, symbol, api_key, api_secret, quantity, db):
        super().__init__(symbol, api_key, api_secret, quantity)
        self.db = db
        self.setup_logger()
        self.set_thresholds()

    def setup_logger(self):
        # 移除默认的控制台输出
        logger.remove()
        # 添加带有时间戳的文件输出
        log_file = f"grid_trading_{self.symbol.replace('/', '_')}.log"
        logger.add(log_file, rotation="500 MB", level="INFO")

    def set_thresholds(self, price_drop=10, price_rise=10, long_profit=50, short_profit=50):
        """设置交易阈值参数

        Args:
            price_drop (float): 价格下跌百分比，触发开多单
            price_rise (float): 价格上涨百分比，触发开空单
            long_profit (float): 多单获利百分比，触发平仓
            short_profit (float): 空单获利百分比，触发平仓
        """
        self.price_drop = price_drop  # 价格下跌10%，开多单
        self.price_rise = price_rise  # 价格上涨10%，开空单
        self.long_profit = long_profit  # 多单获利50%，平仓
        self.short_profit = short_profit  # 空单获利50%，平仓

        logger.info(f"{self.symbol}交易阈值设置：")
        logger.info(f"开多单阈值：跌{self.price_drop}")
        logger.info(f"开空单阈值：涨{self.price_rise}")
        logger.info(f"多单获利平仓阈值：{self.long_profit}")
        logger.info(f"空单获利平仓阈值：{self.short_profit}")

def main():
    # 从环境变量获取API密钥
    api_key = os.getenv('BINANCE_API_KEY')
    api_secret = os.getenv('BINANCE_API_SECRET')

    # 初始化数据库
    db = Database()
    db.init_database()

    # 获取激活的交易对配置
    trading_pairs = db.get_active_trading_pairs()

    # 如果没有配置，添加默认的交易对
    if not trading_pairs:
        # 添加ETH/USDT交易对
        db.add_trading_pair(
            symbol='ETH/USDT',
            quantity=0.1,  # 交易数量
            price_drop=10,  # 价格下跌10%时开多单
            price_rise=10,  # 价格上涨10%时开空单
            long_profit=50,  # 多单获利50%时平仓
            short_profit=50,  # 空单获利50%时平仓
            status=1  # 激活状态
        )
        # 添加BTC/USDT交易对
        db.add_trading_pair(
            symbol='BTC/USDT',
            quantity=0.01,
            price_drop=10,
            price_rise=10,
            long_profit=50,
            short_profit=50,
            status=1
        )
        # 重新获取交易对配置
        trading_pairs = db.get_active_trading_pairs()

    # 创建交易实例
    traders = []
    for pair in trading_pairs:
        trader = CryptoGridTrading(
            symbol=pair['symbol'],
            api_key=api_key,
            api_secret=api_secret,
            quantity=pair['quantity'],
            db=db
        )
        # 设置交易阈值
        trader.set_thresholds(
            price_drop=pair['price_drop'],
            price_rise=pair['price_rise'],
            long_profit=pair['long_profit'],
            short_profit=pair['short_profit']
        )
        traders.append(trader)

    # 运行交易
    while True:
        for trader in traders:
            try:
                trader.run()
            except Exception as e:
                logger.error(f"交易对{trader.symbol}运行出错：{str(e)}")
        time.sleep(1)  # 休眠1秒

if __name__ == "__main__":
    main()