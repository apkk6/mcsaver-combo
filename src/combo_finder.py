"""「预算内最划算组合」主流程示例骨架。

对应 SKILL.md 的执行流程，演示如何编排麦当劳 MCP 的 Tool 完成一次搭配：
领券 → 盘点券 → 定位门店 → 拉菜单 → 组合 → 官方试算 → 营养汇总。

说明：
- 各 Tool 的入参字段名以接入后 tools/list 返回的 inputSchema 为准，
  下方带 TODO 的参数名为占位写法，拿到真实 Token 后必须逐项校正才能跑通；
- 本示例只做查询与试算，不调用任何下单类 Tool。
"""

from mcd_mcp_client import McdMcpClient


def find_combos(
    budget_yuan: float,
    address_keyword: str,
    people: int = 1,
    max_kcal_per_person: float | None = None,
) -> list[dict]:
    client = McdMcpClient()
    client.initialize()

    # 1) 一键领券 + 盘点已有券
    client.call_tool("auto-bind-coupons", {})  # TODO: 按 inputSchema 校正参数
    my_coupons = client.call_tool("query-my-coupons", {})  # TODO: 同上

    # 2) 定位门店 + 查门店券
    stores = client.call_tool(
        "query-nearby-stores",
        {"address": address_keyword},  # TODO: 字段名以 inputSchema 为准（如 address / keyword / 经纬度）
    )
    store = pick_first_store(stores)  # TODO: 按返回结构取第一家可用门店
    store_coupons = client.call_tool(
        "query-store-coupons",
        {"storeCode": store["code"]},  # TODO: 字段名以 inputSchema 为准
    )

    # 3) 拉取在售菜单候选池
    meals = client.call_tool(
        "query-meals",
        {"storeCode": store["code"]},  # TODO: 同上
    )

    # 4) 本地组合逻辑（骨架）：按预算与券门槛生成候选组合
    candidates = build_candidates(meals, my_coupons, store_coupons, budget_yuan, people)

    # 5) 逐套用官方 calculate-price 验算，只保留不超预算的
    verified = []
    for combo in candidates:
        priced = client.call_tool(
            "calculate-price",
            {
                "storeCode": store["code"],
                "items": combo["items"],      # TODO: 商品列表结构以 inputSchema 为准
                "couponIds": combo["coupon_ids"],  # TODO: 同上
            },
        )
        total = extract_payable_total(priced)  # TODO: 按返回结构取应付总价字段
        if total is not None and total <= budget_yuan:
            combo["payable_total"] = total
            verified.append(combo)

    # 6) 营养汇总与热量过滤
    nutrition = client.call_tool("list-nutrition-foods", {})  # TODO: 按 inputSchema 校正
    for combo in verified:
        combo["nutrition"] = summarize_nutrition(combo, nutrition)
    if max_kcal_per_person is not None:
        verified = [
            c for c in verified
            if c["nutrition"]["kcal"] / people <= max_kcal_per_person
        ]

    return verified[:3]


# ---- 以下为待实现的本地辅助函数（与 MCP 无关，纯本地逻辑） ----

def pick_first_store(stores_result: dict) -> dict:
    raise NotImplementedError("TODO: 按 query-nearby-stores 的实际返回结构实现")


def build_candidates(meals, my_coupons, store_coupons, budget_yuan, people) -> list[dict]:
    raise NotImplementedError("TODO: 按菜单/券的实际返回结构实现组合生成")


def extract_payable_total(priced_result: dict) -> float | None:
    raise NotImplementedError("TODO: 按 calculate-price 的实际返回结构取应付总价")


def summarize_nutrition(combo: dict, nutrition_result: dict) -> dict:
    raise NotImplementedError("TODO: 按 list-nutrition-foods 的实际返回结构汇总营养")


if __name__ == "__main__":
    results = find_combos(budget_yuan=40, address_keyword="示例地址", people=2)
    for r in results:
        print(r)
