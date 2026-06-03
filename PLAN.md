# 剧本杀 Agent 系统 — 项目计划

> 一个用于学习现代 Agent 工程的剧本杀系统：Agent 作为 DM 读取并演绎剧本，
> 支持多名真人玩家（群聊式交互），AI 玩家可选。
> 技术主线：**LangGraph 编排 + LangChain RAG + 跨厂商多 LLM + 本地嵌入向量库**。

---

## 1. 核心目标与定位

- **DM Agent**：读取结构化剧本，以上帝视角演绎剧情、分发线索、控制节奏、裁决检定。
- **玩家**：以"群聊"方式交互；MVP 阶段真人玩家通过 CLI 接入，支持多人；AI 玩家可插拔。
- **信息隔离**：每个参与者只能看到自己有权看到的内容（这是系统的安全边界）。
- **学习导向**：完整覆盖 LangGraph 状态机 / RAG / 多 LLM 路由 / human-in-the-loop。

---

## 2. 技术选型（已定稿）

| 维度 | 选型 | 说明 |
|------|------|------|
| 编排 | **LangGraph** | `StateGraph` 跑流程状态机；`checkpointer` 存档恢复；`interrupt()` 等真人输入 |
| 组件 | **LangChain** | `init_chat_model` 统一封装跨厂商模型、RAG 链、retriever、工具绑定 |
| RAG 框架 | **LangChain RAG 栈** | loaders + splitters + Chroma + retriever（含 SelfQueryRetriever），与 LangGraph 同生态 |
| 向量库 | **Chroma**（本地） | 零额外 API 费用，离线可跑，支持 `where` 元数据过滤 |
| 嵌入 | **本地 sentence-transformers** | 例：`bge-small-zh` / `bge-m3`（中文剧本友好） |
| LLM | **跨厂商混用** | Claude + OpenAI；按环节分档（见 §5） |
| 真人接入(MVP) | **CLI** | 对接 LangGraph `interrupt()`；后续可换 Web 不动核心 |

> 备选：若剧本 ingestion 变复杂，可引入 **LlamaIndex** 仅作索引层，检索结果喂给 LangGraph。
> 当前不引入，避免双框架增加学习负担。

---

## 3. 系统架构

```
        真人玩家(CLI) ──┐
                        │  (LangGraph interrupt 挂起/恢复)
        ┌───────────────▼────────────────────────────┐
        │            LangGraph StateGraph              │
        │   GameState · 节点 · 条件边 · checkpointer    │
        └───┬───────────────┬───────────────┬─────────┘
            │               │               │
       ┌────▼────┐    ┌──────▼──────┐  ┌─────▼─────┐
       │ DM 节点  │    │ 玩家节点(AI)  │  │ 工具:dice  │
       │ 上帝视角 │    │ 受限视角      │  └───────────┘
       └────┬────┘    └──────┬──────┘
            │ scoped RAG     │ scoped RAG
        ┌───▼────────────────▼───┐
        │   Chroma 向量库(本地)    │
        │  分块 + visibility 元数据 │
        └─────────────────────────┘
```

核心抽象：真人与 AI 玩家在引擎眼里都是"参与者"，区别只在消息来源
（真人来自 CLI 输入，AI 来自 LLM 调用）。统一后增删玩家、未来换 Web 不动核心逻辑。

---

## 4. RAG 子系统 ＝ 信息隔离

**关键洞察：RAG 的元数据过滤恰好就是剧本杀信息隔离的实现机制，两个需求合二为一。**

### 4.1 数据切分与元数据
剧本所有内容切分入 Chroma，每个分块携带元数据：
- `visibility`：`public` / `character:<id>` / `dm_only`
- `type`：`background` / `clue` / `character_profile` / `truth`
- `phase`：该内容在哪个阶段后才可见
- `clue_id`：线索唯一标识（用于动态揭示判断）

