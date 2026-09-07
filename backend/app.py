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
                    # 忽略单行错误，避免整个导入失败
                    pass

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

    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='sales';")
    if not cursor.fetchone():
        conn.close()
        init_db()
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
    # 注意：前端使用 d.avg_member，这里别名改为 avg_member
    r = query(
        "SELECT SUM(quantity) as total_qty, SUM(revenue) as total_revenue, COUNT(*) as total_records, AVG(member_pct) as avg_member FROM sales")
    if r:
        return jsonify(r[0])
    return jsonify({})


@app.route('/api/monthly')
def api_monthly():
    """按月统计销售额和销量"""
    # 修改别名：total_revenue -> revenue, total_qty -> qty 以匹配前端
    sql = """
        SELECT substr(date, 1, 7) as month, 
               SUM(revenue) as revenue, 
               SUM(quantity) as qty 
        FROM sales 
        GROUP BY month 
        ORDER BY month
    """
    return jsonify(query(sql))


@app.route('/api/product_rank')
def api_product_rank():
    """产品销量排行 Top 10"""
    # 修改别名：total_qty -> qty
    sql = """
        SELECT product, SUM(quantity) as qty, SUM(revenue) as revenue 
        FROM sales 
        GROUP BY product 
        ORDER BY qty DESC 
        LIMIT 10
    """
    return jsonify(query(sql))


@app.route('/api/category_pie')
def api_category_pie():
    """品类销售占比"""
    # 前端图表使用的是 qty (销量)，所以这里返回 qty
    # 如果前端想展示营收占比，需修改前端 JS 将 r.qty 改为 r.revenue
    sql = """
        SELECT category, SUM(quantity) as qty 
        FROM sales 
        GROUP BY category
    """
    return jsonify(query(sql))


@app.route('/api/city_rank')
def api_city_rank():
    """城市销量排行"""
    # 修改别名
    sql = """
        SELECT city, SUM(revenue) as revenue, SUM(quantity) as qty 
        FROM sales 
        GROUP BY city 
        ORDER BY revenue DESC
    """
    return jsonify(query(sql))


@app.route('/api/season')
def api_season():
    """季节销售分析"""
    # 修改别名
    sql = """
        SELECT season, SUM(revenue) as revenue, SUM(quantity) as qty 
        FROM sales 
        GROUP BY season
    """
    return jsonify(query(sql))


@app.route('/api/weather')
def api_weather():
    """天气对销售的影响"""
    # 修改别名
    sql = """
        SELECT weather, AVG(revenue) as avg_revenue, AVG(quantity) as avg_qty 
        FROM sales 
        GROUP BY weather
    """
    return jsonify(query(sql))


@app.route('/api/campaign')
def api_campaign():
    """营销活动效果分析"""
    # 修改别名
    sql = """
        SELECT campaign, SUM(revenue) as revenue, AVG(quantity) as avg_qty 
        FROM sales 
        GROUP BY campaign
    """
    return jsonify(query(sql))


@app.route('/api/city_product')
def api_city_product():
    """各城市热门产品 - 热力图数据预处理"""
    raw_data = query("""
        SELECT city, product, SUM(quantity) as qty
        FROM sales
        GROUP BY city, product
    """)

    # 提取所有唯一的城市和产品的列表，用于建立索引映射
    cities = sorted(list(set([r['city'] for r in raw_data])))
    products = sorted(list(set([r['product'] for r in raw_data])))

    # 创建映射字典
    city_index = {c: i for i, c in enumerate(cities)}
    product_index = {p: i for i, p in enumerate(products)}

    # 转换数据格式为 [cityIndex, productIndex, value]
    heatmap_data = []
    for r in raw_data:
        c_idx = city_index.get(r['city'])
        p_idx = product_index.get(r['product'])
        if c_idx is not None and p_idx is not None:
            heatmap_data.append([c_idx, p_idx, r['qty']])

    return jsonify({
        "cities": cities,
        "products": products,
        "data": heatmap_data
    })


@app.route('/api/holiday')
def api_holiday():
    """节假日 vs 非节假日对比"""
    # 修改别名
    sql = """
        SELECT is_holiday, SUM(revenue) as avg_revenue, AVG(quantity) as avg_qty 
        FROM sales 
        GROUP BY is_holiday
    """
    return jsonify(query(sql))


@app.route('/api/discount')
def api_discount():
    """折扣区间分析"""
    # 修改别名
    sql = """
        SELECT 
            CASE 
                WHEN discount >= 0.9 THEN '9折以上'
                WHEN discount >= 0.8 THEN '8-9折'
                WHEN discount >= 0.7 THEN '7-8折'
                ELSE '7折以下'
            END as discount_range,
            SUM(revenue) as revenue,
            SUM(quantity) as qty,
            AVG(quantity) as avg_qty
        FROM sales
        GROUP BY discount_range
        ORDER BY discount_range
    """
    return jsonify(query(sql))


if __name__ == '__main__':
    if not os.path.exists(DB_PATH):
        init_db()
    else:
        # 检查表是否存在，不存在则重建
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='sales';")
        if not cursor.fetchone():
            conn.close()
            init_db()
        else:
            conn.close()

    app.run(host='0.0.0.0', port=5000, debug=True)