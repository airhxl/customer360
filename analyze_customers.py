"""
客户360°助手 · 第二步：Python 数据统计（对应 SQL）
====================================================
目的：把读出来的客户数据，用Python做"分组统计"和"条件筛选"。

这一课的核心：Python 写法 ↔ SQL 写法 一一对应：
  SQL: SELECT 行业, COUNT(*) FROM 客户表 GROUP BY 行业
  Python: for 循环把客户按"所属行业"装进字典，再数个数

  SQL: SELECT * FROM 客户表 WHERE 客户状态 = '流失风险'
  Python: for 循环 + if 判断
"""

import requests
from collections import Counter

from secret_local import APP_ID, APP_SECRET, APP_TOKEN
TABLE_ID = "tblDRh32uDpu7UQB"   # 客户表

# ---------- 1. 读数据（跟第一步一样） ----------
resp = requests.post(
    "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
    json={"app_id": APP_ID, "app_secret": APP_SECRET},
)
token = resp.json()["tenant_access_token"]

url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{APP_TOKEN}/tables/{TABLE_ID}/records"
records = requests.get(url, headers={"Authorization": f"Bearer {token}"}).json()["data"]["items"]

print(f"✅ 读到了 {len(records)} 条客户记录\n")

# ---------- 2. 按行业统计（= SQL: GROUP BY 行业, COUNT(*)） ----------
# Counter 是Python自带的计数器：把"制造/零售/互联网/金融"分别数个数
industry_count = Counter()
for r in records:
    industry = r["fields"].get("所属行业", "未知")
    industry_count[industry] += 1

print("【按行业统计】（= SELECT 所属行业, COUNT(*) GROUP BY 所属行业）")
for industry, count in industry_count.most_common():
    print(f"  {industry}: {count} 家客户")

# ---------- 3. 筛选流失风险客户（= SQL: WHERE 客户状态 = '流失风险'） ----------
print("\n【流失风险客户】（= SELECT * WHERE 客户状态 = '流失风险'）")
for r in records:
    fields = r["fields"]
    if fields.get("客户状态") == "流失风险":
        print(f"  ⚠️  {fields.get('客户名称')} | {fields.get('所属行业')} | {fields.get('客户规模')}")

# ---------- 4. 组合：每个行业里有多少"进行中"客户（= GROUP BY + WHERE 组合） ----------
print("\n【每个行业的进行中客户数】（= GROUP BY 行业 + WHERE 状态=进行中）")
active_by_industry = Counter()
for r in records:
    fields = r["fields"]
    if fields.get("客户状态") == "进行中":
        active_by_industry[fields.get("所属行业", "未知")] += 1
for industry, count in active_by_industry.most_common():
    print(f"  {industry}: {count} 家")
