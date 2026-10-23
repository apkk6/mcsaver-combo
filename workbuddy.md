# WorkBuddy 开发上下文

> 大赛说明：`workbuddy.md` 为使用 WorkBuddy 开发时的对话上下文，用于核验是否符合联动活动
> 奖励条件，可自行导出；参加 WorkBuddy 专项奖励时必须提交（排行榜前 100 名作品提交本文件
> 可得 3,000 WorkBuddy 积分），文件名不可改动。
>
> ⚠️ 本文件目前是**结构化摘要版**。正式提交前，请在 WorkBuddy 中打开本项目的开发会话，
> 用官方导出方式导出真实对话上下文，替换或补充到本文件中，以通过联动奖励核验。

## 作品信息

- **作品名**：麦门省钱搭配助手（McSaver Combo）
- **类型**：WorkBuddy Skill（基于麦当劳中国 MCP Server）
- **功能**：用户给出预算、门店、人数及可选的热量目标后，Skill 自动完成一键领券、优惠盘点、
在售菜单搭配、官方价格试算与营养汇总，输出 1~3 套预算内最划算的点餐组合。
- **目标用户**：预算敏感的学生/打工人、控卡人群、麦乐送高频用户。

## 所用 MCP 工具（麦当劳 MCP Server，https://mcp.mcd.cn）

- `auto-bind-coupons`（麦麦省一键领券）
- `available-coupons`（麦麦省券列表查询）
- `query-my-coupons`（我的优惠券查询）
- `query-store-coupons`（门店可用券查询）
- `query-nearby-stores`（附近门店查询）
- `query-meals`（在售餐品查询）
- `query-meal-detail`（餐品详情）
- `calculate-price`（价格试算，最终总价以此为准）
- `list-nutrition-foods`（营养信息）
- `campaign-calendar`（活动日历）
- `query-my-account`（积分查询）
- `now-time-info`（当前时间）

不使用任何下单/扣减类工具（`create-order`、`mall-create-order`、`draw-lottery` 等）。

## 使用方式

1. 在 https://open.mcd.cn/mcp 用手机号登录并激活 MCP Token；
2. 在 WorkBuddy中按 `config/mcp-config.example.json` 配置并启用 `mcd-mcp`；
3. 导入本仓库 `SKILL.md`，在对话中说：「预算 40，两个人，帮我配一套最划算的」即可触发。

## 开发过程摘要（待用真实导出替换）

- 选题：结合官方建议方向「麦门省钱助手 + 套餐推荐助手」，确定「预算约束 + 券最优 + 营养参考」三合一选题；
- 在 WorkBuddy 中配置麦当劳 MCP 连接器并逐个验证上述 Tool 的连通性；
- 编写 `SKILL.md` 定义触发条件、调用顺序与输出格式，约束「总价只准用 calculate-price 验算、不自动下单」；
- 用 `src/` 下示例代码做脱离对话的连通性自测。
