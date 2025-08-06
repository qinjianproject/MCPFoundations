'''
1. 启动客户端
2. 连接服务端
3. 回收服务端的资源
'''

from contextlib import AsyncExitStack
from mcp import StdioServerParameters, ClientSession
from mcp.client.stdio import stdio_client
import sys
import asyncio
from openai import OpenAI
import json
from dotenv import load_dotenv
import os
import traceback

load_dotenv(".env")


class MCPClient(object):
    def __init__(self):
        self.session = None 
        self.stdio, self.write = None, None # self.stdio用于接收服务器返回的数据（比如天气查询结果），self.write用于向服务器发送请求（比如城市名称）
        self.exit_stack = AsyncExitStack() # 保证异步函数被调用后自动释放资源
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"), base_url=os.getenv("BASE_URL")) # 大模型客户端
        self.model = os.getenv("MODEL")


    async def cleanup(self):
        '''回收服务端资源'''
        await self.exit_stack.aclose()

    async def connect_server(self, server_script_path):
        if not server_script_path.endswith(".py"):
            ValueError("服务端的脚本必须是python文件，请先检查")
        
        # 创建启动服务器服务的参数
        server_params = StdioServerParameters(
            command = "python",
            args = [server_script_path],
            env = None
        )

        # 启动服务
        self.stdio, self.write = await self.exit_stack.enter_async_context(stdio_client(server_params))
        self.session = await self.exit_stack.enter_async_context(ClientSession(self.stdio, self.write))

        await self.session.initialize() # 与服务端建立握手协议，确认通信正常

        response = await self.session.list_tools()
        print("连接服务器成功，服务器支持以下工具：", [tool.name for tool in response.tools])



    async def process_query(self, query):
        messages = [{"role": "user", "content": query}]

        tools_info = await self.session.list_tools()
        available_tools = [{
            "type": "function",
            "function": {
                "name": tool.name, # 函数名
                "description": tool.description, # 函数描述
                "input_schema": tool.inputSchema # 参数
            }
        }
            for tool in tools_info.tools
        ]

        # print(available_tools)


        '''让模型自动判断是否还需要调用tool_calls'''
        while True:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=available_tools
            )
            
            content = response.choices[0]
            # print("-----------------")
            # print(content)
            # print("-----------------")
            # print(content.message)
            # print("===================")
            
            messages.append(content.message.model_dump()) # 将大模型返回结果添加上
            
            if content.finish_reason != "tool_calls":
                break
                
            # 处理工具调用
            tool_call = content.message.tool_calls[0] 
            tool_name = tool_call.function.name  # 工具名称
            tool_args = json.loads(tool_call.function.arguments) # 工具参数
            
            
            
            # 执行工具
            result = await self.session.call_tool(tool_name, tool_args)
            print(f"执行的工具名: {tool_name}， 参数: {tool_args}")
            
            messages.append({ # 将工具的返回结果添加上
                "role": "tool",
                "content": result.content[0].text,
                "tool_call_id": tool_call.id
            })

        pretty_result = [{"role": message.get("role",""), "content": message.get("content",""), "tool_calls": message.get("tool_calls",None)} for message in messages]
        return json.dumps(pretty_result, indent=4, ensure_ascii=False)






        '''只调用一次tool_calls'''
        # response = self.client.chat.completions.create(
        #         model = self.model,
        #         messages = messages,
        #         tools = available_tools
        #     )


        # content = response.choices[0]
        # print("-----------------")
        # print(content)
        # print("-----------------")
        # print(content.message)
        # print("===================")
        # print(content.message.content)
        # print("====================")


        # messages.append(content.message.model_dump()) # 将大模型返回的信息添加上



        # if content.finish_reason == "tool_calls": # 如果返回的结果中需要调用工具
        #     tool_call = content.message.tool_calls[0]
        #     tool_name = tool_call.function.name
        #     tool_args = json.loads(tool_call.function.arguments)

        #     # 执行工具
        #     result = await self.session.call_tool(tool_name, tool_args)
        #     print(f"执行的工具名: {tool_name}， 参数: {tool_args}")

        #     messages.append({ # 将工具调用结果也添加上
        #         "role": "tool",
        #         "content": result.content[0].text,
        #         "tool_call_id": tool_call.id
        #     })


        #     response = self.client.chat.completions.create(
        #         model = self.model,
        #         messages = messages,
        #     )

        #     return response.choices[0].message.content
        # return content.message.content
            



    '''存在一个问题，没有进行对话的持久化记忆，每个会话是独立的'''
    async def chat(self):
        print("exit[退出]")
        while True:
            try:
                query = input("请输入: ")
                if query.lower() == "exit":
                    break

                response = await self.process_query(query)
                print(response)
            except Exception as err:
                traceback.print_stack()
                print(f"异常: {str(err)}")




async def main():
    if len(sys.argv) < 2:
        print("Usage: uv run client.py <path_to_server_script>")
        sys.exit()
    
    client = MCPClient()
    try:
        await client.connect_server(sys.argv[1])
        await client.chat()


    finally:
        await client.cleanup()

    print("over")

if __name__ == "__main__":
    asyncio.run(main())