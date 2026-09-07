import csv
import os
import sqlite3
from flask import Flask, jsonify, send_from_directory

app = Flask(__name__, static_folder='../frontend', static_url_path="")

DATA_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'bawangchaji_sales.csv')
DB_PATH = os.path.join(os.path.dirname(__file__), 'bawangchaji.db')


def init_db():
    """初始化数据库：创建表并导入CSV数据"""
    print(f"正在初始化数据库: {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # 先删除旧表，确保数据结构最新
    c.execute("DROP TABLE IF EXISTS sales")

    c.execute(
        """CREATE TABLE sales (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT,
        city TEXT,
        store_id TEXT,
        product TEXT,
        category TEXT,
        unit_price REAL,
        quantity INTEGER,
        discount REAL,
        revenue REAL,
        member_pct REAL,
        weather TEXT,
        season TEXT,
        is_holiday TEXT,
        campaign TEXT
        )"""
    )

    try:
        with open(DATA_PATH, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            count = 0
            for row in reader:
                try:
                    c.execute(
                        "INSERT INTO sales VALUES (NULL,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                        (
                            row.get("日期"),
                            row.get("城市"),
                            row.get("门店编号"),
                            row.get("产品名称"),
                            row.get("产品类别"),
                            float(row.get("单价(元)", 0)),
                            int(row.get("销量(杯)", 0)),
                            float(row.get("折扣", 0)),
                            float(row.get("实付金额(元)", 0)),
                            float(row.get("会员占比(%)", 0)),
                            row.get("天气"),
                            row.get("季节"),
                            row.get("是否节假日"),
                            row.get("营销活动"),
                        ),
                    )
                    count += 1
                except Exception as e:
                    print(f"跳过错误行: {e}")

            conn.commit()
            print(f"成功导入 {count} 条数据。")
    except FileNotFoundError:
        print(f"错误: 找不到数据文件 {DATA_PATH}")
    finally:
        conn.close()


def get_db_connection():
    """获取数据库连接，并检查表是否存在"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    # 检查表是否存在
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='sales';")
    if not cursor.fetchone():
        conn.close()
        # 如果表不存在，重新初始化
        init_db()
        # 重新连接
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row

    return conn


def query(sql, params=()):
    conn = get_db_connection()
    try:
        rows = conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


@app.route('/')
def index():
    return send_from_directory(app.static_folder, "index.html")


@app.route('/api/summary')
def api_summary():
    r = query(
        "SELECT SUM(quantity) as total_qty, SUM(revenue) as total_revenue, COUNT(*) as total_records, AVG(member_pct) as avg_member_pct FROM sales")
    if r:
        return jsonify(r[0])
    return jsonify({})


# --- 补全前端请求的其他 API 接口 ---

@app.route('/api/monthly')
def api_monthly():
    """按月统计销售额和销量"""
    sql = """
        SELECT substr(date, 1, 7) as month, 
               SUM(revenue) as total_revenue, 
               SUM(quantity) as total_qty 
        FROM sales 
        GROUP BY month 
        ORDER BY month
    """
    return jsonify(query(sql))


@app.route('/api/product_rank')
def api_product_rank():
    """产品销量排行 Top 10"""
    sql = """
        SELECT product, SUM(quantity) as total_qty, SUM(revenue) as total_revenue 
        FROM sales 
        GROUP BY product 
        ORDER BY total_qty DESC 
        LIMIT 10
    """
    return jsonify(query(sql))


@app.route('/api/category_pie')
def api_category_pie():
    """品类销售占比"""
    sql = """
        SELECT category, SUM(revenue) as total_revenue 
        FROM sales 
        GROUP BY category
    """
    return jsonify(query(sql))


@app.route('/api/city_rank')
def api_city_rank():
    """城市销量排行"""
    sql = """
        SELECT city, SUM(revenue) as total_revenue, SUM(quantity) as total_qty 
        FROM sales 
        GROUP BY city 
        ORDER BY total_revenue DESC
    """
    return jsonify(query(sql))


@app.route('/api/season')
def api_season():
    """季节销售分析"""
    sql = """
        SELECT season, SUM(revenue) as total_revenue, SUM(quantity) as total_qty 
        FROM sales 
        GROUP BY season
    """
    return jsonify(query(sql))


@app.route('/api/weather')
def api_weather():
    """天气对销售的影响"""
    sql = """
        SELECT weather, AVG(revenue) as avg_revenue, SUM(quantity) as total_qty 
        FROM sales 
        GROUP BY weather
    """
    return jsonify(query(sql))


@app.route('/api/campaign')
def api_campaign():
    """营销活动效果分析"""
    sql = """
        SELECT campaign, SUM(revenue) as total_revenue, AVG(discount) as avg_discount 
        FROM sales 
        GROUP BY campaign
    """
    return jsonify(query(sql))


@app.route('/api/city_product')
def api_city_product():
    """各城市热门产品 (简单返回前5个城市的前3产品)"""
    # 这里为了简化，返回每个城市销售额最高的产品
    sql = """
        SELECT city, product, SUM(revenue) as total_revenue
        FROM sales
        GROUP BY city, product
        ORDER BY city, total_revenue DESC
    """
    # 注意：SQLite 没有简单的 TOP N per group 语法，这里返回所有组合，前端可过滤或后端需复杂处理
    # 为简单起见，直接返回原始数据供前端处理，或者限制总数
    return jsonify(query(sql + " LIMIT 50"))


@app.route('/api/holiday')
def api_holiday():
    """节假日 vs 非节假日对比"""
    sql = """
        SELECT is_holiday, SUM(revenue) as total_revenue, AVG(quantity) as avg_qty 
        FROM sales 
        GROUP BY is_holiday
    """
    return jsonify(query(sql))


@app.route('/api/discount')
def api_discount():
    """折扣区间分析"""
    # 简单将折扣分为几个区间
    sql = """
        SELECT 
            CASE 
                WHEN discount >= 0.9 THEN '9折以上'
                WHEN discount >= 0.8 THEN '8-9折'
                WHEN discount >= 0.7 THEN '7-8折'
                ELSE '7折以下'
            END as discount_range,
            SUM(revenue) as total_revenue,
            SUM(quantity) as total_qty
        FROM sales
        GROUP BY discount_range
        ORDER BY discount_range
    """
    return jsonify(query(sql))


if __name__ == '__main__':
    # 每次启动都检查数据库状态，如果表缺失则自动重建
    # 如果想强制刷新数据，可以手动删除 bawangchaji.db 文件
    if not os.path.exists(DB_PATH):
        init_db()
    else:
        # 可选：如果希望每次启动都强制更新数据，取消下面注释
        # init_db()
        pass

    app.run(host='0.0.0.0', port=5000, debug=True)