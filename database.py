import pymysql
from loguru import logger
import os
from datetime import datetime

class Database:
    def __init__(self):
        self.host = os.getenv('DB_HOST', 'localhost')
        self.user = os.getenv('DB_USER', 'root')
        self.password = os.getenv('DB_PASSWORD', '')
        self.db = os.getenv('DB_NAME', 'grid_trading')
        self.connection = None
        self.connect()

    def connect(self):
        try:
            self.connection = pymysql.connect(
                host=self.host,
                user=self.user,
                password=self.password,
                db=self.db,
                charset='utf8mb4',
                cursorclass=pymysql.cursors.DictCursor
            )
        except Exception as e:
            logger.error(f"数据库连接失败：{str(e)}")
            raise

    def init_database(self):
        try:
            with self.connection.cursor() as cursor:
                # 创建positions表
                cursor.execute("""
                CREATE TABLE IF NOT EXISTS positions (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    symbol VARCHAR(20) NOT NULL,
                    position_type VARCHAR(10) NOT NULL,
                    quantity DECIMAL(20,8) NOT NULL,
                    entry_price DECIMAL(20,8) NOT NULL,
                    current_price DECIMAL(20,8) NOT NULL,
                    profit_loss DECIMAL(20,8) NOT NULL,
                    status VARCHAR(20) NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
                )
                """)

                # 创建trades表
                cursor.execute("""
                CREATE TABLE IF NOT EXISTS trades (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    symbol VARCHAR(20) NOT NULL,
                    trade_type VARCHAR(10) NOT NULL,
                    quantity DECIMAL(20,8) NOT NULL,
                    price DECIMAL(20,8) NOT NULL,
                    profit_loss DECIMAL(20,8),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """)

                # 创建trading_pairs表
                cursor.execute("""
                CREATE TABLE IF NOT EXISTS trading_pairs (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    symbol VARCHAR(20) NOT NULL,
                    quantity DECIMAL(20,8) NOT NULL,
                    price_drop DECIMAL(10,2) NOT NULL DEFAULT 10,
                    price_rise DECIMAL(10,2) NOT NULL DEFAULT 10,
                    long_profit DECIMAL(10,2) NOT NULL DEFAULT 50,
                    short_profit DECIMAL(10,2) NOT NULL DEFAULT 50,
                    status TINYINT NOT NULL DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
                )
                """)

                self.connection.commit()
                logger.info("数据库初始化成功")
        except Exception as e:
            logger.error(f"数据库初始化失败：{str(e)}")
            raise

    def record_position(self, symbol, position_type, quantity, entry_price, current_price, profit_loss, status):
        try:
            with self.connection.cursor() as cursor:
                sql = "INSERT INTO positions (symbol, position_type, quantity, entry_price, current_price, profit_loss, status) VALUES (%s, %s, %s, %s, %s, %s, %s)"
                cursor.execute(sql, (symbol, position_type, quantity, entry_price, current_price, profit_loss, status))
                self.connection.commit()
        except Exception as e:
            logger.error(f"记录持仓信息失败：{str(e)}")
            raise

    def record_trade(self, symbol, trade_type, quantity, price, profit_loss=None):
        try:
            with self.connection.cursor() as cursor:
                sql = "INSERT INTO trades (symbol, trade_type, quantity, price, profit_loss) VALUES (%s, %s, %s, %s, %s)"
                cursor.execute(sql, (symbol, trade_type, quantity, price, profit_loss))
                self.connection.commit()
        except Exception as e:
            logger.error(f"记录交易信息失败：{str(e)}")
            raise

    def get_active_trading_pairs(self):
        """获取所有激活状态的交易对配置"""
        try:
            with self.connection.cursor() as cursor:
                sql = "SELECT * FROM trading_pairs WHERE status = 1"
                cursor.execute(sql)
                return cursor.fetchall()
        except Exception as e:
            logger.error(f"获取交易对配置失败：{str(e)}")
            raise

    def add_trading_pair(self, symbol, quantity, price_drop=10, price_rise=10, 
                        long_profit=50, short_profit=50, status=1):
        """添加新的交易对配置"""
        try:
            with self.connection.cursor() as cursor:
                sql = """
                INSERT INTO trading_pairs 
                (symbol, quantity, price_drop, price_rise, long_profit, short_profit, status) 
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """
                cursor.execute(sql, (symbol, quantity, price_drop, price_rise, 
                                   long_profit, short_profit, status))
                self.connection.commit()
        except Exception as e:
            logger.error(f"添加交易对配置失败：{str(e)}")
            raise

    def update_trading_pair(self, symbol, quantity=None, price_drop=None, price_rise=None, 
                           long_profit=None, short_profit=None, status=None):
        """更新交易对配置"""
        try:
            with self.connection.cursor() as cursor:
                updates = []
                params = []
                if quantity is not None:
                    updates.append("quantity = %s")
                    params.append(quantity)
                if price_drop is not None:
                    updates.append("price_drop = %s")
                    params.append(price_drop)
                if price_rise is not None:
                    updates.append("price_rise = %s")
                    params.append(price_rise)
                if long_profit is not None:
                    updates.append("long_profit = %s")
                    params.append(long_profit)
                if short_profit is not None:
                    updates.append("short_profit = %s")
                    params.append(short_profit)
                if status is not None:
                    updates.append("status = %s")
                    params.append(status)

                if not updates:
                    return

                sql = f"UPDATE trading_pairs SET {', '.join(updates)} WHERE symbol = %s"
                params.append(symbol)
                cursor.execute(sql, params)
                self.connection.commit()
        except Exception as e:
            logger.error(f"更新交易对配置失败：{str(e)}")
            raise