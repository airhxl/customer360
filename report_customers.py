"""
客户360°助手 · 代表作：客户健康度报告
================================================================================
本文件 = 完整学习笔记版。代码可正常运行，注释是今天课程的复习提纲。

【这个脚本在干什么】
  把多维表格里4张表（客户/联系人/合同/工单）的数据读出来，
  按客户合并成一份"健康度报告"——每个客户一行，含联系人数量、
  合同金额合计、未关闭工单数、风险提示。

【脚本的通用骨架】（所有"从飞书取数→加工→出报告"的脚本都一样）
  ① 换 token（证明身份，拿通行证）
  ② 按表名找表（不硬编码ID，避免抄错）
  ③ 读数据（通用函数，四张表共用）
  ④ 跨表关联（用 record_id 把各表数据挂到客户上）
  ⑤ 统计 + 输出报告

  以后写新脚本：①~③直接复制，④~⑤换成你的业务逻辑。

【运行方式】
  终端里：python3 report_customers.py
  或先 cd 到本文件所在目录再运行。

【今天踩过的坑（复习）】
  · App Secret 里的 I/l 长得像，复制要小心 —— 报错"app secret invalid"
  · 表ID要tbl开头、从"列出表"接口拿，不要手抄 —— 报错"TableIdNotFound"
  · 关联字段键名是 record_ids（复数、列表），不是 record_id —— 报错KeyError
  · API返回的金额是字符串'480000'、日期是毫秒时间戳，要转换才能用
  · 看API返回什么，打印出来看，不要猜结构
"""

import requests                                    # 发HTTP请求的库（联网访问飞书）
from datetime import datetime, date                # 日期时间处理
from collections import Counter                    # 计数器（分组统计神器）

# =====================================================================
# 配置区：你自己的应用凭据 + 多维表格文件ID
# =====================================================================
from secret_local import APP_ID, APP_SECRET, APP_TOKEN

# =====================================================================
# ① 换 token：证明身份，拿临时通行证
#    为什么：飞书API不允许无凭证访问。必须先告诉它"我是谁"（app_id+secret），
#    它验证通过后发一张通行证（tenant_access_token，有效期约2小时）。
#    之后每次请求都带上这张通行证，飞书就知道"这个人是合法用户"。
#
#    概念：HTTP请求 = 你的程序给服务器发一条消息。
#      requests.post(url, json={...}) = 向 url 发一条"POST"消息，附带数据。
#      服务器返回的 resp.json() 是JSON格式（一种通用的数据交换格式，
#      长得像 {键: 值}，Python里叫字典 dict）。
# =====================================================================
resp = requests.post(
    "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
    json={"app_id": APP_ID, "app_secret": APP_SECRET},   # 把身份放进请求体发给飞书
)
token = resp.json()["tenant_access_token"]               # 从返回的JSON里取出通行证
headers = {"Authorization": f"Bearer {token}"}            # 把通行证打包成"请求头"
                                                         # 后续每个请求都带上 headers

# =====================================================================
# ② 按表名找表：不硬编码表ID
#    为什么：表ID是一长串随机字符（tbl开头），手抄极易错（0/O、I/l、5/S）。
#    正确姿势：让程序列出所有表，按表名找到目标ID——程序不会抄错。
#
#    概念：函数 def = 把一段代码装进一个"盒子"，起个名字，随时调用。
#      def list_tables(): ... 定义
#      list_tables()          调用
#    这里返回的是 字典 {表名: 表ID}，比如 {'客户表': 'tblDRh32...'}
# =====================================================================
def list_tables():
    """列出多维表格里所有表，返回 {表名: 表ID} 的字典"""
    url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{APP_TOKEN}/tables"
    # f-string：把变量值插进字符串，f"...{APP_TOKEN}..." 会自动替换成真实值
    result = requests.get(url, headers=headers).json()    # GET = "读取"型请求
    return {t["name"]: t["table_id"] for t in result["data"]["items"]}
    # 上面这行是"字典推导式"：遍历返回的每张表t，取它的name做键、table_id做值

tables = list_tables()          # 调用函数，得到全部表
CUSTOMER_TABLE = tables["客户表"]
CONTACT_TABLE  = tables["联系人表"]
CONTRACT_TABLE = tables["合同表"]
TICKET_TABLE   = tables["工单表"]

# =====================================================================
# ③ 读表：一个通用函数，四张表共用
#    为什么：读客户表和读工单表，代码完全一样，只是表ID不同。
#    把重复代码收进函数 → 一处写、四处用。这叫"复用"，是代码整洁的核心。
#
#    概念：list = 列表，一列数据，如 [1, 2, 3] 或 [客户1, 客户2, ...]
# =====================================================================
def read_table(table_id):
    """读一张表的全部记录，返回记录列表；失败时打印错误并返回空列表"""
    url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{APP_TOKEN}/tables/{table_id}/records"
    resp = requests.get(url, headers=headers)
    result = resp.json()
    if result.get("code") != 0:      # 飞书API用 code 表示成功(0)或失败(非0)
        print(f"❌ 读表失败: {result.get('msg')}")   # 失败要打出来，别让程序静默失败
        return []
    return result["data"]["items"]   # items = 所有记录的列表

customers = read_table(CUSTOMER_TABLE)   # 4张表分别读一次
contacts  = read_table(CONTACT_TABLE)
contracts = read_table(CONTRACT_TABLE)
tickets   = read_table(TICKET_TABLE)

