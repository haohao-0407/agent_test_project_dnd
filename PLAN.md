# DND Agent 系统 - 项目计划

> 目标：把当前“剧本杀 Agent 系统”的方向调整为一个可运行、可扩展的 DND Agent 系统。
> 优先实现 DND 核心玩法与 Web 体验：地图展示、角色卡、行动回合、骰子检定、战斗/探索流程。
> LLM 作为 DM，通过 function call 调用确定性工具完成骰子投掷、地图编辑、角色控制、规则查询和状态更新。

---

## 1. 核心定位

- **LLM DM**：负责叙事、场景描述、规则解释、NPC 行为、遭遇推进、玩家行动裁决。
- **工具驱动**：所有会改变游戏状态的操作必须通过 function call 完成，避免 LLM 直接“脑补”状态。
- **Web 优先**：MVP 从 CLI 转向 Web，首屏就是跑团桌面，包含地图、角色卡、聊天/行动记录、骰子结果。
- **DND 功能优先**：先实现通用 DND 跑团能力，再考虑剧情模组、长期战役、多人同步和高级 AI 玩家。
- **规则可控**：核心规则由结构化规则、工具和测试约束实现；LLM 负责解释和裁决建议，但最终状态由代码写入。

---

## 2. 产品形态

### 2.1 Web 跑团桌面

首版 Web 页面包含四个主要区域：

- **地图区**：网格地图、地形、障碍物、角色/NPC token、可见范围、坐标。
- **角色卡区**：玩家角色属性、生命值、护甲等级、技能、豁免、法术位、物品、状态效果。
- **DM/聊天区**：玩家输入行动，DM 回复叙事和裁决；显示公开事件、私密提示、系统事件。
- **工具/日志区**：骰子结果、行动历史、回合顺序、状态变更、地图变更记录。

### 2.2 基础玩法范围

MVP 先覆盖：

- 角色创建/导入：属性、熟练项、生命值、护甲、技能、武器、法术。
- 探索模式：移动、观察、调查、交互、检定。
- 战斗模式：先攻、回合顺序、移动、攻击、伤害、豁免、状态效果、死亡豁免。
- 地图操作：创建房间、放置 token、移动 token、添加地形/障碍、标记可见信息。
- 骰子系统：d20 检定、优势/劣势、伤害骰、多骰表达式、公开/私密投掷。

---

## 3. 系统架构

```text
Web Client
  - 地图画布 / 角色卡 / 聊天面板 / 回合面板
        |
        v
API / Session Controller
  - 会话管理
  - WebSocket/SSE 事件推送
  - 用户输入归一化
        |
        v
LangGraph DND StateGraph
  - DM 节点
  - 玩家行动节点
  - 工具执行节点
  - 规则裁决节点
  - 回合/场景切换条件边
        |
        v
Deterministic Tools
  - roll_dice
  - update_character
  - move_token
  - edit_map
  - resolve_attack
  - apply_condition
  - query_rules
        |
        v
State Stores
  - GameState
  - CharacterState
  - MapState
  - EventLog
  - Rule/Module RAG
```

关键原则：

- LLM 只能提出叙事、意图和工具调用；角色 HP、坐标、状态、背包、地图等事实由工具更新。
- Web 客户端只展示后端事件流，不自行推断核心规则结果。
- 每次状态变更写入事件日志，支持回放、撤销和调试。

---

## 4. 核心状态模型

### 4.1 GameState

- `session_id`：战役/单次跑团唯一标识。
- `mode`：`exploration` / `combat` / `downtime` / `scene_setup`。
- `scene_id`：当前场景。
- `current_turn`：当前行动角色。
- `initiative_order`：战斗先攻顺序。
- `round_number`：战斗轮数。
- `public_events`：公开事件。
- `private_events`：DM 私密记录和个人提示。
- `pending_actions`：等待玩家确认或工具执行的动作。
- `summaries`：场景摘要、长期记忆摘要。

### 4.2 CharacterState

