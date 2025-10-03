# Deepseek-2api 🤖

一个基于 `Nginx` + `FastAPI` 构建的、支持粘性会话的高性能 `Deepseek` 网页版聊天本地代理。本项目完整模拟了官方网页端的**完整认证链**，包括 `Proof-of-Work` 挑战和 `Cookie` 验证。

[![Docker](https://img.shields.io/badge/Deploy-Docker-blue?style=for-the-badge&logo=docker)](https://github.com/lzA6/Deepseek-2api)
[![Hugging Face](https://img.shields.io/badge/Deploy-Hugging%20Face-yellow?style=for-the-badge&logo=huggingface)](https://huggingface.co/spaces/lzA6/Deepseek-2api)

---

## ✨ 项目亮点

- **🚀 生产级架构**: 采用 `Nginx` + `FastAPI` 的黄金组合，`Nginx` 负责负载均衡和粘性会话，`FastAPI` 应用负责核心业务逻辑，稳定高效。
- **🔐 完整认证模拟**: 完整复现了 `Deepseek` 网页端的**双重认证机制**，包括计算密集型的 `Proof-of-Work (PoW)` 挑战和必需的 `Cookie` 验证，确保请求与真实浏览器行为一致。
- **🌊 精准流式解析**: 实现了对 `Deepseek` 定制的 `JSON Patch-like` SSE 数据流的精确解析，将复杂的增量数据转换为标准的 OpenAI `chat.completion.chunk` 格式。
- **📦 一键本地部署**: 提供优化的 `Docker` 部署方案，让你在几分钟内拥有一个私有、稳定、可靠的本地 `Deepseek` API。
- **🔑 安全可靠**: 所有敏感信息均通过 `.env` 文件配置，代码与配置分离，同时支持设置 `API_MASTER_KEY` 保护你的服务。

## ⚔️ 技术差异深度剖析

本项目在设计上，汲取了 `Qwen-2api` 和 `Ernie-2api` 的精华，并针对 `Deepseek` 更复杂的验证方式进行了深度定制。

| 特性 | **Deepseek-2api (本项目)** | `lzA6/Qwen-2api` | `lzA6/Ernie-2api` |
| :--- | :--- | :--- | :--- |
| **核心认证** | **`Token` + `Cookie` 双重验证** | `Authorization` Bearer Token | Cookie + acs-token + sign |
| **前置操作** | **PoW 挑战 (服务端计算)** | 无 | 获取动态 `sign` |
| **复杂性** | **极高** (需逆向 PoW 算法并维持 Cookie) | 中等 | 较高 (需处理多项动态参数) |
| **流式格式** | **JSON Patch-like 增量** | 累积式 JSON | 简单文本增量 |
| **解析难度** | **高** (需解析复杂结构) | 中等 (需处理累积内容) | 低 (直接获取增量) |

**结论**: `Deepseek-2api` 的逆向工程难度是三者中最高的，它不仅引入了 PoW 机制，还强制要求请求中携带有效的 `Cookie`，这对代理服务的模拟程度提出了极高的要求。

---

## 📸 抓包教程 (独家 - Token & Cookie)

为了让项目正常工作，我们需要从浏览器中获取两个关键信息：`Authorization` 和 `Cookie`。

1.  **打开开发者工具**
    *   在 `Chrome` 或 `Edge` 浏览器中访问 [chat.deepseek.com](https://chat.deepseek.com/) 并登录。
    *   按下 `F12` 键，打开开发者工具，并切换到 **“网络 (Network)”** 选项卡。

2.  **发送一条消息**
    *   在聊天框中随便输入点什么，比如“你好”，然后发送。

3.  **找到 `completion` 请求**
    *   在网络请求列表中，找到一个名为 `completion` 的请求，点击它。

4.  **复制 `Authorization` 和 `Cookie`**
    *   在右侧弹出的窗口中，向下滚动到 **“请求标头 (Request Headers)”** 部分。
    *   找到 `authorization` 一项，**完整复制**它的值 (以 `Bearer ` 开头)。
    *   紧接着，找到 `cookie` 这一项，**完整复制**它后面那一长串字符串。
    *   **提示**: 这两项通常在同一个区域，很容易一起找到。

    ![抓包教程](https://github.com/lzA6/Deepseek-2api/raw/main/assets/capture_tutorial.png)
    *(注意：上图仅展示了 `authorization` 的位置，请在该位置附近寻找 `cookie` 并一并复制。)*

5.  **填入配置文件**
    *   将复制的 `Authorization` 字符串粘贴到你的 `.env` 文件的 `DEEPSEEK_AUTHORIZATION_TOKEN` 字段中。
    *   将复制的 `Cookie` 字符串粘贴到你的 `.env` 文件的 `DEEPSEEK_COOKIE` 字段中。

---

## 🚀 快速开始

### 本地 Docker 部署 (强烈推荐)

这是最稳定、最可靠的部署方式，可以避免因云平台 IP 被屏蔽而导致的问题。

**前置要求**: `Docker` 和 `docker-compose`

1.  **克隆项目**
    ```bash
    git clone https://github.com/lzA6/Deepseek-2api.git
    cd Deepseek-2api
    ```

2.  **创建并编辑 `.env` 文件**
    ```bash
    cp .env.example .env
    ```
    使用编辑器打开 `.env` 文件，填入以下三项信息：
    *   `API_MASTER_KEY`: 你自定义的API密钥，用于保护服务。
    *   `DEEPSEEK_AUTHORIZATION_TOKEN`: 你刚刚获取的 `Authorization` 值。
    *   `DEEPSEEK_COOKIE`: 你刚刚获取的 `Cookie` 值。

3.  **启动服务**
    ```bash
    docker-compose up -d
    ```

4.  **测试**
    服务将在 `http://localhost:8083` 上可用。
    ```bash
    curl -X POST http://localhost:8083/v1/chat/completions \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer your_super_secret_key" \
    -d '{
        "model": "deepseek-chat",
        "messages": [
            {"role": "user", "content": "你好，你是谁？"}
        ],
        "stream": true
    }'
    ```

### Hugging Face Spaces 部署

⚠️ **重要部署警告** ⚠️

**不推荐**使用 Hugging Face 等免费云平台进行部署。因为 Deepseek 的服务器很可能会因为安全策略而**屏蔽这些平台的服务器 IP 地址**，导致您遇到 `403 Forbidden` 错误，即使您的配置完全正确。

如果您仍想尝试，请按以下步骤操作：

1.  点击上方 "Deploy to Hugging Face" 按钮 `Duplicate` 本项目。
2.  在创建页面，将可见性 (Visibility) 设置为 **Private**。
3.  部署完成后，进入 "Settings" -> "Secrets" 页面，添加以下**三个** `Secret`：
    *   `API_MASTER_KEY`: 你的自定义 API 密钥。
    *   `DEEPSEEK_AUTHORIZATION_TOKEN`: 你抓取的 `Bearer Token`。
    *   `DEEPSEEK_COOKIE`: 你抓取的 `Cookie`。
4.  服务会自动重启。如果遇到 `403` 错误，请参考下方的“常见问题排查”。

## 💡 常见问题排查 (Troubleshooting)

#### Q: 我遇到了 `403 Forbidden` 错误，怎么办？

这是最常见的问题，请按以下顺序排查：

1.  **凭证过期 (最常见)**: `Token` 和 `Cookie` 的有效期可能很短（数小时或一天）。请**重新抓取最新**的凭证，并更新到你的 `.env` 文件或 Hugging Face Secrets 中，然后重启服务。**90% 的问题都可以通过这个方法解决。**

2.  **IP 被屏蔽**: 如果你在 Hugging Face 等云平台部署时遇到此问题，但在**本地电脑上测试成功**，则 100% 是云平台的 IP 被屏蔽了。请切换到本地部署或使用 IP 地址干净的 VPS 服务器。

3.  **配置错误**: 请仔细检查 `.env` 文件或 Secrets 中的内容，确保复制时**完全、没有遗漏或多余的字符**，特别是 `Bearer ` 前缀和 `Cookie` 的分号。

## 📝 API 兼容性

本项目兼容 OpenAI 的 `/v1/chat/completions` 和 `/v1/models` 接口，可以无缝接入任何支持 OpenAI API 格式的客户端。
