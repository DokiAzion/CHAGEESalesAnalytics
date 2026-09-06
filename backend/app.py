import csv
import os
import sqlite3
from flask import Flask, jsonify,send_from_directory
app = Flask(__name__,static_folder='../frontend',static_url_path="")

DATA_PATH = os.path.join(os.path.dirname(__file__),'..','data','bawangchaji_sales.csv')
DB_PATH = os.path.join(os.path.dirname(__file__),'bawangchaji.db')

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DROP TABLE IF EXISTS sales")
    c.execute(  """CREATE TABLE sales (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT, city TEXT, store_id TEXT, product TEXT,
            category TEXT, unit_price REAL, quantity INTEGER,
            discount REAL, revenue REAL, member_pct REAL,
            weather TEXT, season TEXT, is_holiday TEXT, campaign TEXT
        )"""
)
    with open(DATA_PATH,'r',encoding='utf-8') as f:
        reader = csv.reader(f)
        for row in reader:
           c.execute(
               "INSERT INTO sales VALUES (NULL,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
               (
                   row["日期"], row["城市"], row["门店编号"], row["产品名称"],
                   row["产品类别"], float(row["单价(元)"]), int(row["销量(杯)"]),
                   float(row["折扣"]), float(row["实付金额(元)"]),
                   float(row["会员占比(%)"]), row["天气"], row["季节"],
                   row["是否节假日"], row["营销活动"],
               ),
            )
        conn.commit()
        conn.close()

def query(sql, params=()):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]

@app.route('/')
def index():
    return send_from_directory(app.static_folder,"index.html")

if __name__ == '__main__':
    if not os.path.exists(DB_PATH):
        init_db()
    app.run(host='0.0.0.0',port=5000,debug=True)