- `id` / `name` / `type`：玩家角色、NPC、怪物。
- `level` / `class` / `race` / `background`。
- `attributes`：STR / DEX / CON / INT / WIS / CHA。
- `proficiency_bonus`。
- `skills` / `saving_throws`。
- `hp_current` / `hp_max` / `temporary_hp`。
- `armor_class` / `speed`。
- `inventory` / `equipment`。
- `spells` / `spell_slots`。
- `conditions`：倒地、昏迷、中毒、束缚等。
- `position`：地图坐标、朝向、所在图层。

### 4.3 MapState

- `map_id` / `scene_id`。
- `grid_size`：方格尺寸。
- `width` / `height`。
- `terrain`：地形层。
- `walls` / `doors` / `obstacles`。
- `tokens`：角色、NPC、怪物、物件。
- `fog_of_war`：战争迷雾。
- `annotations`：DM 标记、公开标记、临时效果范围。

---

## 5. Function Call 工具设计

所有工具应返回结构化结果，并写入事件日志。

### 5.1 骰子工具

```python
roll_dice(
    expression: str,
    reason: str,
    roller_id: str | None = None,
    visibility: Literal["public", "dm_only", "private"] = "public",
    advantage: Literal["normal", "advantage", "disadvantage"] = "normal"
) -> DiceResult
```

支持示例：

- `1d20+5`
- `2d6+3`
- `1d20kh1+4` 或通过 `advantage` 参数处理优势/劣势。

### 5.2 角色工具

- `create_character`
- `update_character`
- `apply_damage`
- `apply_healing`
- `apply_condition`
- `remove_condition`
- `spend_resource`
- `restore_resource`

要求：

- HP、法术位、状态效果等必须由工具修改。
- 每次修改输出前后差异，供 Web 日志展示。

### 5.3 地图工具

- `create_map`
- `edit_map_tile`
- `place_token`
- `move_token`
- `remove_token`
- `set_visibility`
- `add_annotation`
- `measure_distance`

要求：

- token 移动要校验速度、障碍、地形代价。
- 地图编辑区分 DM 私有层和玩家可见层。

### 5.4 规则/裁决工具

- `query_rules`
- `resolve_skill_check`
- `resolve_saving_throw`
- `resolve_attack`
- `resolve_area_effect`
- `start_combat`
- `advance_turn`
- `end_combat`

要求：

- DM 可以解释规则，但关键计算使用工具完成。
- 规则引用要可追踪，避免 LLM 混用版本或自造规则。

---

## 6. LLM 与 Agent 编排

### 6.1 LangGraph 节点

- `receive_player_input`：接收玩家行动意图。
- `dm_interpret`：DM 理解行动、判断是否需要工具。
- `tool_execute`：执行骰子、地图、角色、规则工具。
- `dm_narrate`：根据工具结果生成叙事反馈。
- `state_summarize`：压缩长期上下文。
- `human_confirm`：高风险操作前请求玩家或 DM 确认。

### 6.2 DM 行为边界

DM 可以：

- 描述场景和 NPC。
- 提出检定。
- 调用骰子、规则、地图、角色工具。
- 根据工具结果裁决叙事后果。
- 生成战斗和探索建议。

DM 不可以：

- 直接修改角色数值。
- 直接移动 token。
- 直接宣称骰子结果。
- 忽略工具返回的事实状态。
- 泄露 DM 私有地图层、怪物数据或未发现线索。

---

## 7. RAG 与规则资料

RAG 不再围绕剧本杀线索隔离，而是服务于 DND 规则、模组和战役记忆。

### 7.1 资料类型

- `rules_core`：核心规则摘要。
- `rules_spells`：法术规则。
- `rules_items`：物品和装备。
- `monster_blocks`：怪物数据。
- `module_public`：玩家已知模组内容。
- `module_dm_only`：DM 私有模组内容。
- `campaign_memory`：长期战役事件和人物关系。

### 7.2 权限边界

- 玩家角色只能检索公开规则、自己角色卡、已公开战役信息。
- DM 可以检索规则、怪物、模组私有内容和完整事件日志。
- 地图私有层、未触发遭遇、隐藏陷阱和怪物数据必须保持 DM only。

---

## 8. Web UI 计划

### 8.1 首屏布局

