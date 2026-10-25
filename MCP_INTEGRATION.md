# MCP 集成说明

本文件说明本项目实际使用的麦当劳 MCP Server、Tool、调用流程和业务价值
（大赛官方要求文件，文件名不可改动）。

## 1. 使用的 MCP Server

| 项 | 内容 |
| --- | --- |
| 服务 | 麦当劳中国 MCP Server（官方远程托管） |
| 接入地址 | `https://mcp.mcd.cn` |
| 传输协议 | Streamable HTTP（MCP 标准） |
| 鉴权 | 请求头 `Authorization: Bearer <MCP_TOKEN>`，Token 在 https://open.mcd.cn/mcp 用手机号登录后于控制台激活申请 |
| 限流 | 每个 Token 每分钟最多 600 次请求，超限返回 429 |
| 配置示例 | 见本仓库 `config/mcp-config.example.json`（Token 仅为占位符） |

> 工具清单来源：麦当劳官方《McDonald's China MCP Server Integration Guide》
> （https://github.com/M-China/mcd-mcp-server ）「3. 工具列表」一节。
> 各 Tool 的入参字段以接入后 `tools/list` 返回的 `inputSchema` 为准，接入时需逐项校正
> （示例代码中已用 `TODO` 标出待校正处）。

## 2. 实际使用的 Tool

本 Skill 只使用下列 Tool，全部为查询/试算类，不涉及下单：

| Tool | 官方名称 | 在本 Skill 中的用途 |
| --- | --- | --- |
| `auto-bind-coupons` | 麦麦省一键领券 | 流程开始时自动领取当前可领的全部麦麦省优惠券 |
| `available-coupons` | 麦麦省券列表查询 | 查看当前可领取的券，补充说明优惠来源 |
| `query-my-coupons` | 我的优惠券查询 | 盘点用户账户下已有的可用券及门槛 |
| `query-nearby-stores` | 查询附近可用门店 | 按用户提供的地址/位置定位目标门店 |
| `query-store-coupons` | 查询用户当前门店下可用的优惠券列表 | 查目标门店专属可用券 |
| `query-meals` | 查询当前可售卖的餐品列表 | 拉取门店在售菜单（分类、餐品编码、标签）作为搭配候选池 |
| `query-meal-detail` | 查询餐品详情 | 查看套餐组成与可替换选项，确认搭配可行性 |
| `calculate-price` | 商品价格计算 | 对每套候选组合按「商品 + 优惠券」试算金额、配送费、优惠金额与应付总价，做最终验算 |
| `list-nutrition-foods` | 餐品营养信息列表 | 汇总组合的能量、蛋白质、脂肪、碳水、钠、钙，支持按热量目标过滤 |
| `campaign-calendar` | 活动日历查询工具 | 查询当月营销活动，给用户做限时活动提醒 |
| `query-my-account` | 我的积分查询 | 附带展示可用积分/即将过期积分，提示可兑换方向 |
| `now-time-info` | 获取当前时间信息 | 校准「当月活动」「券有效期」等时间敏感判断 |

明确**不使用**的 Tool：`create-order`、`cancel-order`、`mall-create-order`、`draw-lottery`、
`party-order-create` 等一切会产生订单、扣减积分或资金动作的工具。本 Skill 只做推荐，不代下单。

## 3. 调用流程

一次「预算搭配」请求的典型调用链：

```
用户输入（预算 / 人数 / 门店或位置 / 热量目标）
│
▼
1. now-time-info 校准当前时间
2. auto-bind-coupons 一键领取麦麦省可领券
3. query-my-coupons 盘点已有券
available-coupons 补充可领券信息
4. query-nearby-stores 定位目标门店
5. query-store-coupons 查门店可用券
6. query-meals 拉取在售菜单候选池
query-meal-detail 核对套餐组成（按需）
7. 按预算 + 券门槛 + 偏好生成候选组合
8. calculate-price 逐套官方试算，淘汰超预算方案
9. list-nutrition-foods 汇总营养，按热量目标过滤/排序
10. campaign-calendar 附当月活动提醒
│
▼
输出 1~3 套方案：明细、券使用说明、验算总价、热量与营养
```

异常处理：

- **401**：Token 无效/过期/未提供 → 提示用户检查 WorkBuddy 中的 MCP 配置与 Token；
- **429**：触发限流（600 次/分钟）→ 降低调用频率、合并查询，本 Skill 单次请求调用量远低于上限；
- 工具返回空结果（如门店无可用券）→ 降级为「无券最优组合」，并明确告知用户。

## 4. 业务价值

- **对用户**：把「翻券、查菜单、凑满减、算总价、查热量」五件分散的事压缩成一句话提问，
且总价来自官方 `calculate-price` 试算而非模型估算，结果可信、可直接照单点餐。
- **对场景**：预算点餐和控卡点餐是高频刚需，券利用率提升对用户是真金白银的节省。
- **对生态**：展示了 MCP 在「优惠资产盘点 + 实时菜单 + 价格试算 + 营养数据」多工具编排下的
组合能力，是单一问答或单一工具调用做不到的完整闭环（查询侧）。
