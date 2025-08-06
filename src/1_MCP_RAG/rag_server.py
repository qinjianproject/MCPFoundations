# 1. 索引的构建
# 2. server服务的封装，mcp的封装

from langchain_community.document_loaders import PyPDFLoader, TextLoader # 加载文档
from langchain_text_splitters import RecursiveCharacterTextSplitter
# from langchain_community.vectorstores import Chroma
from langchain_chroma import Chroma
from langchain.chains import RetrievalQA
# from langchain.embeddings.huggingface import HuggingFaceEmbeddings
from langchain_huggingface import HuggingFaceEmbeddings
import os
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from dotenv import load_dotenv

load_dotenv(".env")

class RAGSystem(object):
    def __init__(self, config):
        self.config = config

        # # 常规大模型
        # self.llm = ChatOpenAI(
        #     model = os.getenv("MODEL", "qwen-plus"),
        #     base_url = os.getenv("BASE_URL"),
        #     api_key = os.getenv("OPEN_API_KEY")
        # )

        # 常规大模型
        self.llm = ChatOpenAI(
            model = "deepseek-chat",
            base_url = "https://api.deepseek.com/v1",
            api_key = "sk-2bca1a21b8594c068c0daf2c02a07106"
        )


        # embedding模型
        self.embedding = HuggingFaceEmbeddings(
            model_name = os.getenv("EMBED_MODEL")
        )

        # 向量数据库
        self.vectorstore = Chroma(
            collection_name=self.config["collection_name"], # 向量数据库名称
            embedding_function=self.embedding, # embedding模型
            persist_directory=self.config["persist_dir"] # 永久化目录
        )

        # 检索
        self.retriever = self.vectorstore.as_retriever(
            search_type = "mmr", # 搜索类型
            search_kwargs = { # 搜索参数
                "k": self.config.get("top_k", 5) # 返回top_k条
            }
        )

    # 加载文档
    def _load_documents(self, file_paths):
        docs = []
        for path in file_paths:
            # path = ""
            if path.endswith(".pdf"):
                loader = PyPDFLoader(path)
            elif path.endswith(".txt"):
                loader = TextLoader(path, encoding="utf-8")
            else:
                print(f"跳过不支持的文件：{path}")
                continue
            docs.extend(loader.load())
        return docs
    
    # 文档切片
    def _chunk_documents(self, docs):
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size = self.config.get("chunk_size", 500),
            chunk_overlap = self.config.get("chunk_overlap", 50),
            length_function = len,
            is_separator_regex = True
        )

        return text_splitter.split_documents(docs)

    # 构建知识库
    def build_knowledge(self, file_paths):
        # 1. 加载文档
        raw_docs = self._load_documents(file_paths)
        # 2. 切块
        chunks = self._chunk_documents(raw_docs)
        # 3. 生成向量并存储
        self.vectorstore.add_documents(chunks)

        print(f"知识库构建完成，文档块数：{len(chunks)}")

    # 查询
    def query(self, question):
        qa_chain = RetrievalQA.from_chain_type(
            self.llm, # 大模型，用于根据返回的信息生成答案
            retriever=self.retriever, # 检索方式
            return_source_documents=True # 返回原文档
        )

        result = qa_chain.invoke({"query": question}) 
        return_result = {
            "answer": result["result"],
            "sources":[
                {
                    "source": doc.metadata.get("source", "unknown"),
                    "page": doc.metadata.get("page", "N/A")
                }
                for doc in result["source_documents"]
            ]
        }

        return return_result
    

config = {
    "persist_dir": "./data/rag_db",
    "collection_name": "rag",
    "chunk_size": 500,
    "chunk_overlap": 50,
    "top_k": 5
}


rag = RAGSystem(config)

rag.build_knowledge(
    file_paths=[
        "/home/qinjian/agent_study/src/1_MCP_RAG/data/doupocangqiong.txt"
    ]
)

from mcp.server.fastmcp import FastMCP
mcp = FastMCP("rag_mcp")
import asyncio

@mcp.tool()
async def rag_query(query):
    response = rag.query(query)
    print("response: ", response)
    return response["answer"]

async def search_demo():
    query = "萧炎的女性朋友有哪些？"
    response = await rag_query(query)
    print(response)

if __name__ == "__main__":
    # asyncio.run(search_demo())
    mcp.run(transport="stdio")