```text
+---------------------------------------------------------------+
| Top Bar: Session / Mode / Round / Current Turn / Actions       |
+-----------------------------+---------------------------------+
| Map                         | Character Sheet                 |
| - grid                      | - stats / HP / AC               |
| - tokens                    | - skills / saves                |
| - terrain                   | - inventory / spells            |
| - fog                       | - conditions                    |
+-----------------------------+---------------------------------+
| Chat / DM Narration         | Dice / Event Log / Initiative   |
+---------------------------------------------------------------+
```

### 8.2 必备交互

- 点击 token 查看角色/NPC 简要信息。
- 拖拽 token 发起移动请求。
- 点击地图格子添加标记或选择目标。
- 角色卡可折叠显示技能、攻击、法术、物品。
- 聊天输入支持自然语言行动。
- 骰子日志可展开查看公式、每颗骰子、修正值和原因。
- DM 模式可编辑地图和隐藏层。

### 8.3 前后端工程化方案

当前 Web MVP 已经验证了地图、角色卡、聊天、骰子和 token 移动的基本交互，但标准库 HTTP server + 静态三件套会在后续变得难维护。正式路线改为：

- **后端：FastAPI + Uvicorn**
  - 继续留在 Python 生态，方便接 LangGraph、RAG、LLM registry 和 function call tools。
  - 用 `APIRouter` 拆分 `sessions` / `maps` / `characters` / `dice` / `chat` / `rules`。
  - 用 Pydantic schema 约束 `GameState`、`MapState`、`CharacterState`、`DiceResult`、`EventLog`。
  - 用 WebSocket 推送地图、骰子、聊天、角色状态、DM 流式输出和系统事件。

- **前端：Vite + React + TypeScript**
  - 把当前 DOM/JS 单页拆成组件：`MapView`、`TokenLayer`、`CharacterSheet`、`EventLog`、`DicePanel`、`ChatPanel`。
  - 用 TypeScript 类型对齐后端 Pydantic schema。
  - 用统一 API client 管理 REST 和 WebSocket。
  - 初期地图继续用 DOM/CSS Grid；地图复杂后再切 PixiJS 或 Konva。

- **迁移策略**
  - 第一步只替换后端：把当前 `/api/state`、`/api/dice`、`/api/chat`、`/api/token/move` 搬到 FastAPI，前端暂时不变。
  - 第二步拆前端：引入 React/Vite 后复刻现有 UI，确保行为一致。
  - 第三步接实时事件：把轮询/刷新式状态替换为 WebSocket event stream。
  - 第四步接 LangGraph DM：`chat` endpoint 不再直接生成占位回复，而是进入 DM graph，由 LLM 通过工具更新状态。

---

## 9. 项目结构目标

当前代码还保留 `playscript_agent` 命名；后续代码阶段优先在该包内新增成熟 Web 后端，再按需要迁移或新增 `dnd_agent` 包。目标结构如下：

```text
playscript_agent/
  api/
    app.py                  # FastAPI app factory / ASGI entry
    routers/
      sessions.py           # 会话创建、快照、恢复
      maps.py               # 地图读取、编辑、token 移动
      characters.py         # 角色卡、HP、资源、状态
      dice.py               # 骰子表达式、优势/劣势、公开/私密投掷
      chat.py               # 玩家输入、DM 回复、流式事件入口
      rules.py              # DND 规则 RAG 查询
    schemas/
      session.py
      map.py
      character.py
      event.py
      dice.py
    services/
      game_state.py         # 单一事实源，后续可替换为持久化存储
      websocket_hub.py      # 多客户端事件广播
      dice_service.py
      map_service.py
      character_service.py
      dm_service.py         # LangGraph/LLM DM 入口
  graph/
    state.py
    builder.py
    nodes/
      dm.py
      player_input.py
      tools.py
      combat.py
      summarize.py
  tools/
    dice.py
    character.py
    map.py
    rules.py
    combat.py
  rules/
    schema.py
    loader.py
    retriever.py
  models/
    character.py
    map.py
    event.py
    session.py
  data/
    demo_campaign/
      characters/
      maps/
      encounters/
      rules/
  tests/
    test_dice.py
    test_character_state.py
    test_map_tools.py
    test_combat_flow.py
    test_dm_tool_boundaries.py

web/
  package.json
  vite.config.ts
  src/
    main.tsx
    api/
      client.ts             # REST + WebSocket client
      types.ts              # 与后端 schema 对齐的 TS 类型
    state/
      sessionStore.ts       # 当前会话、地图、角色、事件状态
    components/
      tabletop/
        MapView.tsx
        TokenLayer.tsx
        CharacterSheet.tsx
        EventLog.tsx
        DicePanel.tsx
        ChatPanel.tsx
    styles/
      app.css
```

