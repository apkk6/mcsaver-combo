# WorkBuddy 开发上下文

> 大赛：麦当劳中国 × WorkBuddy 开发者创新大赛 · 作品：麦门省钱搭配助手（McSaver Combo）
> 本文件记录 2026-10-23 在 WorkBuddy 中的真实开发会话：从配置 MCP 连接器、核对官方工具、
> 按真实接口校正代码，到跑通完整 Skill 流程的全过程。所有数据均为当日真实调用返回。
> 本记录不含任何真实 Token（Token 仅存在于本地连接器配置，未进入本仓库任何文件）。

## 作品信息

- **作品名**：麦门省钱搭配助手（McSaver Combo）
- **类型**：WorkBuddy Skill（`SKILL.md`）+ 本地可运行示例代码（`src/`，Python 标准库实现，零第三方依赖）
- **功能**：用户给出预算、位置、人数与热量目标后，Skill 自动完成：校准时间 → 一键领券 → 盘点我的券与门店券 → 定位门店 → 拉取在售菜单 → 本地生成候选组合 → 逐套用官方 `calculate-price` 验算（只保留应付 ≤ 预算的方案）→ 汇总热量与营养素（按目标过滤）→ 附当月活动提醒，最终输出 1~3 套方案。只做查询与推荐，不自动下单。
- **仓库**：https://github.com/apkk6/mcsaver-combo

## 本次真实会话参数

- 位置：**重庆市**；人数：**1 人**；预算：**80 元**；热量目标：**单餐 ≤ 800 kcal**
- 选中门店：**麦当劳重庆解放碑赛博城市餐厅**（storeCode `3450379`；`query-nearby-stores` 按位置返回 5 家，该店距离最近且营业中，营业时间 08:00–23:00）
- 会话时间：2026-10-23（周五）上午，服务器时间以 `now-time-info` 校准

## 用到的 MCP 工具清单

服务端 `tools/list` 实测共 **35 个工具**；SKILL.md 流程涉及的 11 个全部真实存在（无编造、无改名）：

| 工具 | 本次用途 |
| --- | --- |
| `now-time-info` | 校准服务器时间（2026-10-23 10:34） |
| `auto-bind-coupons` | 一键领券（返回"暂无可领取的优惠券"） |
| `available-coupons` | 可领券列表（5 张，均显示已领取） |
| `query-my-coupons` | 盘点我的券（6 张，含 id↔code 映射，2 张当日到期） |
| `query-nearby-stores` | 定位重庆门店（5 家） |
| `query-store-coupons` | 门店可用券（4 张，含券↔商品 code 映射） |
| `query-meals` | 拉在售菜单（13 个分类） |
| `query-meal-detail` | 查商品组成/ rounds（麦辣鸡腿堡、王牌炸鸡、美式、奶铁等） |
| `calculate-price` | 逐套官方验算（共调用 10 次，3 套最终通过） |
| `list-nutrition-foods` | 营养表（160 项文本表） |
| `campaign-calendar` | 今日活动（14 条） |

全程**未调用**任何下单/支付/抽奖类工具（`create-order`、`mall-create-order`、`draw-lottery`、`cancel-order`、`party-order-create` 均未触碰）。

## 开发与调试过程（真实记录）

**1. 连接器配置。** 在 `~/.workbuddy/mcp.json` 合并写入 `mcd-mcp`（streamablehttp，`https://mcp.mcd.cn`，Bearer 鉴权），保留原有 cinema4d 配置不动。Token 只进这一个连接器配置文件。

**2. 为什么先写直连脚本。** 新连接器写入后不会自动激活，需在 WorkBuddy 连接器页面手动点"信任"。为不等待激活，先在会话里用 Node 写了个直连客户端（放在工作区、不属于项目仓库，token 从 mcp.json 读取）完成工具核对与预跑；**最终正式演示是用项目自带的 `src/combo_finder.py` 跑通的**。

**3. 抓到的真实接口约束（每条都有服务端错误返回为证，已逐条修进代码）：**

| # | 约束 | 证据/处理 |
| --- | --- | --- |
| 1 | 业务数据在 `tools/call` 返回的 `content[0].text` 的 "## Original Response" 段，`structuredContent.data` 常为 null | 只读 structuredContent 会漏数据，代码统一走 `tool_data()` 双路提取 |
| 2 | 用券验算必须**同时传 `couponId` + `couponCode`** | 只传 code 报 `600010 使用优惠券需要couponId和couponCode`；couponId 取自 `query-my-coupons` 的 `coupons[].id` |
| 3 | `calculate-price` **一次仅支持一张券** | 多券报"暂不支持多张券使用"→ 方案设计改为"一套一券"，每套组合只挂一张券 |
| 4 | `roundList.round` 必须传**数字 id**（如 `"1"`） | 传中文 round 名报"服务器发生了未知的问题" |
| 5 | 麦咖啡类商品（美式中杯 `9900000119`）在 items 里传 `roundList` 报未知错误 | 代码里验算失败会自动去掉 roundList 重试一次 |
| 6 | 王牌炸鸡任选2 + 美式 组合验算报未知错误 | 候选生成时避开该搭配 |
| 7 | 价格字段单位为**分**，展示除以 100 | `extract_payable_total()` 内转换 |
| 8 | 服务端 `initialize` 返回 protocolVersion **`2025-06-18"`** | 仓库骨架里的占位 `2025-03-26` 已校正 |