### 4.2 按参与者构建 scoped retriever
| 参与者 | 检索过滤器 |
|--------|-----------|
| DM | 默认无过滤（上帝视角，检索全部）；必要时按 `phase` / `type` 收窄上下文 |
| 玩家 X | `visibility ∈ {public, character:X}` 且 `phase <= current_phase` 且 `(clue_id is null OR clue_id ∈ revealed_clues)` |

**向量库静态、过滤器动态**：线索"已揭示集合"从 LangGraph 的 `GameState` 实时取，
查询时拼进 Chroma 的 `where` 过滤条件，从源头杜绝"偷看别人剧本"。
权限过滤必须由代码确定性生成，不能交给 LLM 自行决定；LLM 最多参与查询改写。

> **学习点**：本地 embedding、Chroma、metadata filtering，且带真实业务约束（隔离）。
> 可探索 `SelfQueryRetriever`，但只作为非权限字段的检索增强实验，不进入安全边界。

---

## 5. 多 LLM 注册表（跨厂商）

`get_llm(role)` 工厂 + `config.yaml`，按环节挑厂商/档位。换模型只改配置字符串
（`init_chat_model("anthropic:...")` / `("openai:...")`）。

| 环节 | role | 建议档位 | 厂商示例 | 理由 |
|------|------|---------|---------|------|
| DM 叙事/裁决 | `dm` | 最强 | Claude Opus | 演绎质量、防泄密、逻辑一致性最吃能力 |
| AI 玩家 | `player` | 中档 | GPT / Claude Sonnet | 多实例并发，控成本 |
| 上下文摘要 | `summarizer` | 轻量 | Claude Haiku / GPT-mini | 压缩历史，便宜快 |
| 发言调度 | `moderator` | 轻量 | Claude Haiku / GPT-mini | 判断"该谁说话"，高频小任务 |
| 嵌入 | `embedder` | 本地 | sentence-transformers | 与对话模型分开 |

> **学习点**：provider 路由 + 成本/能力权衡，工程化 Agent 的核心能力。

---

## 6. LangGraph 骨架

### 6.1 GameState（TypedDict）
- `thread_id` / `session_id`：一次剧本局的唯一标识，用于 checkpointer 恢复
- `phase`：当前阶段
- `public_events`：公开事件流（群聊消息、公开线索、系统广播、掷骰结果）
- `private_events`：私密事件流（DM→玩家私信、角色私有信息、未公开线索）
- `revealed_clues`：已揭示线索集合（驱动 RAG 动态过滤）
- `votes`：投票记录
- `participants`：玩家清单（真人/AI 标记）
- `current_speaker`：当前应发言参与者
- `pending_interrupts`：等待真人输入的挂起点
- `turn_count` / `phase_deadline`：节奏控制与超时判定
- `summaries`：阶段性摘要，避免上下文膨胀

### 6.2 节点与流程
```
setup(分发角色) → dm_narrate(开场) → introductions(自我介绍)
   → investigation(搜证) → discussion(讨论·自由群聊)
   → voting(投票) → reveal(公布真相/复盘)
```
- **条件边**控阶段切换（讨论是否充分 / 到时 / 玩家请求推进）。
- **`interrupt()`** 在"需真人发言"处挂起，等 CLI/controller 恢复。
  超时不放在 LangGraph 节点内部，而由 CLI/controller 计时后 resume 一个 `timeout` 事件，防止挂机卡死。
- **`checkpointer`** 自动存档，长局可中断恢复。
- **AI 发言时机**：MVP 用 **DM 点名**（状态机+DM 主导 cue 玩家）；后续升级"意愿打分"做更自然群聊。

---

## 7. 工具：骰子（Function Call）

```python
dice(sides: int, count: int = 1, reason: str = "") -> {
    "rolls": [int], "total": int, "reason": str
}
```
- 主要供 DM 在搜证/技能检定时调用，结果回灌 DM 决定叙事走向。
- 真人也可在群聊请求 DM 代掷，DM 调用后把结果播报到群聊。
- 后续可平滑扩展更多工具（发线索、记录投票等）。

---

## 8. 项目结构

