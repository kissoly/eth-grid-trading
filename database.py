import os
import pymysql
from datetime import datetime
from dotenv import load_dotenv
from loguru import logger

class Database:
    def __init__(self):
        load_dotenv()
        
        # 数据库配置
        self.host = os.getenv('DB_HOST', 'localhost')
        self.port = int(os.getenv('DB_PORT', 3306))
        self.user = os.getenv('DB_USER', 'root')
        self.password = os.getenv('DB_PASSWORD', '')
        self.database = os.getenv('DB_NAME', 'grid_trading')
        
        # 初始化数据库连接
        self.init_database()
    
    def get_connection(self):
        """获取数据库连接"""
        return pymysql.connect(
            host=self.host,
            port=self.port,
            user=self.user,
            password=self.password,
            database=self.database,
            charset='utf8mb4'
        )
    
    def init_database(self):
        """初始化数据库和表"""
        try:
            # 连接MySQL（不指定数据库）
            conn = pymysql.connect(
                host=self.host,
                port=self.port,
                user=self.user,
                password=self.password
            )
            cursor = conn.cursor()
            
            # 创建数据库
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS {self.database}")
            conn.commit()
            
            # 切换到目标数据库
            cursor.execute(f"USE {self.database}")
            
            # 创建positions表（记录当前持仓）
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS positions (
                    id BIGINT AUTO_INCREMENT PRIMARY KEY,
                    symbol VARCHAR(20) NOT NULL,
                    position_type ENUM('long', 'short') NOT NULL,
                    amount DECIMAL(20,8) NOT NULL,
                    entry_price DECIMAL(20,8) NOT NULL,
                    entry_time DATETIME NOT NULL,
                    order_id VARCHAR(50) NOT NULL,
                    status ENUM('open', 'closed') NOT NULL DEFAULT 'open',
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
                )
            """)
            
            # 创建trades表（记录交易历史）
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS trades (
                    id BIGINT AUTO_INCREMENT PRIMARY KEY,
                    position_id BIGINT NOT NULL,
                    symbol VARCHAR(20) NOT NULL,
                    trade_type ENUM('open', 'close') NOT NULL,
                    position_type ENUM('long', 'short') NOT NULL,
                    amount DECIMAL(20,8) NOT NULL,
                    price DECIMAL(20,8) NOT NULL,
                    fee DECIMAL(20,8) NOT NULL,
                    fee_currency VARCHAR(10) NOT NULL,
                    order_id VARCHAR(50) NOT NULL,
                    trade_time DATETIME NOT NULL,
                    profit DECIMAL(20,8),
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (position_id) REFERENCES positions(id)
                )
            """)
            
            conn.commit()
            logger.info("数据库初始化成功")
            
        except Exception as e:
            logger.error(f"数据库初始化失败：{str(e)}")
            raise
        finally:
            cursor.close()
            conn.close()
    
    def record_position(self, symbol, position_type, amount, price, order_id):
        """记录新开仓位"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            sql = """
                INSERT INTO positions 
                (symbol, position_type, amount, entry_price, entry_time, order_id)
                VALUES (%s, %s, %s, %s, %s, %s)
            """
            cursor.execute(sql, (
                symbol,
                position_type,
                amount,
                price,
                datetime.now(),
                order_id
            ))
            
            position_id = cursor.lastrowid
            conn.commit()
            
            # 记录开仓交易
            self.record_trade(
                position_id=position_id,
                symbol=symbol,
                trade_type='open',
                position_type=position_type,
                amount=amount,
                price=price,
                fee=0,  # 实际fee需要从交易所获取
                fee_currency='USDT',
                order_id=order_id
            )
            
            return position_id
            
        except Exception as e:
            logger.error(f"记录持仓失败：{str(e)}")
            conn.rollback()
            return None
        finally:
            cursor.close()
            conn.close()
    
    def close_position(self, position_id, close_price, close_order_id, profit, fee=0):
        """记录平仓信息"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # 获取持仓信息
            cursor.execute("SELECT * FROM positions WHERE id = %s", (position_id,))
            position = cursor.fetchone()
            
            if not position:
                raise ValueError(f"持仓ID {position_id} 不存在")
            
            # 更新持仓状态
            cursor.execute("""
                UPDATE positions 
                SET status = 'closed'
                WHERE id = %s
            """, (position_id,))
            
            # 记录平仓交易
            self.record_trade(
                position_id=position_id,
                symbol=position[1],  # symbol
                trade_type='close',
                position_type=position[2],  # position_type
                amount=position[3],  # amount
                price=close_price,
                fee=fee,
                fee_currency='USDT',
                order_id=close_order_id,
                profit=profit
            )
            
            conn.commit()
            
        except Exception as e:
            logger.error(f"记录平仓失败：{str(e)}")
            conn.rollback()
        finally:
            cursor.close()
            conn.close()
    
    def record_trade(self, position_id, symbol, trade_type, position_type, 
                     amount, price, fee, fee_currency, order_id, profit=None):
        """记录交易详情"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            sql = """
                INSERT INTO trades 
                (position_id, symbol, trade_type, position_type, amount, 
                 price, fee, fee_currency, order_id, trade_time, profit)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            cursor.execute(sql, (
                position_id,
                symbol,
                trade_type,
                position_type,
                amount,
                price,
                fee,
                fee_currency,
                order_id,
                datetime.now(),
                profit
            ))
            
            conn.commit()
            
        except Exception as e:
            logger.error(f"记录交易失败：{str(e)}")
            conn.rollback()
        finally:
            cursor.close()
            conn.close()
    
    def get_open_positions(self, symbol=None):
        """获取当前持仓"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            if symbol:
                sql = "SELECT * FROM positions WHERE status = 'open' AND symbol = %s"
                cursor.execute(sql, (symbol,))
            else:
                sql = "SELECT * FROM positions WHERE status = 'open'"
                cursor.execute(sql)
            
            positions = cursor.fetchall()
            return positions
            
        except Exception as e:
            logger.error(f"获取持仓失败：{str(e)}")
            return []
        finally:
            cursor.close()
            conn.close()
    
    def get_position_trades(self, position_id):
        """获取持仓相关的交易记录"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            sql = "SELECT * FROM trades WHERE position_id = %s ORDER BY trade_time"
            cursor.execute(sql, (position_id,))
            
            trades = cursor.fetchall()
            return trades
            
        except Exception as e:
            logger.error(f"获取交易记录失败：{str(e)}")
            return []
        finally:
            cursor.close()
            conn.close()