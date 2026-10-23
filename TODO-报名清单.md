# TODO 报名清单（需本人完成）

大赛：麦当劳中国 × WorkBuddy 开发者创新大赛
报名及排名期：2026-10-09 10:30 — **2026-10-25 23:59（北京时间）**，10-26 00:00 按公开 Star 数定榜。
官方仓库：https://github.com/M-China/mcd-developer-innovation-challenge

骨架（本目录）已备好官方要求的全部文件。剩下以下步骤必须由本人完成：

- [] 1. 注册/登录 GitHub 账号，并确保账号留有可用邮箱（获奖通知发到 GitHub 注册邮箱）。
- [] 2. 打开 https://open.mcd.cn/mcp ，用本人手机号验证登录，在控制台点获取 MCP Token。
- [] 3. 在 WorkBuddy 中按 `config/mcp-config.example.json` 配置 `mcd-mcp`（把占位符换成自己的 Token），启用后逐个验证 SKILL.md 里用到的 Tool 能正常返回。
- [] 4. 在 WorkBuddy 里完成一次真实的开发/调试会话，并导出对话上下文，替换 `workbuddy.md` 中的摘要版（冲 WorkBuddy 专项 3,000 积分必须交真实导出）。
- [] 5. 把 `src/combo_finder.py` 中标 TODO 的入参字段按 `tools/list` 返回的 inputSchema 校正（如要提交可运行代码版本）。
- [] 6. 把本目录推送到自己的 GitHub 账号下，仓库设为 **Public 公开**（仓库名建议 `mcd-workbuddy-skill`）；推送前确认仓库里没有任何真实 Token（只有 `YOUR_MCP_TOKEN` 占位符）。
- [] 7. （保险起见）用官方仓库的原文件覆盖一遍 `CONTEST_DECLARATION.md`，确保与官方内容逐字一致（官方要求文件名及内容均不可改动）。
- [] 8. 去官方仓库按标准格式提交报名 Issue（标题与正文之间不要加多余换行、项目地址不要用 Markdown 链接格式，校验很严）：
- 标题：自定义报名标题
- 正文：`` / `项目名称：麦门省钱搭配助手（McSaver Combo）` / `项目地址：{你的公开仓库地址}` / `项目简介：{一句话简介}`
- [] 9. 提交后等系统在 Issue 下回复「报名成功」通知；若回复失败原因，按提示修改后重新提交 Issue。
- [] 10. 报名成功后留意官方仓库 `RANKING.md` 排行榜（Star 数 > 0 才进榜，前 100 名有奖）。

截止提醒：2026-10-25 23:59 前必须完成报名 Issue 提交，逾期无法参赛。
