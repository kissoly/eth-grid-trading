# 加密货币网格交易系统

这是一个基于Python实现的加密货币网格交易系统，支持BTC和ETH在主流加密货币交易所进行自动化网格交易。

## 功能特点

### BTC网格交易
- 支持自定义价格区间和网格数量
- 自动在不同价格位置放置买卖单
- 订单成交后自动补充新的网格订单

### ETH网格交易
- 支持ETH/USDT交易对
- 价格下跌10个单位自动开0.1个多单
- 价格上涨10个单位自动开0.1个空单
- 多单盈利50个单位自动平仓
- 空单盈利50个单位自动平仓
- 使用MySQL数据库记录交易数据

### Web界面功能
- 实时监控持仓状态
- 动态调整交易参数
- 查看最近交易记录
- 系统运行状态展示
- 自动刷新数据

### 通用功能
- 完整的日志记录系统
- 支持多个交易所（默认使用Binance）
- 实时监控账户余额
- 自动计算交易盈亏

## 安装要求

- Python 3.8+
- MySQL 5.7+
- 安装依赖包：
```bash
pip install -r requirements.txt
```

## 配置说明

1. 复制环境变量示例文件并修改：
```bash
cp .env.example .env
```

2. 在`.env`文件中填入交易所API密钥和数据库配置：
```
# 交易所API配置
API_KEY=your_api_key_here
API_SECRET=your_api_secret_here

# 数据库配置
DB_HOST=localhost
DB_PORT=3306
DB_USER=your_username
DB_PASSWORD=your_password
DB_NAME=grid_trading
```

## 使用方法

### Web界面
1. 启动Web界面：
```bash
streamlit run web_interface.py
```

2. 在浏览器中访问：`http://localhost:8501`

3. 通过Web界面可以：
   - 查看当前持仓信息
   - 修改交易参数
   - 查看最近交易记录
   - 监控系统状态

### BTC网格交易
1. 在`grid_trading.py`中设置交易参数：
```python
upper_price = 45000  # 网格上限价格
lower_price = 40000  # 网格下限价格
grid_num = 10        # 网格数量
total_investment = 1000  # 总投资额（USDT）
```

2. 运行BTC网格交易：
```bash
python grid_trading.py
```

### ETH网格交易
1. 在`eth_grid_trading.py`中可以调整以下参数：
```python
self.trade_amount = 0.1  # 每次交易数量
self.price_drop_threshold = 10  # 跌多少开多单
self.price_rise_threshold = 10  # 涨多少开空单
self.long_profit_threshold = 50  # 多单获利平仓阈值
self.short_profit_threshold = 50  # 空单获利平仓阈值
```

2. 运行ETH网格交易：
```bash
python eth_grid_trading.py
```

## 数据库结构

### positions表（持仓记录）
- id: 持仓ID
- symbol: 交易对
- position_type: 持仓类型（多/空）
- amount: 持仓数量
- entry_price: 开仓价格
- entry_time: 开仓时间
- order_id: 订单ID
- status: 持仓状态
- created_at: 创建时间
- updated_at: 更新时间

### trades表（交易记录）
- id: 交易ID
- position_id: 关联的持仓ID
- symbol: 交易对
- trade_type: 交易类型（开仓/平仓）
- position_type: 持仓类型（多/空）
- amount: 交易数量
- price: 交易价格
- fee: 手续费
- fee_currency: 手续费币种
- order_id: 订单ID
- trade_time: 交易时间
- profit: 交易盈亏
- created_at: 创建时间

## 风险提示

- 本程序仅供学习和研究使用
- 请在实盘交易前充分测试
- 加密货币交易具有高风险，请谨慎使用
- 建议先使用小额资金测试
- 确保账户有足够的资金
- 注意设置合理的交易参数

## 日志说明

- BTC网格交易日志：`grid_trading.log`
- ETH网格交易日志：`eth_grid_trading_{time}.log`
- ETH日志文件大小超过500MB时自动轮换
- ETH日志保留最近10天的记录

## 代码结构

- `grid_trading.py`: BTC网格交易主程序
- `eth_grid_trading.py`: ETH网格交易主程序
- `database.py`: 数据库操作模块
- `web_interface.py`: Web界面程序
- `requirements.txt`: 依赖包列表
- `.env`: 配置文件（需自行创建）
- `.env.example`: 配置文件示例

## 常见问题

1. 数据库连接失败
   - 检查MySQL服务是否运行
   - 验证数据库用户名和密码
   - 确认数据库端口是否正确

2. 交易所API错误
   - 检查API密钥是否正确
   - 确认API权限是否足够
   - 检查网络连接状态

3. 余额不足
   - 确保账户有足够的交易币种
   - 检查交易数量设置是否合理

4. Web界面问题
   - 确保Streamlit正确安装
   - 检查端口8501是否被占用
   - 确认数据库连接正常

## 维护建议

1. 定期检查日志文件
2. 监控数据库大小
3. 备份重要数据
4. 及时更新依赖包
5. 定期检查系统性能
6. 定期检查Web界面运行状态