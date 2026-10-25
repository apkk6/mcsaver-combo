"""「预算内最划算组合」主流程。

对应 SKILL.md 的执行流程，编排麦当劳 MCP 的 Tool 完成一次搭配：
领券 → 盘点券 → 定位门店 → 拉菜单 → 组合 → 官方试算 → 营养汇总 → 活动提醒。

入参字段名均以 2026-10-23 接入后 tools/list 返回的 inputSchema 实测校正：
- query-nearby-stores：必填 beType(1=到店自取) + searchType(2=按位置)，city/keyword 定位；
- query-store-coupons / query-meals / query-meal-detail / calculate-price：到店自取场景
  必填 storeCode + orderType=1 + beType=1，不传 beCode；
- calculate-price 的 items[] 支持 productCode / quantity / couponId / couponCode /
  roundList（round 必须传数字 id，如 "1"）；一次调用仅支持一张券；
- 真实业务数据在 tools/call 返回的 content[0].text 的 "## Original Response" 段
  （structuredContent.data 可能为 null），由 tool_data() 统一提取；
- calculate-price 的价格字段单位为「分」，展示时除以 100。

本示例只做查询与试算，不调用任何下单类 Tool。
"""

import argparse
import json

from mcd_mcp_client import McdMcpClient

# 到店自取场景固定参数（beType=1 时不传 beCode）
ORDER_TYPE = 1
BE_TYPE = 1


# ---------------------------------------------------------------- 基础工具

def tool_data(result: dict):
    """从 MCP tools/call 结果中提取业务数据。

    优先 structuredContent.data；其为 None 时（如 calculate-price），
    回退解析 content[0].text 中 "## Original Response" 段的 JSON；
    非 JSON 文本（如 list-nutrition-foods 的表格）原样返回字符串。
    """
    if not isinstance(result, dict):
        return None
    sc = result.get("structuredContent")
    if isinstance(sc, dict) and sc.get("data") is not None:
        return sc["data"]
    text = ""
    for block in result.get("content") or []:
        if isinstance(block, dict) and isinstance(block.get("text"), str):
            text = block["text"]
            break
    marker = "## Original Response"
    if marker in text:
        body = text.split(marker, 1)[1].strip()
        try:
            return json.loads(body)
        except json.JSONDecodeError:
            return body
    return text or None


def pick_first_store(stores_result: dict) -> dict:
    """从 query-nearby-stores 结果中取第一家营业中的门店。"""
    data = tool_data(stores_result)
    if isinstance(data, dict):  # 防御：个别返回包一层
        data = data.get("list") or data.get("stores") or []
    for store in data or []:
        if store.get("businessStatus") and store.get("storeCode"):
            return {
                "storeCode": str(store["storeCode"]),
                "storeName": store.get("storeName", ""),
            }
    raise RuntimeError("未找到营业中的门店，请更换位置关键词重试")


def fetch_item(client: McdMcpClient, store_code: str, code: str) -> dict | None:
    """查询单个餐品详情，取名称与套餐轮次；查不到名称则返回 None。"""
    result = client.call_tool(
        "query-meal-detail",
        {"storeCode": store_code, "orderType": ORDER_TYPE, "beType": BE_TYPE, "code": str(code)},
    )
    data = tool_data(result) or {}
    name = data.get("name")
    if not name:
        return None
    return {"code": str(code), "name": name, "rounds": data.get("rounds") or []}


def build_round_list(rounds: list) -> list | None:
    """按 query-meal-detail 的 rounds 生成 calculate-price 的 roundList。

    实测约束：round 必须传数字 id（如 "1"），传中文 round 名会报服务器未知错误。
    每轮取前 quantity 个候选，各 1 份。
    """
    if not rounds:
        return None
    first = rounds[0]
    choices = first.get("choices") or []
    qty = first.get("quantity") or 1
    picked = []
    for choice in choices[: max(1, qty)]:
        picked.append({"code": str(choice.get("code")), "quantity": 1})
    if not picked:
        return None
    return [{"round": str(first.get("id")), "comboItemList": picked}]


def codes_from_category(categories: list, keyword: str, limit: int = 3) -> list:
    """从菜单分类中按关键词取前 limit 个餐品 code（如「小食」「饮品」「堡」）。"""
    out = []
    for cat in categories or []:
        if keyword in (cat.get("name") or ""):
            for meal in cat.get("meals") or []:
                code = meal.get("code")
                if code:
                    out.append(str(code))
                    if len(out) >= limit:
                        return out
    return out


# ---------------------------------------------------------------- 主流程