# =====================================================================
# ④ 跨表关联：把四张表的数据"挂"到每个客户身上
#    为什么：合同/工单/联系人表里只存了客户ID（record_id），不含客户名/行业。
#    要先建一张"索引表"（客户ID → 客户信息），再去翻译其他表里的ID。
#    这就是数据库 JOIN（连表查询）的手动版，也是FDE数据对接的核心动作。
#
#    概念：record_id = 每条记录的唯一ID（reczz28HEZqe6LyJ 这种），
#    相当于人的身份证号。不同表之间靠它互相指认。
# =====================================================================
customer_info = {}   # 空字典，待填充：{ 客户ID: {名称, 行业, 规模, 状态} }
for c in customers:  # for循环 = 把列表里的每一条记录挨个拿出来处理
    f = c["fields"]  # 每条记录的字段内容都在 fields 里（也是个字典）
    customer_info[c["record_id"]] = {   # 以客户ID为"键"存进去
        "名称": f.get("客户名称", "?"), # .get("字段名", 默认值)：取不到就返回默认值
        "行业": f.get("所属行业", "?"), # 容错：防止某些记录缺字段导致程序崩溃
        "规模": f.get("客户规模", "?"),
        "状态": f.get("客户状态", "?"),
    }

# 关联字段的真实结构（今天踩坑学到的，打印第一条合同记录才看清）：
#   所属客户 = [{'record_ids': ['reczz28...'], 'text': '深圳明远制造', ...}]
#   注意：
#     1. 键名是 record_ids（复数），不是 record_id —— 猜错就KeyError崩溃
#     2. record_ids 是【列表】—— 一个合同可关联多个客户（多对多）
#     3. 还带着 text 字段（客户名），但按ID关联更可靠（名字可能重复）
def linked_customer_ids(fields):
    """从一条记录的关联字段里，取出它关联的所有客户ID（列表）"""
    links = fields.get("所属客户") or []   # 取不到关联字段就用空列表（容错）
    ids = []
    for link in links:
        ids.extend(link.get("record_ids", []))   # extend = 把子列表展开加进ids
    return ids

# 用 Counter（计数器）按客户ID汇总4类数据
# 概念：Counter 会自动做"某个键出现一次就+1"；
# 手动写法是 count[cid] = count.get(cid, 0) + 1，Counter帮你省了这行。
contract_sum = Counter()        # 每个客户的合同金额合计
contact_count = Counter()       # 每个客户的联系人数量
open_ticket_count = Counter()   # 每个客户的未关闭工单数
high_priority_open = Counter()  # 每个客户的高优先级未关闭工单数

for ct in contracts:            # 遍历每张合同
    f = ct["fields"]
    for cid in linked_customer_ids(f):   # 这单合同关联了哪些客户？
        # API返回的金额是字符串 '480000'，必须 float() 转成数字才能相加
        # 为什么是字符串：表格里金额单元格本质上存的是文本，API原样返回
        contract_sum[cid] += float(f.get("合同金额") or 0)  # or 0：空值当0

for ct in contacts:
    for cid in linked_customer_ids(ct["fields"]):
        contact_count[cid] += 1          # 数到1个联系人就+1

for tk in tickets:
    f = tk["fields"]
    # 业务规则：状态=待处理/处理中 → 未关闭；已解决 → 关闭
    # 判断"是不是未关闭"要用字段真实值，不能只看标题文字
    is_open = f.get("状态") in ("待处理", "处理中")
    if is_open:
        for cid in linked_customer_ids(f):
            open_ticket_count[cid] += 1
            if f.get("优先级") == "高":
                high_priority_open[cid] += 1

# =====================================================================
# ⑤ 输出：客户健康度报告
#    为什么：把散在四张表的数据，合并成"一个客户一行"的业务视图。
#    这就是FDE交付物最常见的形态：把数据变成人能看懂、能决策的报告。
#
#    概念：f-string 格式化 = f"文字{变量}文字"，{变量}会被替换成值。
#    {total/10000:.0f} = 把金额除以1万（元→万元），:.0f 表示保留0位小数。
# =====================================================================
print("=" * 62)                                    # 打印62个=，做分隔线
print("客户健康度报告")
print(f"生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}")  # 当前时间
print("=" * 62)

for cid, info in customer_info.items():   # .items() 同时取出字典的键和值
    name = info["名称"]
    total = contract_sum.get(cid, 0)        # .get(键, 0)：没有合同就按0算
    contacts_n = contact_count.get(cid, 0)
    open_n = open_ticket_count.get(cid, 0)
    high_n = high_priority_open.get(cid, 0)

    print(f"\n■ {name}（{info['行业']} | {info['规模']} | 状态:{info['状态']}）")
    print(f"  联系人 {contacts_n} 位 | 合同金额合计 {total/10000:.0f} 万 | 未关闭工单 {open_n} 个（高优 {high_n}）")

    # 风险提示 = 多条件组合判断，这就是"业务规则落地成代码"
    # 面试可讲：规则要能解释"为什么这么判"，且能测试、能回归
    risks = []
    if info["状态"] == "流失风险":
        risks.append("客户状态=流失风险，需立即介入")
    if high_n > 0:
        risks.append(f"有 {high_n} 个高优工单未关闭")
    if total == 0:
        risks.append("无合同记录，可能是纯线索客户")
    if not risks:
        risks.append("暂无显著风险")
    print(f"  ⚠ {'; '.join(risks)}")    # '; '.join(list) = 把列表拼成一行文字
