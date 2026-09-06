import csv
import os
import sqlite3
from flask import Flask, jsonify,send_from_directory

app = Flask(__name__,static_folder='../frontend',static_url_path="")
DATA_PATH = os.path.join(os.path.dirname(__file__),'..','data','bawangchaji_sales.csv')
DB_PATH = os.path.join(os.path.dirname(__file__),'bawangchaji.db')
@app.route('/')
def index():
    return send_from_directory(app.static_folder,"index.html")

if __name__ == '__main__':
    app.run(host='0.0.0.0',port=5000,debug=True)















