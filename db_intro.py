"""
数据库入门：SQLite 第一课
================================================================================
本文件 = 数据库(SQLite)的第一课，代码可正常运行，注释是复习提纲。

【本脚本在干什么】
  1. 创建一个SQLite数据库文件（customer360.db）
  2. 在里面建一张表 customers（客户表）
  3. 插入5个客户（就是多维表格客户表里的那5家）
  4. 用SQL查出来 + 按行业分组统计

【数据库是什么】
  数据库 = 专门用来"存数据 + 查数据"的软件。
  你熟悉的多维表格就是数据库的图形化版本——表格、字段、记录一一对应。

  对应关系（重要）：
    多维表格的"表"    = 数据库的"表"（table）
    多维表格的"字段"  = 数据库的"列"（column）
    多维表格的"行"    = 数据库的"记录"（row）

【SQL是什么】
  SQL = 查询数据库的语言（Structured Query Language）。
  你之前用Python写的统计逻辑，SQL都有对应：

    Python:  counter[cid] += 1            → SQL:  COUNT(*)
    Python:  if 状态 == "已续签": 跳过     → SQL:  WHERE 状态 != '已续签'
    Python:  按行业分组统计                 → SQL:  GROUP BY 行业

【SQLite是什么】
  SQLite = 最简单的一种数据库：整个数据库就是一个文件（.db），
  Python自带支持（sqlite3模块），不用装任何东西。FDE做小工具首选它。

【运行方式】
  终端里：python3 db_intro.py
"""

import sqlite3  # Python内置的SQLite支持库（不用安装）

# =====================================================================
# ① 连接数据库
#    概念：sqlite3.connect("文件名") = 打开数据库文件。
#      文件不存在会自动创建；存在就打开（下次运行不会丢数据）。
# =====================================================================
conn = sqlite3.connect("customer360.db")   # 连接/创建数据库文件
cursor = conn.cursor()                      # cursor = "游标"，执行SQL用的手柄

# =====================================================================
# ② 建表（如果不存在）
#    概念：CREATE TABLE = 创建表。IF NOT EXISTS = 表已存在就不重复建。
#    列类型：TEXT=文本，INTEGER=整数，REAL=小数（金额用）
#    主键 PRIMARY KEY = 这一列的值不能重复（像身份证号）
# =====================================================================
cursor.execute("""
    CREATE TABLE IF NOT EXISTS customers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,   -- 自增编号（自动+1）
        name TEXT NOT NULL,                     -- 客户名称
        industry TEXT,                          -- 所属行业
        size TEXT,                              -- 客户规模
        status TEXT                             -- 客户状态
    )
""")

# =====================================================================
# ③ 插入5个客户
#    概念：INSERT INTO 表名 (列名...) VALUES (值...) = 插入一行
#    execute = 执行一条SQL；executemany = 批量执行多条（列表里每个元素一条）
# =====================================================================
customers = [
    ("深圳明远制造", "制造", "500-2000", "进行中"),
    ("广州优选零售", "零售", "2000+", "续约中"),
    ("杭州云启科技", "互联网", "500人以下", "流失风险"),
    ("北京鼎盛金融", "金融", "2000+", "进行中"),
    ("成都新锐网络", "互联网", "500人以下", "续约中"),
]

cursor.executemany(
    "INSERT INTO customers (name, industry, size, status) VALUES (?, ?, ?, ?)",
    customers,
)
# 上面的 ? 是"占位符"：防止SQL注入攻击的标准写法，值从列表里取

conn.commit()   # 提交 = 把改动真正写进文件（不commit不保存）

# =====================================================================
# ④ 查询：把5个客户全部读出来
#    概念：SELECT 列名 FROM 表名 = 查数据
#      * = 所有列。fetchall() = 把查询结果全部取回来（列表套元组）
# =====================================================================
print("=" * 50)
print("【查询1】所有客户（SELECT * FROM customers）")
print("=" * 50)
cursor.execute("SELECT * FROM customers")
rows = cursor.fetchall()
for row in rows:
    print(row)   # 每行 = (id, 名称, 行业, 规模, 状态)

# =====================================================================
# ⑤ 分组统计：按行业数客户数量
#    概念：GROUP BY = 按某列分组；COUNT(*) = 每组有几行
#    这就是你之前用Python Counter("行业")干的事，SQL一句话搞定
# =====================================================================
print("\n" + "=" * 50)
print("【查询2】按行业分组统计（GROUP BY + COUNT）")
print("=" * 50)
cursor.execute("SELECT industry, COUNT(*) FROM customers GROUP BY industry")
for industry, count in cursor.fetchall():
    print(f"{industry}: {count} 家")

# =====================================================================
# ⑥ 条件查询：只查"流失风险"的客户
#    概念：WHERE = 筛选条件（就是Python里的 if）
# =====================================================================
print("\n" + "=" * 50)
print("【查询3】只查流失风险客户（WHERE）")
print("=" * 50)
cursor.execute("SELECT name, status FROM customers WHERE status = '流失风险'")
for name, status in cursor.fetchall():
    print(f"{name} | {status}")

# 关闭连接（养成好习惯：用完要关）
conn.close()
