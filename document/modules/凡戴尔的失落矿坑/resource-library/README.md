# 凡戴尔的失落矿坑资源库

这套资源用于本项目的跑团应用，提供原创探索背景、战斗底图、遭遇地图 JSON 和 DM 检索清单。它是兼容资源，不复制官方地图、朗读文本、房间原文或官方美术。

## 内容

- 探索场景：88 个，登记在 `../scenes.json`
- 战斗场景：52 个，地图在 `../maps/`
- 探索背景：`../pictures/Player/exploration/`
- 战斗底图：`../pictures/DM/battle/`
- AI 重绘提示词：`image-prompts.json`

## 使用建议

1. 应用读取 `scenes.json` 后，开场仍从 `triboar-trail-road` 进入。
2. 每个探索场景都带有 `battleSceneId` / `combatSceneId`，为空时表示主要是社交、线索、陷阱或过渡场景。
3. 当前 PNG 是程序化原创草图，适合先跑通流程；需要更精美图片时，用 `image-prompts.json` 中对应提示词重绘后替换同名文件。
4. 地图是抽象战术布局，不是官方地图复刻；如要贴合你桌上的版本，可在地图编辑器里微调墙、门、障碍和网格。
