"""
客户360°助手 · 第三步：30天内到期合同提醒
============================================
需求：找出未来30天内到期的合同，算出还剩几天，输出提醒清单。

这一课的技术点：
  1. API返回的日期是【毫秒时间戳】（如 1819728000000），要转成日期
  2. 计算"还剩几天"要用今天（运行当天）动态算，不能写死日期
  3. 已过期的合同单独列出（那是流失风险信号，就像杭州云启那样）

真实FDE场景：这个脚本就是"到期提醒"的最小版本，之后可以挂定时任务，
每周一自动跑一遍，把结果推给客户成功经理。
"""

import requests
from datetime import datetime, date

from secret_local import APP_ID, APP_SECRET, APP_TOKEN

# ---------- 1. 换 token ----------
resp = requests.post(
    "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
    json={"app_id": APP_ID, "app_secret": APP_SECRET},
)
token = resp.json()["tenant_access_token"]
headers = {"Authorization": f"Bearer {token}"}

# ---------- 2. 按表名找合同表（不硬编码ID） ----------
url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{APP_TOKEN}/tables"
tables = {t["name"]: t["table_id"] for t in requests.get(url, headers=headers).json()["data"]["items"]}
CONTRACT_TABLE = tables["合同表"]

# ---------- 3. 读合同表 ----------
url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{APP_TOKEN}/tables/{CONTRACT_TABLE}/records"
contracts = requests.get(url, headers=headers).json()["data"]["items"]

# ---------- 4. 日期处理 ----------
today = date.today()   # 运行当天，动态取，不写死
print(f"📅 今天是 {today}（脚本每次运行自动取当天）\n")

def to_date(ms_timestamp):
    """把飞书返回的毫秒时间戳转成日期。
    时间戳 = 从1970年1月1日到现在的毫秒数，计算机的"标准日历"。
    /1000 变成秒，datetime.fromtimestamp 转成人类日期。
    """
    return datetime.fromtimestamp(ms_timestamp / 1000).date()

expiring = []   # 未来30天内到期
expired = []    # 已过期

for ct in contracts:
    f = ct["fields"]
    expire_ms = f.get("到期日期")
    if not expire_ms:
        continue   # 没有到期日期的合同跳过（脏数据容错）

    expire_date = to_date(expire_ms)
    remaining = (expire_date - today).days   # 剩余天数，负数=已过期

    # 关联字段里带了客户名（text），直接取，不用再查客户表
    customer = f["所属客户"][0]["text"] if f.get("所属客户") else "未知"
    status = f.get("合同状态", "未知")

    row = {
        "合同编号": f.get("合同编号"),
        "客户": customer,
        "金额": float(f.get("合同金额") or 0),
        "到期日": expire_date,
        "剩余天数": remaining,
        "状态": status,
    }

    if 0 <= remaining <= 30:
        expiring.append(row)
    elif remaining < 0:
        # 业务规则：到期日过了，但状态是"已续签"= 客户已续新合同，不是流失风险
        if status == "已续签":
            print(f"  ℹ️ 排除（已续签）：{customer} | {row['合同编号']} | 到期日 {expire_date} | 状态={status}")
        else:
            expired.append(row)

# ---------- 5. 输出 ----------
print(f"【⚠️ 未来30天内到期：{len(expiring)} 单】（= WHERE 到期日 BETWEEN 今天 AND 今天+30）")
for r in sorted(expiring, key=lambda x: x["剩余天数"]):   # 按紧急程度排序
    print(f"  🔔 {r['客户']} | {r['合同编号']} | 还剩 {r['剩余天数']} 天 | 到期日 {r['到期日']} | {r['金额']:.0f}元")

print(f"\n【❌ 已过期且未续签：{len(expired)} 单】（= WHERE 到期日 < 今天 AND 状态 != '已续签'）")
for r in sorted(expired, key=lambda x: x["剩余天数"]):
    print(f"  💀 {r['客户']} | {r['合同编号']} | 已过期 {-r['剩余天数']} 天 | 到期日 {r['到期日']} | 状态={r['状态']}")

if not expiring and not expired:
    print("  （没有需要提醒的合同）")