```
playscript_agent/
  graph/
    state.py          # GameState(TypedDict)
    builder.py        # StateGraph：节点 + 条件边 + checkpointer
    nodes/            # setup / dm_narrate / player_turn / voting / reveal
  rag/
    ingest.py         # 剧本 → 切分 → 本地嵌入 → Chroma（写 visibility 元数据）
    retrievers.py     # 按参与者构建 scoped retriever
    filters.py        # 确定性生成 Chroma where 过滤条件（权限边界）
  llm/
    registry.py       # get_llm(role) 工厂
    config.yaml       # 各环节 → 厂商/模型映射
  agents/
    dm.py             # DM 链（上帝视角 + 防泄密 + 全量 RAG）
    player.py         # AI 玩家链（受限视角 + scoped RAG）
  guard/
    output.py         # DM/AI 输出防泄密校验
    policy.py         # visibility / phase / clue_id 权限策略
  tools/
    dice.py
  scripts/
    demo/             # 手写极简样本剧本（带 visibility 标注）
      meta.json · background.md · characters/ · clues.json · truth.json · dm_manual.json
  cli/
    client.py         # 真人接入，对接 LangGraph interrupt
  config/             # .env（API keys）· 模型与嵌入配置
  tests/
    test_rag_filters.py      # 越权检索测试
    test_output_guard.py     # 越权输出测试
```

---

## 9. 实施路线（融入学习节奏）

| 阶段 | 目标 | 学习重点 |
|------|------|---------|
| 0 | 剧本 schema + 极简 demo 剧本 + 权限测试骨架 | 数据契约 / visibility / phase / clue_id |
| 1 | LangGraph 骨架 + 单 LLM，跑通"开场→自我介绍→公布真相"，CLI 接 1 真人 | StateGraph / interrupt / 节点与边 |
| 2 | 确定性 scoped RAG：剧本本地嵌入入 Chroma，DM/玩家按权限检索 | embedding / Chroma / metadata filtering |
| 3 | 公开/私密事件流：private 通道、揭示线索、验证检索不串台 | event log / 信息隔离 / 测试 |
| 4 | 多 LLM：接 `get_llm(role)`，DM/玩家/摘要分别用 Claude/OpenAI 不同档 | provider 路由 / 成本权衡 |
| 5 | AI 玩家 + 骰子：player 节点 + DM 点名调度 + `dice` 工具 | 多 actor 协调 / tool calling |
| 6 | 完整流程 + 打磨：搜证/讨论/投票/复盘、摘要、防泄密校验、checkpointer 恢复 | 上下文管理 / 持久化 |

---

## 10. 关键技术难点

| 难点 | 应对 |
|------|------|
| 信息隔离 | 确定性 RAG scoped retriever + private 通道，从检索源头隔离 |
| DM 防泄密 | prompt 约束 + 输出 guard 校验（不泄 `dm_only` / 未揭示 `clue_id`） |
| 上下文膨胀 | 阶段性摘要（summarizer 角色）+ checkpointer |
| AI 发言时机 | MVP DM 点名 → 后续意愿打分 |
| 真人挂机 | CLI/controller 计时，超时 resume `timeout` 事件，跳过或 DM 催 |
| 剧本结构化 | 先定 schema，手写极简样本验证 |

---

## 11. 待确认 / 下一步

- [x] Python 环境约定：后续使用 `D:\anaconda\envs\playscript-agent` 专用环境
- [ ] 选定本地嵌入模型（中文剧本建议 `bge-m3` 或 `bge-small-zh`）
- [ ] 确定玩家用哪家厂商（GPT vs Claude Sonnet）
- [x] 先完成 **阶段 0**：剧本 schema、极简 demo、权限过滤测试
- [x] 完成 **阶段 1**：LangGraph 骨架 + interrupt/resume CLI demo，跑通"开场→自我介绍→公布真相"

> 参考：LangChain vs LlamaIndex RAG 框架对比（2025/2026）。本项目选 LangChain RAG 栈
> 以与 LangGraph 同生态；LlamaIndex 留作 ingestion 复杂化时的索引层备选。
