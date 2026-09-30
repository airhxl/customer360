"""
客户360°助手 · 第三步：跨表统计（合同金额 > 20万，按行业分组）
================================================================
需求（你的中文）：每个行业、合同金额大于20万的合同数量
SQL 写法：SELECT 所属行业, COUNT(*) FROM 合同表 WHERE 合同金额 > 200000 GROUP BY 所属行业

技术点：合同表里的"所属客户"是关联字段，只存了客户记录的ID（record_id），
不含行业信息。行业在客户表里。所以要先读客户表，建立"客户ID → 行业"的映射，
再回到合同表翻译。这就是"跨表JOIN"的Python手动版。
"""

import requests
from collections import Counter

from secret_local import APP_ID, APP_SECRET, APP_TOKEN
CUSTOMER_TABLE = "tblDRh32uDpu7UQB"   # 客户表

# ---------- 1. 换 token ----------
resp = requests.post(
    "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
    json={"app_id": APP_ID, "app_secret": APP_SECRET},
)
token = resp.json()["tenant_access_token"]
headers = {"Authorization": f"Bearer {token}"}

def list_tables():
    """列出这个多维表格里所有表，返回 {表名: 表ID}"""
    url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{APP_TOKEN}/tables"
    result = requests.get(url, headers=headers).json()
    return {t["name"]: t["table_id"] for t in result["data"]["items"]}

def find_table_id(tables, keyword):
    """按表名关键词找表ID（不硬编码ID，避免手抄出错）"""
    for name, tid in tables.items():
        if keyword in name:
            print(f"✅ 找到表「{name}」→ {tid}")
            return tid
    print(f"❌ 没找到名字含「{keyword}」的表，现有表：{list(tables.keys())}")
    exit(1)

# 按表名找ID（关键词各取一个独特字）
tables = list_tables()
CUSTOMER_TABLE = find_table_id(tables, "客户表")   # 重新用真实ID
CONTRACT_TABLE = find_table_id(tables, "合同表")

def read_table(table_id):
    """通用函数：读一张表的全部记录（表ID不同，复用同一段逻辑）"""
    url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{APP_TOKEN}/tables/{table_id}/records"
    resp = requests.get(url, headers=headers)
    result = resp.json()
    if result.get("code") != 0:
        # 调试关键：API报错时，把完整返回打出来看，而不是只看崩溃信息
        print(f"❌ 读表失败 {table_id}: code={result.get('code')}, msg={result.get('msg')}")
        print(f"   原始返回: {result}")
        return []
    return result["data"]["items"]

# ---------- 2. 读客户表，建立 客户ID → 行业 的映射 ----------
customers = read_table(CUSTOMER_TABLE)
customer_industry = {}   # { 客户记录ID: 行业 }
for c in customers:
    cid = c["record_id"]                          # 每条记录的唯一ID
    customer_industry[cid] = c["fields"].get("所属行业", "未知")

# ---------- 3. 读合同表，先看真实数据结构 ----------
contracts = read_table(CONTRACT_TABLE)

# 调试：打印第一条合同记录的完整原始数据，看清关联字段长什么样
if contracts:
    first = contracts[0]["fields"]
    print("\n【调试】第一条合同记录的原始字段：")
    for k, v in first.items():
        print(f"  {k} = {repr(v)[:200]}")
    print()

big_deal_by_industry = Counter()   # 统计结果
big_deals = []                     # 明细，便于核对

for ct in contracts:
    f = ct["fields"]
    amount = f.get("合同金额")
    # 关联字段在API里的形态：所属客户 = [{"record_id": "xxx"}]，可能有多条（一个合同对多个客户）
    linked_customers = f.get("所属客户") or []

    # 金额可能是数字或字符串，统一转成数字比较
    try:
        amount = float(amount)
    except (TypeError, ValueError):
        continue   # 金额缺失或异常，跳过这条（真实数据对接时要注意这种脏数据）

    if amount > 200000:   # 对应 SQL 的 WHERE 合同金额 > 200000
        for link in linked_customers:
            # 真实结构：{'record_ids': ['reczz28...'], 'table_id': ..., 'text': '客户名'}
            # record_ids 是列表（一个合同可关联多个客户），逐个取
            for rid in link.get("record_ids", []):
                industry = customer_industry.get(rid, "未知")
                big_deal_by_industry[industry] += 1
                big_deals.append((f.get("合同编号"), industry, amount))

# ---------- 4. 输出结果 ----------
print("【每个行业合同金额>20万的合同数】（= GROUP BY 行业 WHERE 金额>20万）")
for industry, count in big_deal_by_industry.most_common():
    print(f"  {industry}: {count} 单")

print("\n【明细核对】")
for contract_id, industry, amount in big_deals:
    print(f"  {contract_id} | {industry} | {amount:.0f}元")
