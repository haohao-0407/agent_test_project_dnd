# Python 环境约定

本项目后续统一使用 `D:\anaconda` 下的项目专用 conda 环境：

```text
D:\anaconda\envs\playscript-agent
```

推荐解释器：

```text
D:\anaconda\envs\playscript-agent\python.exe
```

建议在运行项目命令前先确认当前解释器来自该目录：

```powershell
python -c "import sys; print(sys.executable)"
```

后续依赖安装、测试、LangGraph/RAG 相关命令都以这个专用环境为准，避免污染 Anaconda base 环境。

激活方式：

```powershell
D:\anaconda\Scripts\conda.exe activate playscript-agent
```

也可以不激活，直接使用完整解释器路径运行：

```powershell
D:\anaconda\envs\playscript-agent\python.exe -m unittest discover -s tests
```

阶段 1 CLI demo：

```powershell
D:\anaconda\envs\playscript-agent\python.exe -m playscript_agent.cli.client
```

非交互 smoke test：

```powershell
D:\anaconda\envs\playscript-agent\python.exe -m playscript_agent.cli.client --auto-intro "我是林安，今晚我会配合调查。"
```

阶段 2 scoped RAG demo：

```powershell
D:\anaconda\envs\playscript-agent\python.exe -m playscript_agent.cli.rag_demo --query "怀表 蓝色 油彩"
```

默认使用快速 hash embedding，只用于本地 smoke test，不下载模型。真实本地 embedding 可加
`--real-embedding`，默认模型为 `BAAI/bge-small-zh-v1.5`：

```powershell
D:\anaconda\envs\playscript-agent\python.exe -m playscript_agent.cli.rag_demo --real-embedding --query "怀表 蓝色 油彩"
```

`SentenceTransformerEmbeddingModel` 会自动把 Hugging Face / Transformers / Xet 缓存放到项目 `.cache`
目录，并优先 `local_files_only=True` 从缓存加载；缓存不存在时才联网下载。它还会设置
`HF_HUB_DISABLE_SYMLINKS=1`、`HF_HUB_DISABLE_XET=1` 和 `HF_HUB_DISABLE_PROGRESS_BARS=1`，
避免 Windows 下 symlink/Xet 缓存造成权限错误，并减少“Loading weights”进度条带来的误解。
真实 embedding 的 Chroma collection 名称为 `playscript_chunks_bge_small_zh_v1_5`，不会和 hash
smoke test 的 32 维 collection 混用。

如果 Hugging Face 下载限速，可在 `.env` 中配置：

```powershell
HF_TOKEN="你的 Hugging Face token"
```

DM 全量视角：

```powershell
D:\anaconda\envs\playscript-agent\python.exe -m playscript_agent.cli.rag_demo --dm --query "凶手 真相"
```

## 当前检测结果

- Python: `3.11.15` (`D:\anaconda\envs\playscript-agent\python.exe`)
- conda: `23.7.4`
- `pip check`: No broken requirements found
- 项目阶段 0 测试：`D:\anaconda\envs\playscript-agent\python.exe -m unittest discover -s tests` 通过，9 个测试 OK
- Chroma 显式 embedding smoke test 通过

已安装关键包：

| 包 | 版本 |
|---|---|
| `langgraph` | `1.2.4` |
| `langchain` | `1.3.4` |
| `langchain-core` | `1.4.0` |
| `langchain-community` | `0.4.2` |
| `langchain-chroma` | `1.1.0` |
| `chromadb` | `1.5.9` |
| `sentence-transformers` | `5.5.1` |
| `transformers` | `5.9.0` |
| `torch` | `2.12.0` |
| `langchain-openai` | `1.2.2` |
| `langchain-anthropic` | `1.4.4` |
| `openai` | `2.40.0` |
| `anthropic` | `0.105.2` |
| `python-dotenv` | `1.2.2` |
| `pyyaml` | `6.0.3` |
| `pytest` | `9.0.3` |
| `numpy` | `2.4.6` |
| `pydantic` | `2.13.4` |

## Hugging Face 缓存

直接导入 `transformers` 时，默认 Hugging Face 缓存目录提示不可写：
`C:\Users\shenc\.cache\huggingface\hub`。

建议后续在项目命令中把缓存放到工作区内：

```powershell
$env:HF_HOME="D:\agent_project\.cache\huggingface"
$env:TRANSFORMERS_CACHE="D:\agent_project\.cache\huggingface\transformers"
```

用上述缓存设置重新导入 `transformers` 已验证可用。

## Chroma 缓存

Chroma 默认 embedding 会使用 `Path.home()\.cache\chroma` 下载 ONNX 模型。当前默认 home 指向的
`C:\Users\shenc` 缓存路径不可写；后续如果使用 Chroma 默认 embedding，建议把 `USERPROFILE` 临时指到项目缓存：

```powershell
$env:USERPROFILE="D:\agent_project\.cache\home"
```

本项目计划使用 `sentence-transformers` 作为本地 embedding，所以正常 RAG 实现不需要依赖 Chroma 默认 ONNX embedding。

## API Key 配置

本地 API key 和第三方 API 入口放在项目根目录 `.env`，该文件已加入忽略列表，不应提交或共享。

```powershell
OPENAI_API_KEY="你的 OpenAI key"
OPENAI_BASE_URL=""
ANTHROPIC_API_KEY="你的 Anthropic key"
ANTHROPIC_BASE_URL=""
LANGSMITH_TRACING=false
LANGSMITH_PROJECT=playscript-agent
```

可参考 `.env.example`。`playscript_agent.llm.registry.get_llm()` 会自动加载 `.env`。

模型、provider、API 入口在 `config/llm.yaml` 中配置。OpenAI-compatible 第三方服务可以继续走
`openai:<model>`，同时把 `base_url_env` 指向对应环境变量，例如：

```yaml
models:
  player:
    model: "openai:deepseek-chat"
    api_key_env: DEEPSEEK_API_KEY
    base_url_env: DEEPSEEK_BASE_URL
    temperature: 0.8
```

`.env` 中对应：

```powershell
DEEPSEEK_API_KEY="你的 DeepSeek key"
DEEPSEEK_BASE_URL="https://api.deepseek.com"
```

如果接入私有网关，也可以直接配置自己的 env 名称：

```yaml
models:
  dm:
    model: "${DM_MODEL}"
    api_key_env: DM_API_KEY
    base_url_env: DM_BASE_URL
```
