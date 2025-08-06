# MCP 示例项目教程

本项目展示了如何使用 MCP 构建多种能力集成的应用模块，支持包括 RAG、LangChain、GraphRAG 等模块的快速注册与调用。

## 安装方法

确保已安装 `pip`，然后运行以下命令：

```bash
pip install uv
uv sync
```

## 使用教程
### 📁 0_MCP_client_server

**功能**：将天气查询能力注册到 MCP server 中（使用 weatherapi）

**使用步骤**：
1. 进入项目目录：

    ```bash
    cd src/0_MCP_client_server
    ```

2. 配置 `.env` 文件，填写大模型 API 调用参数（支持 OpenAI 格式）。

3. 编辑 `server.py` 文件，补充 `weather_url` 与 `weather_api`。

4. 运行客户端与服务端：

    ```bash
    uv run client.py server.py
    ```

### 📁 1_MCP_RAG
**功能**：将基于 LangChain 实现的 RAG（检索增强生成）能力注册到 MCP server 中。

**使用步骤**：
1. 进入目录：
    ```bash
    cd src/1_MCP_RAG
    ```

2. 下载 `HuggingFace` 上的 `embedding` 模型，并填写 `.env` 文件中的 `EMBED_MODEL` 参数。

    例如使用 qwen-embedding-0.6b，则填入：

    ```ini
    EMBED_MODEL=qwen-embedding-0.6b
    ```

3. 配置 `.env` 文件的大模型 API 参数（OpenAI 格式）。

4. 启动服务：
    
    ```bash
    uv run rag_client.py rag_server.py
    ```

### 📁 2_MCP_GraphRAG
**功能**：将 GraphRAG 实现的 RAG 能力注册到 MCP server 中。

**使用步骤**：
1. 进入目录：

    ```bash
    cd src/2_MCP_GraphRAG
    ```

2. 构建 GraphRAG 知识库（已提供示例项目：src/2_MCP_GraphRAG/doupocangqiong）：

    - 创建输入目录，并将待处理的文本或文档放入该目录。

        ```bash
        mkdir -p rag_text/input
        ```
    

    - 初始化项目：

        ```bash
        graphrag init --root src/2_MCP_GraphRAG/rag_text/input
        ```


    - 编辑 `settings.yaml` 文件中的核心参数：

        ```ini
        api_base=
        model=
        encoding_model=
        ```

    - 填写 `src/2_MCP_GraphRAG/doupocangqiong/.env` 文件。

3. 配置 `src/2_MCP_GraphRAG/.env` 文件中大模型 API 参数（OpenAI 格式）。

4. 编辑 `server.py` 文件，确保设置正确的 `PROJECT_DIRECTORY` 路径。

5. 启动服务：

    ```bash
    uv run client.py server.py
    ```

### 常见问题排查

若运行过程中遇到问题，建议先单独测试 server.py 是否可正常运行。以 0_MCP_client_server 为例：

✅ 测试示例

1. 修改 server.py：

    ```python
    if __name__ == "__main__":
        print(asyncio.run(query_weather("shenzhen")))
        # mcp.run(transport="stdio") 
    ```

2. 单独运行 server：

    ```bash
    uv run server.py
    ```
