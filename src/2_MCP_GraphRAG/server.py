from pathlib import Path
import pandas as pd
import graphrag.api as api
from graphrag.config.load_config import load_config
from mcp.server.fastmcp import FastMCP
import asyncio

#初始化MCP服务器
mcp = FastMCP("rag_ml")
USER_AGENT ="rag_ML-app/1.0"

@mcp.tool()
async def rag_ml(query: str)->str:
    """
    为斗破苍穹小说提供相关的知识补充[graphrag]
    :param query：用户提出的具体问题
    :return：最终获得的答案
    """
    PROJECT_DIRECTORY = r"src\2_MCP_GraphRAG\doupocangqiong"
    graphrag_config = load_config(Path(PROJECT_DIRECTORY))
    # 加载实体
    entities=pd.read_parquet(f"{PROJECT_DIRECTORY}/output/entities.parquet")
    print(entities)
    # 加载社区
    communities=pd.read_parquet(f"{PROJECT_DIRECTORY}/output/communities.parquet")
    print(communities)
    # 加载社区报告
    community_reports=pd.read_parquet(f"{PROJECT_DIRECTORY}/output/community_reports.parquet")
    print(community_reports)
    # 进行全局搜索
    response,context=await api.global_search(
        config=graphrag_config,
        entities=entities,
        communities=communities,
        community_reports=community_reports,
        community_level=2, # 指定社区层级为2
        dynamic_community_selection=False, # 关闭动态社区选择
        response_type="Multiple Paragraphs", # 指定相应类型为多段落文本
        query=query
    )
    # print(response)
    return response

if __name__ == "__main__":
    # asyncio.run(rag_ml("萧炎的女性朋友有哪些？"))
    
    mcp.run(transport="stdio")
