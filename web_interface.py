import streamlit as st
from eth_grid_trading import ETHGridTrading
from database import Database
import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 初始化数据库连接
db = Database()

def main():
    st.set_page_config(page_title="ETH网格交易系统", layout="wide")
    st.title("ETH网格交易系统")

    # 侧边栏 - 交易参数设置
    with st.sidebar:
        st.header("交易参数设置")
        long_grid_size = st.number_input("多单网格大小", value=10.0, step=0.1)
        short_grid_size = st.number_input("空单网格大小", value=10.0, step=0.1)
        position_size = st.number_input("仓位大小", value=0.1, step=0.01)
        profit_target = st.number_input("目标利润点数", value=50.0, step=1.0)
        
        if st.button("更新参数"):
            # 更新交易参数
            trading_bot = ETHGridTrading()
            trading_bot.long_grid_size = long_grid_size
            trading_bot.short_grid_size = short_grid_size
            trading_bot.position_size = position_size
            trading_bot.profit_target = profit_target
            st.success("参数更新成功！")

    # 主界面 - 交易信息展示
    col1, col2 = st.columns(2)

    # 当前持仓信息
    with col1:
        st.subheader("当前持仓")
        positions = db.get_open_positions()
        if positions:
            for pos in positions:
                st.write(f"类型: {'多单' if pos['type'] == 'long' else '空单'}")
                st.write(f"开仓价格: {pos['entry_price']}")
                st.write(f"数量: {pos['size']}")
                st.write("---")
        else:
            st.info("当前没有持仓")

    # 最近交易记录
    with col2:
        st.subheader("最近交易记录")
        trades = db.get_recent_trades(limit=5)
        if trades:
            for trade in trades:
                st.write(f"时间: {trade['timestamp']}")
                st.write(f"类型: {'开多' if trade['type'] == 'long' else '开空' if trade['type'] == 'short' else '平仓'}")
                st.write(f"价格: {trade['price']}")
                st.write(f"数量: {trade['size']}")
                st.write(f"盈亏: {trade.get('pnl', 'N/A')}")
                st.write("---")
        else:
            st.info("暂无交易记录")

    # 系统状态
    st.subheader("系统状态")
    st.write("✅ 系统运行中")
    
    # 自动刷新
    st.empty()
    st.experimental_rerun()

if __name__ == "__main__":
    main()