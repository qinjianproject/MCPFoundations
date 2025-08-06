import asyncio
import os
import json
import sys
from typing import Optional
from contextlib import AsyncExitStack

from openai import AsyncOpenAI
from dotenv import load_dotenv
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from openai.types.chat import ChatCompletionToolParam

# 加载环境变量
load_dotenv(".env")

class MCPClient:
    def __init__(self):
        """
        初始化MCP客户端
        """
        self.write = None
        self.stdio = None
        self.exit_stack = AsyncExitStack()
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.base_url=os.getenv("BASE_URL")
        self.model=os.getenv("MODEL")
        if not self.openai_api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set")
        self.client = AsyncOpenAI(api_key=self.openai_api_key, base_url=self.base_url)
        # 创建一个OpenAI客户端
        self.session: Optional[ClientSession] = None


    async def connect_to_server(self,server_script_path:str):
        """
        连接到MCP服务器
        :param server_script_path: MCP服务器脚本路径
        """
        is_python=server_script_path.endswith(".py")
        is_js=server_script_path.endswith(".js")
        if not (is_python or is_js):
            raise ValueError("服务器脚本必须是.py或.js文件")
        command="python" if is_python else "node"
        server_parameters=StdioServerParameters(
            command=command,
            args=[server_script_path],
            env=None
        )
        
        stdio_transport=await self.exit_stack.enter_async_context(stdio_client(server_parameters))
        self.stdio,self.write=stdio_transport
        self.session=await self.exit_stack.enter_async_context(ClientSession(self.stdio,self.write))

        await self.session.initialize()

        # 列出MCP服务器上的工具
        response=await self.session.list_tools()
        tools=response.tools
        print(f"MCP服务器上的工具：{tools}")

    async def process_query(self,query:str)-> str:
        """
        使用大模型查询并调用可用的MCP工具
        :param query: 用户输入的查询
        :return: 处理后的结果
        """
        messages=[{"role":"user","content":query}]
        response=await self.session.list_tools()

        # 构建符合 OpenAI API 规范的工具列表
        available_tools = []
        for tool in response.tools:
            tool_param = ChatCompletionToolParam(
                type="function",
                function={
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.inputSchema
                }
            )
            available_tools.append(tool_param)

        response=await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            tools=available_tools,
            stream=False  # 明确指定不使用流式
        )

        # 处理返回内容
        choice = response.choices[0]
        message = choice.message
        if hasattr(message, 'tool_calls') and message.tool_calls:
            # 获取工具调用
            tool_call=message.tool_calls[0]
            tool_name=tool_call.function.name
            tool_args=json.loads(tool_call.function.arguments)

            # 调用工具
            result=await self.session.call_tool(tool_name,tool_args)
            print(f"调用工具：{tool_name}，参数：{tool_args}")

            # 添加工具调用结果
            messages.append(message.model_dump())
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": result.content[0].text
            })
            print("----")
            print(result.content[0].text)
            print("----")

            # 将上面的消息发送给模型
            response=await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
            )
            # print("=============")
            # print(response.choices[0].message)
            
            return response.choices[0].message.content
            

        return message.content

    async def chat_loop(self):
        while True:
            try:
                query=input("you:").strip()
                if query.lower() == "quit":
                    break
                
                response=await self.process_query(query)
                print("=============")
                print(f"{self.model}: {response}")
                print("=============")

            except Exception as e:
                print(e)

    async def cleanup(self):
        await self.exit_stack.aclose()

async def main():
    if len(sys.argv) < 2:
        print("Usage: uv run client.py <path_to_server_script>")
        sys.exit(1)
    client = MCPClient()
    try:
        await client.connect_to_server(sys.argv[1])
        await client.chat_loop()
    finally:
        await client.cleanup()

if __name__ == "__main__":
    asyncio.run(main())