def find_combos(
    budget_yuan: float,
    address_keyword: str,
    people: int = 1,
    max_kcal_per_person: float | None = None,
    city: str | None = None,
) -> list[dict]:
    """按 SKILL.md 流程跑完一次「预算内最划算组合」，返回验算通过的方案列表。"""
    people = max(1, int(people))
    client = McdMcpClient()
    client.initialize()

    # 1) 校准时间（券有效期/当月活动判断依赖）
    client.call_tool("now-time-info", {})

    # 2) 一键领券 + 盘点我的券
    client.call_tool("auto-bind-coupons", {})
    my_coupons = tool_data(client.call_tool("query-my-coupons", {}))

    # 3) 定位门店 + 查门店可用券
    stores = client.call_tool(
        "query-nearby-stores",
        {
            "searchType": 2,  # 按位置搜索
            "city": city or address_keyword,
            "keyword": address_keyword,
            "beType": BE_TYPE,  # 1=到店自取
        },
    )
    store = pick_first_store(stores)
    store_coupons = tool_data(
        client.call_tool(
            "query-store-coupons",
            {"storeCode": store["storeCode"], "orderType": ORDER_TYPE, "beType": BE_TYPE},
        )
    )

    # 4) 拉取在售菜单候选池
    meals = tool_data(
        client.call_tool(
            "query-meals",
            {"storeCode": store["storeCode"], "orderType": ORDER_TYPE, "beType": BE_TYPE},
        )
    )
    categories = (meals or {}).get("categories", [])

    # 5) 本地组合：每套以「一张我的可用券」为核心，配小食 + 饮料（一次仅一张券）
    my_by_code = {
        c.get("code"): c for c in (my_coupons or {}).get("coupons", []) if c.get("code")
    }
    usable_coupons = []
    for sc in store_coupons or []:
        code = sc.get("couponCode")
        products = sc.get("products") or []
        if code in my_by_code and products:
            usable_coupons.append({"coupon": my_by_code[code], "products": products})

    candidates = []
    for entry in usable_coupons[:3]:  # 最多 3 套带券候选
        core_code = str(entry["products"][0].get("productCode"))
        core = fetch_item(client, store["storeCode"], core_code)
        if not core:
            continue
        item = {
            "productCode": core["code"],
            "quantity": people,
            "couponId": entry["coupon"].get("id"),
            "couponCode": entry["coupon"].get("code"),
        }
        round_list = build_round_list(core["rounds"])
        if round_list:
            item["roundList"] = round_list
        names = [core["name"]]
        for r in core["rounds"]:
            for choice in (r.get("choices") or [])[: (r.get("quantity") or 1)]:
                if choice.get("name"):
                    names.append(choice["name"])
        items = [item]
        # 配 1 份小食
        for code in codes_from_category(categories, "小食"):
            side = fetch_item(client, store["storeCode"], code)
            if side:
                items.append({"productCode": side["code"], "quantity": 1})
                names.append(side["name"])
                break
        # 配饮料（按人数）
        for code in codes_from_category(categories, "饮品"):
            drink = fetch_item(client, store["storeCode"], code)
            if drink:
                items.append({"productCode": drink["code"], "quantity": people})
                names.append(drink["name"])
                break
        candidates.append(
            {
                "items": items,
                "names": names,
                "coupon_title": entry["coupon"].get("title", ""),
            }
        )

    if not candidates:
        # 降级：无可用券时给出「主食 + 小食 + 饮料」无券基础组合
        main_codes = codes_from_category(categories, "堡") or codes_from_category(categories, "餐")
        items, names = [], []
        for code in main_codes[:1] + codes_from_category(categories, "小食")[:1] + codes_from_category(categories, "饮品")[:1]:
            it = fetch_item(client, store["storeCode"], code)
            if it:
                qty = people if "堡" in it["name"] or "餐" in it["name"] else 1
                items.append({"productCode": it["code"], "quantity": qty})
                names.append(it["name"])
        if items:
            candidates.append({"items": items, "names": names, "coupon_title": ""})

    # 6) 逐套官方试算，只保留应付总价 ≤ 预算的；roundList 失败时去 roundList 重试一次
    verified = []
    for combo in candidates:
        priced = client.call_tool(
            "calculate-price",
            {
                "storeCode": store["storeCode"],
                "orderType": ORDER_TYPE,
                "beType": BE_TYPE,
                "items": combo["items"],
            },
        )
        total = extract_payable_total(priced)
        if total is None and any("roundList" in it for it in combo["items"]):
            retry_items = [
                {k: v for k, v in it.items() if k != "roundList"} for it in combo["items"]
            ]
            priced = client.call_tool(
                "calculate-price",
                {
                    "storeCode": store["storeCode"],
                    "orderType": ORDER_TYPE,
                    "beType": BE_TYPE,
                    "items": retry_items,
                },
            )
            total = extract_payable_total(priced)
            combo["items"] = retry_items
        if total is not None and total <= budget_yuan:
            combo["payable_total"] = total
            combo["priced_detail"] = tool_data(priced)
            verified.append(combo)

    # 7) 营养汇总与热量过滤
    nutrition = client.call_tool("list-nutrition-foods", {})
    for combo in verified:
        combo["nutrition"] = summarize_nutrition(combo, nutrition)
    if max_kcal_per_person is not None:
        verified = [
            c for c in verified
            if c["nutrition"]["kcal"] / people <= max_kcal_per_person
        ]

    # 8) 当月活动提醒（今日进行中的活动标题）
    calendar = tool_data(client.call_tool("campaign-calendar", {}))
    today_events = []
    for day in (calendar or {}).get("dailyList", []):
        if day.get("today"):
            for event in day.get("events", []):
                article = event.get("articleDto") or {}
                title = article.get("title") or event.get("activityTitle")
                if title:
                    today_events.append(title)
            break
    for combo in verified:
        combo["today_events"] = today_events

    return verified[:3]


