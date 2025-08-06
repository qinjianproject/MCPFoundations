# 安装教程
`pip install uv`
`uv sync`


# 使用教程

## 0_MCP_client_server
最基础的MCP搭建流程：
功能：将天气查询功能（调用weather_api查询：https://www.weatherapi.com/）注册到MCP server中
使用方法：
1. `cd src/0_MCP_client_server`
2. 填写.env文件大模型API调用相关参数（openai格式）
3. 填写server.py文件中weather_url和weather_api
4. `uv run client.py server.py`



## 1_MCP_RAG
MCP + langchain + RAG
功能：将RAG作为功能注册到MCP server中，RAG用langchain实现
使用方法：
1. cd `src/1_MCP_RAG`
1. 从huggingface上下载任意embedding模型，填写.env文件中的EMBED_MODEL参数，例如下载qwen-embedding-0.6b模型（https://hf-mirror.com/Qwen/Qwen3-Embedding-0.6B）就填写"qwen-embedding-0.6b"
2. 填写.env文件大模型API调用相关参数（openai格式）
3. `uv run rag_client.py rag_server.py`


## 2_MCP_GraphRAG
MCP + GraphRAG
功能：将RAG作为功能注册到MCP server中，RAG用GraphRAG实现
1. `cd src\2_MCP_GraphRAG`
2. 构建GraphRAG知识库（项目中已经给出了示例"src/2_MCP_GraphRAG/doupocangqiong"）
（1） `mkdir -p rag_text/input`，用于保存待处理的文本文件。将待处理的文本或其他类型的文件放入input目录下。
（2）`graphrag init --root src/2_MCP_GraphRAG/rag_text/input`，初始化
（3）修改settings.yaml文件中的几个重要参数，通常而言只需要修改api_base，model，encoding_model
（4）填写src/2_MCP_GraphRAG/doupocangqiong/.env文件
3. 填写src/2_MCP_GraphRAG/.env文件大模型API调用相关参数（openai格式）
4. 修改server.py文件中的PROJECT_DIRECTORY参数
5. `uv run client.py server.py`



## 问题
如果直接运行存在问题，可以先把尝试单独测试server.py是否能正常运行，然后在排查问题。以0_MCP_client_server为例：
1. 修改代码
```python
if __name__ == "__main__":
    print(asyncio.run(query_weather("shenzhen")))
    # mcp.run(transport="stdio")
```
2. 运行`uv run server.py`看看是否能正常运行