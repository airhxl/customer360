"""
客户360°助手 · AI摘要版：让豆包给"到期提醒"写人话风险摘要
================================================================================
【本脚本在干什么】
  1. 和 check_expiring.py 一样，从飞书拉合同、算出"30天内到期 + 已过期未续签"
  2. 【新】把这份数据清单"喂"给豆包大模型
  3. 豆包输出"人话风险摘要"（每家客户：风险等级 + 一句话分析 + 建议动作）
  4. 摘要打印出来，同时追加写入 ai_report.log（可追踪、可回归）

【为什么这步值钱】
  check_expiring.py 输出的是【数据】："广州优选零售还剩20天"
  加上AI后输出的是【洞察】："该客户续约中但对接销售为空，剩20天，
  建议本周指派销售启动谈判——高优先级"
  FDE干的事就是：把大模型接进业务流程，让数据变成可行动的判断。

【核心概念：Prompt（提示词）】
  大模型靠"你给它什么"决定"它回什么"。给数据+要求输出格式，
  它就能产出结构化结论。Prompt设计是AI落地最重要的手艺之一。
================================================================================
"""

import requests
from datetime import datetime, date

from secret_local import APP_ID, APP_SECRET, APP_TOKEN, ARK_API_KEY   # 密钥全在本地配置

# =====================================================================
# 第一部分：从飞书拉数据（和check_expiring.py一样，复习）
# =====================================================================
resp = requests.post(
    "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
    json={"app_id": APP_ID, "app_secret": APP_SECRET},
)
token = resp.json()["tenant_access_token"]
headers = {"Authorization": f"Bearer {token}"}

url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{APP_TOKEN}/tables"
tables = {t["name"]: t["table_id"] for t in requests.get(url, headers=headers).json()["data"]["items"]}
CONTRACT_TABLE = tables["合同表"]

url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{APP_TOKEN}/tables/{CONTRACT_TABLE}/records"
contracts = requests.get(url, headers=headers).json()["data"]["items"]

today = date.today()

def to_date(ms_timestamp):
    """毫秒时间戳 → 日期（复习：时间戳是计算机的日历，/1000转秒再转日期）"""
    return datetime.fromtimestamp(ms_timestamp / 1000).date()

expiring, expired = [], []
for ct in contracts:
    f = ct["fields"]
    expire_ms = f.get("到期日期")
    if not expire_ms:
        continue
    expire_date = to_date(expire_ms)
    remaining = (expire_date - today).days
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
    elif remaining < 0 and status != "已续签":
        expired.append(row)

# =====================================================================
# 第二部分：把数据清单拼成一段文字（这是给AI的"输入"）
# =====================================================================
lines = [f"今天是{today}，以下是客户合同风险清单："]
if expiring:
    lines.append(f"未来30天内到期的合同{len(expiring)}份：")
    for r in sorted(expiring, key=lambda x: x["剩余天数"]):
        lines.append(f"- {r['客户']}，合同{r['合同编号']}，金额{r['金额']:.0f}元，还剩{r['剩余天数']}天，状态{r['状态']}")
if expired:
    lines.append(f"已过期且未续签的合同{len(expired)}份：")
    for r in sorted(expired, key=lambda x: x["剩余天数"]):
        lines.append(f"- {r['客户']}，合同{r['合同编号']}，金额{r['金额']:.0f}元，已过期{-r['剩余天数']}天，状态{r['状态']}")
if not expiring and not expired:
    lines.append("- 无到期风险合同")

data_text = "\n".join(lines)

# =====================================================================
# 第三部分：调豆包（Prompt = 角色设定 + 数据 + 输出要求）
# =====================================================================
prompt = (
    "你是企业客户续约风险分析专家。请基于下面的合同风险清单，"
    "输出一份简洁的中文风险摘要：\n"
    "1. 先给一句话总览（风险程度判断）\n"
    "2. 再按紧急程度逐条列出：客户名 | 风险等级(高/中/低) | 一句话分析 | 建议动作\n"
    "3. 如果清单里有客户状态为'续约中'或对接有盲区（比如临近到期），要特别提示\n\n"
    f"【合同风险清单】\n{data_text}"
)

resp = requests.post(
    "https://ark.cn-beijing.volces.com/api/v3/chat/completions",
    headers={
        "Content-Type": "application/json",
        "Authorization": f"Bearer {ARK_API_KEY}",
    },
    json={
        "model": "doubao-seed-2-1-lite-260915",   # 模型ID（已开通）
        "messages": [
            {"role": "system", "content": "你是严谨的客户续约风险分析师，输出要专业、可执行。"},
            {"role": "user", "content": prompt},
        ],
    },
)
data = resp.json()

# =====================================================================
# 第四部分：输出 + 写日志（可追踪可回归）
# =====================================================================
if "choices" in data:
    summary = data["choices"][0]["message"]["content"]
    print("🤖 豆包AI风险摘要：\n")
    print(summary)
    # 追加写入日志（>> 是追加模式，历史记录不丢）
    with open("ai_report.log", "a", encoding="utf-8") as f:
        f.write(f"\n===== {today} 运行 =====\n{summary}\n")
    print(f"\n✅ 已写入 ai_report.log（日志只追加，历史不丢 = 可回归）")
else:
    print("❌ 调用失败，返回内容：")
    print(data)