def extract_payable_total(priced_result: dict) -> float | None:
    """从 calculate-price 结果取应付总价（单位分 → 元）。"""
    data = tool_data(priced_result)
    if not isinstance(data, dict):
        return None
    price_fen = data.get("price")
    if price_fen is None:
        return None
    return price_fen / 100.0


def summarize_nutrition(combo: dict, nutrition_result) -> dict:
    """按 list-nutrition-foods 的文本表汇总整套热量与营养素。

    表格为 CSV 文本行：名称,说明,能量kJ,能量kcal,蛋白质,脂肪,碳水,钠,钙。
    未收录餐品记入 missing，不做估算。
    """
    table = tool_data(nutrition_result)
    rows = {}
    if isinstance(table, str):
        for line in table.splitlines():
            parts = [p.strip() for p in line.split(",")]
            if len(parts) >= 8 and parts[0]:
                try:
                    rows[parts[0]] = {
                        "kcal": float(parts[3]),
                        "protein": float(parts[4]),
                        "fat": float(parts[5]),
                        "carb": float(parts[6]),
                        "sodium": float(parts[7]),
                    }
                except ValueError:
                    continue  # 表头/非法行
    total = {"kcal": 0.0, "protein": 0.0, "fat": 0.0, "carb": 0.0, "sodium": 0.0, "missing": []}
    for name in combo.get("names", []):
        row = rows.get(name)
        if row:
            for key in ("kcal", "protein", "fat", "carb", "sodium"):
                total[key] += row[key]
        else:
            total["missing"].append(name)
    return total


# ---------------------------------------------------------------- 命令行入口

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="麦门省钱搭配助手：预算内最划算组合")
    parser.add_argument("--budget", type=float, default=80, help="预算（元）")
    parser.add_argument("--address", default="重庆市", help="位置关键词")
    parser.add_argument("--city", default=None, help="城市（缺省同 address）")
    parser.add_argument("--people", type=int, default=1, help="人数")
    parser.add_argument("--max-kcal", type=float, default=None, help="单人热量上限（kcal）")
    args = parser.parse_args()

    results = find_combos(
        budget_yuan=args.budget,
        address_keyword=args.address,
        people=args.people,
        max_kcal_per_person=args.max_kcal,
        city=args.city,
    )

    if not results:
        print("没有找到符合预算/热量目标的组合。")
    for idx, combo in enumerate(results, 1):
        detail = combo.get("priced_detail") or {}
        print(f"\n===== 方案 {idx} =====")
        for item in combo["items"]:
            coupon = f"（用券：{item['couponCode']}）" if item.get("couponCode") else ""
            print(f"  - {item['productCode']} x{item['quantity']}{coupon}")
        print(f"  商品原价：{(detail.get('productOriginalPrice') or 0) / 100:.2f} 元")
        print(f"  优惠金额：{(detail.get('discount') or 0) / 100:.2f} 元")
        print(f"  应付总价：{combo['payable_total']:.2f} 元（calculate-price 验算）")
        nutrition = combo["nutrition"]
        print(
            f"  热量：{nutrition['kcal']:.0f} kcal｜蛋白 {nutrition['protein']:.1f}g｜"
            f"脂肪 {nutrition['fat']:.1f}g｜碳水 {nutrition['carb']:.1f}g｜钠 {nutrition['sodium']:.0f}mg"
        )
        if nutrition["missing"]:
            print(f"  （营养库未收录：{'、'.join(nutrition['missing'])}）")
    if results and results[0].get("today_events"):
        print("\n今日活动提醒：" + "；".join(results[0]["today_events"][:5]))
    print("\n价格与供应以门店实时为准；本 Skill 不自动下单，确认后请在麦当劳官方渠道下单。")
