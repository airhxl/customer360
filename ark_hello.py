"""
豆包API第一课：让Python调用豆包大模型（最小验证）
================================================================================
【本脚本在干什么】
  用一行代码的请求，让豆包大模型说句话——验证：
  1. API Key 有效
  2. 网络能到火山方舟
  3. Python调大模型的基本格式正确

【调用结构（所有大模型API都长这样）】
  POST https://ark.cn-beijing.volces.com/api/v3/chat/completions
  请求体（JSON）：
    model       = 用哪个模型（这里是豆包1.5 pro 32k）
    messages    = 对话内容（system=给AI设定身份，user=你问的话）
  返回体（JSON）：
    choices[0].message.content = AI的回答

【和飞书API的对比（你已经会飞书，这个一看就懂）】
  飞书：换token → 带token请求 → 拿数据
  豆包：直接带API Key请求 → 拿AI回复（不用换token，Key本身就是通行证）

【运行方式】
  终端里：python3 ark_hello.py
"""

import requests
from secret_local import ARK_API_KEY   # Key从本地配置读取（安全课：不写进代码）

# =====================================================================
# ① 发请求：向豆包提问
# =====================================================================
url = "https://ark.cn-beijing.volces.com/api/v3/chat/completions"
headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {ARK_API_KEY}",   # Key放在请求头里
}
payload = {
    "model": "doubao-seed-2-1-lite-260915",     # 豆包Seed 2.1 lite（模型广场首推，便宜够用）
    "messages": [
        {"role": "system", "content": "你是客户风险分析助手，回答简洁专业。"},
        {"role": "user", "content": "你好，请用一句话介绍你自己，再说一个客户续约提醒的建议。"},
    ],
}

resp = requests.post(url, headers=headers, json=payload)
data = resp.json()

# =====================================================================
# ② 处理返回：成功取content，失败打印错误（不静默失败）
# =====================================================================
if "choices" in data:
    reply = data["choices"][0]["message"]["content"]
    print("🤖 豆包回复：")
    print(reply)
else:
    print("❌ 调用失败，返回内容：")
    print(data)   # 失败要把原始返回打出来，才能排查
