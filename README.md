# 麦门省钱搭配助手（McSaver Combo）

> 基于麦当劳中国 MCP Server 的 Skill：给一个预算和用餐需求，自动领券、查券、查菜单，
> 算出门店当下最划算的点餐组合，并附热量/营养参考，全程用官方 `calculate-price` 验算总价，不靠估算。

本项目为「麦当劳 × WorkBuddy 开发者创新大赛」参赛作品（个人开发，非麦当劳官方产品）。

## 解决什么问题

点麦当劳时最常见的纠结：

- 优惠券一堆，不知道哪张能用、怎么叠最划算；
- 有预算（比如 40 元吃饱两个人），对着菜单凑半天；
- 想控制热量，又不想一个个查营养表。

本 Skill 把这三件事合并成一句话提问：**「预算 40，两个人，在 XX 店吃，热量别太高」**，
剩下的查券、比价、搭配、算总价都由 Skill 调用麦当劳 MCP 完成。

## 功能

1. **一键领券打底**：先调用 `auto-bind-coupons` 领取麦麦省当前可领的券，再查 `available-coupons`、`query-my-coupons` 和门店券 `query-store-coupons`，把可用优惠摸清。
2. **预算内组合推荐**：按门店在售菜单（`query-meals` / `query-meal-detail`）和可用券，组合出 1~3 套不超预算的搭配方案。
3. **官方价格验算**：每套方案都用 `calculate-price` 按「商品 + 优惠券」真实试算，给出商品金额、优惠金额、配送费和应付总价。
4. **营养参考**：用 `list-nutrition-foods` 汇总每套方案的能量、蛋白质、脂肪、碳水、钠，可按热量目标（如单人 ≤ 800 kcal）过滤方案。
5. **活动提醒**：结合 `campaign-calendar` 提示当月进行中的营销活动，避免错过限时优惠。

> 本 Skill 只做查询与推荐，**不自动下单**。确认方案后，用户可自行在麦当劳官方渠道下单。

## 目标用户

- 想省钱的学生党、打工人（预算敏感型点餐）
- 健身/控卡人群（关注餐品热量与营养构成）
- 经常点麦乐送、又懒得研究券的人

## 安装与配置

### 前置条件

1. 一个麦当劳中国 MCP Token（申请方法见下文）。
2. 支持 MCP（Streamable HTTP）的客户端，例如 **WorkBuddy**（本活动官方合作伙伴）、Cherry Studio、Cursor、TRAE 等。

### 第一步：申请 MCP Token

1. 打开麦当劳 MCP 开放平台 https://open.mcd.cn/mcp
2. 点击右上角，使用**手机号**完成验证登录；
3. 登录后点击右上角，点击申请 MCP Token；
4. 阅读并同意服务协议后，即可一键复制 Token。

### 第二步：在 WorkBuddy 中配置 MCP

1. 打开 WorkBuddy，左侧边栏→页签；
2. 点击右上角→，填入以下 JSON（也可直接使用本仓库 `config/mcp-config.example.json`）：

```json
{
"mcpServers": {
"mcd-mcp": {
"type": "streamablehttp",
"url": "https://mcp.mcd.cn",
"headers": {
"Authorization": "Bearer YOUR_MCP_TOKEN"
}
}
}
}
```

3. 把 `YOUR_MCP_TOKEN` 替换为第一步申请到的真实 Token，点击；
4. 回到，将 `mcd-mcp`。

> ⚠️ Token 是个人凭证，**不要**写进任何要提交到 GitHub 的文件；本仓库所有配置文件只保留 `YOUR_MCP_TOKEN` 占位符。

### 第三步：安装本 Skill

将本仓库的 `SKILL.md` 导入 WorkBuddy 的技能目录（或按 WorkBuddy 官方文档的 Skill 导入方式加载本仓库），即可在对话中触发使用。

如需以代码方式调试 MCP 调用，可参考 `src/` 下的最小示例：复制 `.env.example` 为 `.env`，把其中的 `MCD_MCP_TOKEN` 换成真实 Token 后运行示例脚本。

## 使用示例

在 WorkBuddy 对话框中直接说：

- 「预算 40，两个人在公司附近的麦当劳吃午饭，帮我配一套最划算的」
- 「我有啥券能用？配一个 30 元以内的单人餐」
- 「想吃牛肉汉堡，帮我配一餐热量 800 卡以内的，要用上我的券」
- 「这个月麦当劳有啥活动值得薅？」

Skill 的典型回复包含：推荐组合明细、每项单价、用到的优惠券、`calculate-price` 验算的应付总价，以及该组合的热量与主要营养素。

## 项目结构

```
.
├── README.md # 项目介绍（本文件，官方要求文件名）
├── CONTEST_DECLARATION.md # 参赛声明（官方原文，文件名及内容不可改动）
├── MCP_INTEGRATION.md # MCP Server / Tool / 调用流程说明（官方要求文件名）
├── workbuddy.md # WorkBuddy 开发上下文说明（WorkBuddy 专项奖励需提交）
├── SKILL.md # Skill 定义：触发条件、工作流程、输出格式
├── config/
│ └── mcp-config.example.json # MCP 客户端配置示例（Token 为占位符）
├── src/
│ ├── mcd_mcp_client.py # 最小 MCP 客户端骨架（Streamable HTTP + JSON-RPC）
│ └── combo_finder.py # 「预算内最划算组合」主流程示例代码骨架
├──.env.example # 环境变量示例（仅占位符）
└── TODO-报名清单.md # 参赛报名待办清单
```

## 注意事项

- 餐品、价格、优惠券与供应状态均以麦当劳官方渠道实时返回为准，本项目输出仅供参考，不构成营养或消费建议。
- MCP Token 每分钟最多 600 次请求（官方限流），请勿高频轮询；返回 401 时请检查 Token 是否有效。
- 请妥善保管个人 Token，不要提交到公开仓库（见参赛声明·信息安全声明）。

## 官方链接

- 大赛官方仓库：https://github.com/M-China/mcd-developer-innovation-challenge
- 麦当劳 MCP 使用指南：https://github.com/M-China/mcd-mcp-server
- MCP 开放平台：https://open.mcd.cn/mcp
