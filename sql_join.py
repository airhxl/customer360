"""
数据库第三课：JOIN 跨表连查 —— 数据库最核心的技能
================================================================================
【本脚本在干什么】
  回答一个业务问题：每个行业，合同金额>20万的合同各有几份？
  答案需要【合同表】+【客户表】两张表的数据——因为：
    · 合同表：有金额、有客户名，但没有"行业"
    · 客户表：有行业，但没有合同
  所以先把两张表按"客户名"连起来（JOIN），再筛选、分组、计数。

【为什么这是核心技能】
  FDE做数据交付，90%的问题都是"多张表的数据合起来看"。
  JOIN = 数据库最值钱的动作。不会JOIN = 只会看单张表。

【和昨天Python版的对照（可回归验证）】
  昨天 analyze_contracts.py 用Python字典"手动JOIN"算出的答案是：制造2单、金融2单。
  今天用SQL JOIN算，结果应该一模一样——两条路殊途同归，就是"可回归"。

【JOIN语法长什么样】
  SELECT 想要的列
  FROM 合同表
  JOIN 客户表 ON 合同表.客户名 = 客户表.客户名   ← JOIN：按什么字段连
  WHERE 金额 > 200000                            ← 筛选
  GROUP BY 客户表.行业                            ← 分组
  COUNT(*)                                       ← 计数

【运行方式】
  终端里：python3 sql_join.py
  不需要联网！数据已经在 customer360.db 里（昨天fetch_to_db.py存的）
"""

import sqlite3

# =====================================================================
# 连接数据库（注意：直接查本地库，不用调API——这就是入库的好处）
# =====================================================================
conn = sqlite3.connect("customer360.db")
cursor = conn.cursor()

# =====================================================================
# 第一步：先看"单表"的局限（体会为什么要JOIN）
# =====================================================================
print("=" * 55)
print("【第1步】只看合同表——能回答'行业'问题吗？")
print("=" * 55)
cursor.execute("SELECT contract_no, customer, amount, status FROM contracts LIMIT 3")
for row in cursor.fetchall():
    print(f"  {row[0]} | {row[1]} | {row[2]:.0f}元 | {row[3]}")
print("  ↑ 这张表里只有客户名，没有行业 → 回答不了'按行业统计'")

# =====================================================================
# 第二步：JOIN！把客户表"贴"到合同表上
#   概念：JOIN customers ON contracts.customer = customers.name
#      = 拿着合同表里每个客户名，去客户表里找同名的那行，把行业带过来
#    表格的列名要写"表名.列名"，因为两张表可能有同名列
# =====================================================================
print("\n" + "=" * 55)
print("【第2步】JOIN后的全景（合同+客户名+行业+金额）")
print("=" * 55)
cursor.execute("""
    SELECT contracts.customer, customers.industry, contracts.amount
    FROM contracts
    JOIN customers ON contracts.customer = customers.name
""")
for customer, industry, amount in cursor.fetchall():
    print(f"  {customer} | 行业:{industry} | {amount:.0f}元")

# =====================================================================
# 第三步：正式回答问题（JOIN + WHERE + GROUP BY + COUNT 组合拳）
#   逻辑顺序（数据库实际执行顺序）：
#     FROM+JOIN   → 两张表连成一张大表
#     WHERE       → 只留金额>20万的行
#     GROUP BY    → 按行业分组
#     COUNT(*)    → 数每组有几行
# =====================================================================
print("\n" + "=" * 55)
print("【第3步】答案：每个行业 金额>20万 的合同数量")
print("    （JOIN + WHERE + GROUP BY + COUNT 组合拳）")
print("=" * 55)
cursor.execute("""
    SELECT customers.industry, COUNT(*)
    FROM contracts
    JOIN customers ON contracts.customer = customers.name
    WHERE contracts.amount > 200000
    GROUP BY customers.industry
""")
for industry, count in cursor.fetchall():
    print(f"  {industry}: {count} 单")

# =====================================================================
# 第4步：顺手验证——总额按行业汇总（SUM，不是COUNT）
#   概念：COUNT(*) = 数行数；SUM(列) = 把列的值加起来
# =====================================================================
print("\n" + "=" * 55)
print("【第4步】加餐：每个行业的合同总金额（SUM）")
print("=" * 55)
cursor.execute("""
    SELECT customers.industry, SUM(contracts.amount)
    FROM contracts
    JOIN customers ON contracts.customer = customers.name
    GROUP BY customers.industry
""")
for industry, total in cursor.fetchall():
    print(f"  {industry}: 合计 {total/10000:.0f} 万元")

conn.close()
print("\n🎉 JOIN 完成。第3步结果 = 昨天Python算的一样吗？")
