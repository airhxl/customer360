"""
客户360°助手 · 辅助：列出多维表格里所有数据表
=============================================
目的：当 API 报 WrongTableId（表ID不对）时，用"列出所有表"接口
拿到真实的 table_id，而不是靠猜。

这也是一次真实的 API 调试流程：报错 → 列出资源 → 定位正确ID。
"""

import requests

from secret_local import APP_ID, APP_SECRET, APP_TOKEN

# 1. 换 token
resp = requests.post(
    "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
    json={"app_id": APP_ID, "app_secret": APP_SECRET},
)
token = resp.json()["tenant_access_token"]

# 2. 列出这个 Base 里所有的表
url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{APP_TOKEN}/tables"
headers = {"Authorization": f"Bearer {token}"}
resp2 = requests.get(url, headers=headers)
data = resp2.json()

if data.get("code") != 0:
    print("❌ 列表失败：", data)
    exit(1)

print(f"✅ 这个多维表格里有 {len(data['data']['items'])} 张表：")
print("-" * 60)
for t in data["data"]["items"]:
    print(f"  表名: {t['name']}")
    print(f"  table_id: {t['table_id']}")
    print("-" * 60)
