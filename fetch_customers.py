"""
客户360°助手 · 第一步：用Python读飞书多维表格数据
=====================================================
目的：走通飞书开放API的完整调用链：
  1. 用 App ID + App Secret 换 tenant_access_token（访问令牌）
  2. 拿 token 去查多维表格客户表的记录
  3. 把结果打印出来

FDE 通用套路：任何平台API（飞书/火山引擎/豆包）都是这个三步结构。
"""

import requests

# 密钥从本地配置文件读取（不写死在代码里，避免泄露/无法上Git）
from secret_local import APP_ID, APP_SECRET, APP_TOKEN

# ============ 1. 配置 ============
# 从多维表格URL里拿到的：
# https://xxx.feishu.cn/base/Wq6tbJnu8aZKxusgICjc5iv2nTf?table=blk14svuuH5N7XvC
TABLE_ID  = "tblDRh32uDpu7UQB"              # 客户表的"表ID"（tbl开头，从list_tables.py拿到）

# ============ 2. 第1步：换 token ============
# 飞书API要求：先证明"我是谁"（app_id+app_secret），换一张临时通行证（tenant_access_token）
token_url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
resp = requests.post(token_url, json={
    "app_id": APP_ID,
    "app_secret": APP_SECRET,
})

data = resp.json()
if data.get("code") != 0:
    print("❌ 换token失败：", data)
    exit(1)

token = data["tenant_access_token"]
print("✅ 换token成功")

# ============ 3. 第2步：拿 token 读客户表 ============
# 读记录接口：/bitable/v1/apps/{文件ID}/tables/{表ID}/records
records_url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{APP_TOKEN}/tables/{TABLE_ID}/records"
headers = {"Authorization": f"Bearer {token}"}

resp2 = requests.get(records_url, headers=headers)
data2 = resp2.json()

if data2.get("code") != 0:
    print("❌ 读取记录失败：", data2)
    exit(1)

# ============ 4. 打印结果 ============
records = data2["data"]["items"]
print(f"✅ 客户表共 {len(records)} 条记录：")
print("-" * 50)
for r in records:
    fields = r["fields"]
    # 逐字段取出，字段可能不存在，用 .get() 容错
    name = fields.get("客户名称", "?")
    industry = fields.get("所属行业", "?")
    scale = fields.get("客户规模", "?")
    status = fields.get("客户状态", "?")
    print(f"  {name} | {industry} | {scale} | {status}")