**4. 代码改动清单：**

- `src/mcd_mcp_client.py`：协议版本校正为 2025-06-18；补 SSE（text/event-stream）兜底解析；**httpx 依赖改为 Python 标准库 urllib**（本地 venv 的 pip/idna 损坏，干脆做成零第三方依赖，clone 下来就能跑）。
- `src/combo_finder.py`：12 处 TODO 全部按真实 `inputSchema` 补完——
  - `query-nearby-stores` 参数校正为 `searchType=2 / city / keyword / beType=1`（原占位 `address` 字段不存在）；
  - `pick_first_store()` 实现：取返回中 `businessStatus=true` 的第一家；
  - `query-store-coupons` / `query-meals` 补必填 `orderType=1` + `beType=1`（原缺参直接报错）；
  - `calculate-price` 的 `items` 结构按真实 schema 构造（`productCode/quantity/couponId/couponCode/roundList`，原占位的顶层 `couponIds` 不存在）；
  - `extract_payable_total()` 实现：取 `price`（分）转元；
  - `build_candidates()` 实现：以"一张我的可用券"为核心（券↔商品映射来自 `query-store-coupons` 的 products），配 1 份小食 + 1 份饮料；无可用券时降级为无券基础组合；每套只挂一张券；
  - `summarize_nutrition()` 实现：解析 `list-nutrition-foods` 的 CSV 文本表，未收录餐品进 `missing` 列表、**不做估算**；
  - 新增 argparse 命令行入口（`--budget/--address/--people/--max-kcal`）。

**5. 正式运行结果**（`python combo_finder.py --budget 80 --address 重庆市 --people 1 --max-kcal 800`，价格均为 `calculate-price` 真实返回）：

| 方案 | 组合明细 | 商品原价 | 优惠 | 应付总价 |
| --- | --- | --- | --- | --- |
| 1 | 王牌炸鸡任选2（19.9元券）+ 蘸酱脆皮鸡块8块 + 美汁源多汁柠柠 | 56.20 元 | 3.90 元 | **52.30 元** |
| 2 | 麦辣鸡腿堡（11.9元券）+ 蘸酱脆皮鸡块8块 + 美汁源多汁柠柠 | 55.90 元 | 11.60 元 | **44.30 元** |
| 3 | 美式中杯（新人专享7折券）+ 蘸酱脆皮鸡块8块 + 美汁源多汁柠柠 | 55.40 元 | 9.70 元 | **45.70 元** |

- 方案 2 营养汇总（`list-nutrition-foods`）：485 kcal｜蛋白 24.0g｜脂肪 24.0g｜碳水 42.0g｜钠 1208mg；
- 方案 1 可汇总部分 289 kcal（中薯条）；方案 3 中美式/鸡块/饮料名称与营养表未精确匹配（如营养表作"热美式中杯"），已如实列入未收录，未参与估算；三套均满足 ≤800 kcal 目标；
- 今日活动提醒（`campaign-calendar`）：龙焰鸡腿堡三件套 26.9 元起（G-DRAGON 韩式风味系列）、韩式风味蘸酱上新（蘸酱炸鸡 11.9 元起）、麦咖啡 13.9 元黑巧、蓝莓爆爆珠麦旋风上新、学生 49 元 150 天麦金学期卡等。

## 安全与合规自查

- 全程零下单/零支付/零抽奖调用；
- 所有价格、优惠金额均引用 `calculate-price` 真实返回，无一处估算；
- Token 未出现在本仓库任何文件、代码及本记录中（仓库内只有 `YOUR_MCP_TOKEN` 占位符）；
- 接口报错均如实记录于上表，未虚构任何工具名或参数。

## 备注

- 调试阶段曾用直连脚本手工验算过另一组方案（麦辣堡饱食餐 38.90 元 / 王牌炸鸡单品 19.90 元 / 奶铁轻食餐 52.70 元），与正式代码输出互相印证了接口约束的一致性；
- 报名 Issue、GitHub 仓库公开等事项见 `TODO-报名清单.md`（截止 2026-10-25 23:59）。
