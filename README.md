# Inspiration Agent

一个基于 Streamlit 的短剧/漫剧灵感生成 Agent。

用户输入关键词、题材或 IP，再补充热点/风格关键词，应用会生成：

- 设定拆解
- 多个灵感设定候选
- 最优设定的简要剧本梗概
- 基于候选版本和修改意见的二次生成结果

## Features

- 首轮生成：输入主题和热点词，输出设定拆解、候选设定和梗概
- 二次生成：选择一个候选版本，输入修改意见，生成优化后的第二轮梗概
- Markdown / JSON 导出
- 支持模型接口调用
- 模型不可用时支持本地兜底结果

## Tech Stack

- Python
- Streamlit
- Requests

## Project Structure

```text
.
├── app.py
├── requirements.txt
├── .env.example
└── README.md
```

## Local Run

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure environment variables

复制 `.env.example` 为 `.env`，并填入可用配置。

推荐使用以下新接口配置：

```env
MODEL_AGENT_API_KEY=你的火山APIKey
MODEL_AGENT_BASE_URL=https://ark.cn-beijing.volces.com/api/v3/
MODEL_AGENT_MODEL_NAME=你的Endpoint_ID
```

兼容旧版 Agent Bot 配置：

```env
VOLCENGINE_AGENT_API_KEY=
VOLCENGINE_BOT_ID=
VOLCENGINE_AGENT_API_URL=https://open.feedcoopapi.com/agent_api/agent/chat/completion
```

### 3. Start the app

```bash
streamlit run app.py
```

默认访问地址：

```text
http://localhost:8501
```

## Streamlit Community Cloud Deployment

这个项目可以直接部署到 Streamlit Community Cloud。

### Deploy steps

1. 将项目推送到 GitHub 仓库
2. 打开 [Streamlit Community Cloud](https://share.streamlit.io/)
3. 使用 GitHub 账号登录
4. 选择仓库和分支
5. Main file path 填写 `app.py`
6. 在应用设置中配置 Secrets
7. 点击 Deploy

### Secrets example

在 Streamlit Cloud 的 Secrets 中填写：

```toml
MODEL_AGENT_API_KEY="你的火山APIKey"
MODEL_AGENT_BASE_URL="https://ark.cn-beijing.volces.com/api/v3/"
MODEL_AGENT_MODEL_NAME="你的Endpoint_ID"
VOLCENGINE_AGENT_API_KEY=""
VOLCENGINE_BOT_ID=""
VOLCENGINE_AGENT_API_URL="https://open.feedcoopapi.com/agent_api/agent/chat/completion"
```

说明：

- `.env` 不会自动上传到 Streamlit Cloud
- 必须把线上所需环境变量手动填写到 Secrets
- 如果 12 小时没有访问，应用可能进入休眠；访问链接后可手动唤醒

## Notes

- 当前页面展示的“设定拆解”由模型按固定输出协议生成
- 如果模型接口不可用，应用会自动回退到本地兜底结果
- 当前首轮生成协议固定输出 3 个候选设定

## Suggested Repo Name

推荐仓库名：

```text
inspiration-agent
```

如果你想强调“短剧灵感”，也可以用：

```text
short-drama-inspiration-agent
```

前者更短，也更贴合当前“灵感 Agent”的定位，建议优先使用。
