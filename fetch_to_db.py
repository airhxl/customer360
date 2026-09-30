"""
数据库第二课：API取数 → 入库 → 查询（FDE真实日常）
================================================================================
【本脚本在干什么】
  1. 从飞书API读取【客户表】和【合同表】的真实数据
  2. 清洗转换（金额字符串→数字、日期毫秒时间戳→年月日）
  3. 存进 SQLite 数据库（customer360.db，两张表：customers / contracts）
  4. 查出来验证：全量客户、全量合同、金额>20万的合同

【为什么这是FDE的日常】
  FDE最常见的工作 = 把客户系统里的数据接出来，整理入库，再交付查询/报表。
  本脚本就是完整流水线：API取数 → 清洗 → 入库 → 查询。
  昨天的脚本是"读出来打印"（用完即弃）；今天多了"入库"（数据沉淀下来）。

【清洗转换是什么】
  API返回的原始数据不直接能用，要"翻译"成能入库的格式：
    · 金额是字符串 '480000' → float 转数字（才能比较大小、求和）
    · 日期是毫秒时间戳 1756... → 转成 '2027-09-01' 人类日期
  这就是FDE说的"数据对接/清洗"，也是面试常问的点。

【运行方式】
  终端里：python3 fetch_to_db.py
  注意：需要联网（要调飞书API），凭据在下面配置区。
"""

import requests                                # 发HTTP请求（访问飞书）
from datetime import datetime, timezone, timedelta  # 时间处理
import sqlite3                                 # SQLite数据库支持（内置）

# =====================================================================
# 配置区：飞书应用凭据（和之前脚本同一套）
# =====================================================================
from secret_local import APP_ID, APP_SECRET, APP_TOKEN

# =====================================================================
# ① 换 token（证明身份，拿通行证）——和之前完全一样，复制复用
# =====================================================================
resp = requests.post(
    "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
    json={"app_id": APP_ID, "app_secret": APP_SECRET},
)
token = resp.json()["tenant_access_token"]
headers = {"Authorization": f"Bearer {token}"}

# =====================================================================
# ② 按表名找表（不硬编码表ID，避免抄错）——复制复用
# =====================================================================
def list_tables():
    url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{APP_TOKEN}/tables"
    result = requests.get(url, headers=headers).json()
    return {t["name"]: t["table_id"] for t in result["data"]["items"]}

tables = list_tables()

# =====================================================================
# ③ 读表（通用函数）——复制复用
# =====================================================================
def read_table(table_id):
    url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{APP_TOKEN}/tables/{table_id}/records"
    resp = requests.get(url, headers=headers)
    result = resp.json()
    if result.get("code") != 0:
        print(f"❌ 读表失败: {result.get('msg')}")
        return []
    return result["data"]["items"]

customers_raw = read_table(tables["客户表"])
contracts_raw = read_table(tables["合同表"])
print(f"✅ 从API读到：客户 {len(customers_raw)} 家、合同 {len(contracts_raw)} 份")

# =====================================================================
# ④ 清洗转换：API原始数据 → 能入库的干净数据
#    先看一眼合同表的真实字段长什么样（打印调试，不猜结构）
# =====================================================================
if contracts_raw:
    first = contracts_raw[0]["fields"]
    print("\n【调试】合同表第一条的原始字段：")
    for k, v in first.items():
        print(f"  {k} = {v}")

# 客户：字段直接可取（都是文本），容错用 .get
clean_customers = []
for c in customers_raw:
    f = c["fields"]
    clean_customers.append((
        f.get("客户名称", "?"),
        f.get("所属行业", "?"),
        f.get("客户规模", "?"),
        f.get("客户状态", "?"),
    ))

# 合同：需要两个关键转换（今天的主角）
def clean_contract(f):
    """把一条合同记录转成可入库的元组"""
    # 金额：字符串 '480000' → float 数字
    # 为什么：数据库里要能做大小比较（>20万）、求和，字符串做不到
    amount = float(f.get("合同金额") or 0)

    # 到期日期：毫秒时间戳（如 1780185600000）→ 'YYYY-MM-DD'
    # 为什么：时间戳是一串数字，人看不懂；转成日期才好读、好筛选
    # 【坑：时区】飞书时间戳按北京时间(UTC+8)存。若按UTC转，会少8小时→日期差1天！
    #   例：2027-09-01 00:00 北京时间 = 2027-08-31 16:00 UTC → 用UTC转就变成8-31
    #   修复：用北京时间时区 timezone(timedelta(hours=8))
    raw_ts = f.get("到期日期")
    if isinstance(raw_ts, int):                      # 数字 = 毫秒时间戳
        expire = datetime.fromtimestamp(raw_ts / 1000, tz=timezone(timedelta(hours=8))).strftime("%Y-%m-%d")
    else:
        expire = str(raw_ts or "")                    # 空值给空字符串

    # 客户名：关联字段里取 text（人类可读名）
    links = f.get("所属客户") or []
    customer_name = links[0].get("text", "?") if links else "?"

    return (f.get("合同编号", "?"), customer_name, amount, expire, f.get("合同状态", "?"))

clean_contracts = [clean_contract(ct["fields"]) for ct in contracts_raw]

# =====================================================================
# ⑤ 入库：连接数据库 → 建表 → 批量插入
#    每次运行先删旧表再重建（DROP + CREATE）：
#    保证结果是"这次API快照"的干净入库，可复现——呼应你坚持的"可回归"
# =====================================================================
conn = sqlite3.connect("customer360.db")
cursor = conn.cursor()

cursor.execute("DROP TABLE IF EXISTS customers")      # 删旧表（上次的残留）
cursor.execute("DROP TABLE IF EXISTS contracts")
cursor.execute("""
    CREATE TABLE customers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT, industry TEXT, size TEXT, status TEXT
    )
""")
cursor.execute("""
    CREATE TABLE contracts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        contract_no TEXT, customer TEXT,
        amount REAL,            -- 金额：REAL类型（小数），已从字符串转数字
        expire_date TEXT,       -- 日期：存成 'YYYY-MM-DD' 文本，好读好筛
        status TEXT
    )
""")

cursor.executemany("INSERT INTO customers (name, industry, size, status) VALUES (?, ?, ?, ?)", clean_customers)
cursor.executemany("INSERT INTO contracts (contract_no, customer, amount, expire_date, status) VALUES (?, ?, ?, ?, ?)", clean_contracts)
conn.commit()
print(f"\n✅ 已入库：customers {len(clean_customers)} 条、contracts {len(clean_contracts)} 条")

# =====================================================================
# ⑥ 查询验证（不查不算完成——"验证"是你一直坚持的）
# =====================================================================
print("\n" + "=" * 55)
print("【验证1】客户表全部（SELECT * FROM customers）")
print("=" * 55)
for row in cursor.execute("SELECT * FROM customers"):
    print(row)

print("\n" + "=" * 55)
print("【验证2】合同表全部（金额已转数字、日期已转日期）")
print("=" * 55)
for row in cursor.execute("SELECT * FROM contracts"):
    print(row)

print("\n" + "=" * 55)
print("【验证3】金额>20万的合同（WHERE amount > 200000）")
print("=" * 55)
for row in cursor.execute("SELECT customer, contract_no, amount, status FROM contracts WHERE amount > 200000"):
    print(f"  {row[0]} | {row[1]} | {row[2]:.0f}元 | {row[3]}")

conn.close()
print("\n🎉 完成：API → 清洗 → 入库 → 查询，全链路走通")