---

## 10. 实施路线

| 阶段 | 目标 | 验收标准 |
|------|------|----------|
| 0 | 重定向项目计划和数据模型 | PLAN.md 明确 DND 方向、状态模型、工具边界、Web MVP |
| 1 | DND 核心 schema | CharacterState、MapState、GameState、EventLog schema 和基础测试 |
| 2 | 骰子与规则工具 | roll_dice、技能检定、豁免、攻击、伤害工具可独立测试 |
| 3 | 地图与 token 工具 | 创建地图、放置/移动 token、障碍校验、可见层管理 |
| 4 | 角色卡与资源系统 | HP、AC、技能、物品、法术位、状态效果的增删改查 |
| 5 | LangGraph DM MVP | 玩家输入 -> DM 判断 -> 工具调用 -> 叙事反馈闭环 |
| 6 | FastAPI 后端迁移 | 当前 Web API 从标准库 server 迁到 FastAPI routers，前端行为保持一致 |
| 7 | React/Vite 前端迁移 | 复刻现有 Web MVP，拆出地图、角色卡、聊天、骰子组件 |
| 8 | WebSocket 事件流 | 地图移动、骰子、聊天、角色状态通过事件广播同步 |
| 9 | 战斗流程 | 先攻、回合推进、攻击、伤害、状态、死亡豁免 |
| 10 | RAG 规则/模组资料 | DM 可查规则和模组，玩家权限受限 |
| 11 | 多人和长期战役 | 多玩家会话、存档恢复、战役摘要、权限和私密消息 |

---

## 11. 测试重点

- 骰子表达式解析和优势/劣势结果正确。
- LLM 不能绕过工具直接改状态。
- 地图移动遵守速度、障碍和地形代价。
- 战斗回合顺序稳定，不能跳过或重复行动。
- 角色 HP、临时 HP、死亡豁免和状态效果边界正确。
- DM only 信息不会出现在玩家可见事件和 RAG 结果中。
- Web 事件日志能完整回放关键状态变化。

---

## 12. 关键风险

| 风险 | 应对 |
|------|------|
| LLM 自造规则或结果 | 状态变更全部工具化，规则查询可追踪 |
| DND 规则范围过大 | MVP 只实现常用 d20、攻击、伤害、状态、移动和先攻 |
| 地图编辑复杂度高 | 先做方格地图和 token 层，再扩展光照、视野、复杂地形 |
| Web 与 Agent 状态不同步 | 后端事件流作为唯一事实源，前端只渲染事件和快照 |
| 多人实时协作复杂 | 单会话单玩家/DM MVP 先跑通，再加 WebSocket 多人同步 |
| 版权/规则资料边界 | 优先使用自定义摘要、SRD/开放资料或用户提供资料 |

---

## 13. 下一步

- [x] 将计划从剧本杀 Agent 系统调整为 DND Agent 系统。
- [ ] 确定 DND MVP 规则范围：5e 风格、简化 5e、自定义轻规则。
- [ ] 设计 CharacterState / MapState / GameState schema。
- [ ] 设计 function call 工具接口和事件日志格式。
- [x] 决定 Web 技术栈：FastAPI + Uvicorn 后端，Vite + React + TypeScript 前端。
- [ ] 迁移当前标准库 Web API 到 FastAPI，保留现有前端行为。
- [ ] 迁移当前静态前端到 React/Vite 组件化结构。
- [ ] 开始实现阶段 1：DND 核心 schema 与测试。

> 当前要求：只修改 PLAN.md，不写代码。代码迁移、目录重命名和 Web 实现留到后续阶段。
