# -*- coding: utf-8 -*-
# ----------------------------
# @Time    : 2025/4/3 14:59
# @Author  : acedar
# @FileName: rag_client.py
# ----------------------------

import asyncio
import os
import json
from argparse import ArgumentParser
from typing import Optional
from contextlib import AsyncExitStack
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from openai import OpenAI
from dotenv import load_dotenv
import traceback
import sys

# 加载配置文件
load_dotenv(".env")

SYS_PROMPT = "you are a helpful assistant"


class McpClient:
    def __init__(self):
        """
        使用openai的包适配所有支持openai标准接口的第三方服务，如deepseek，qwen等
        """
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.base_url = os.getenv("BASE_URL")  # 读取 BASE YRL
        self.model = os.getenv("MODEL")  # 读取 model
        if not self.openai_api_key:
            raise ValueError("OPENAI_API_KEY 为空，请先配置OPENAI_API_KEY")
        self.client = OpenAI(api_key=self.openai_api_key, base_url=self.base_url)  # 创建OpenAI client
        self.session: Optional[ClientSession] = None

        # 资源管理
        self.exit_stack = AsyncExitStack()

        self.valid_tools = None

        self.messages = None

    async def init_messages(self):
        self.messages = [{"role": "system", "content": SYS_PROMPT}]

    async def connect_to_server(self, server_script: str):
        """
        链接mcp服务
        :param server_script:
        :return:
        """
        # 这里目前支持python脚本，支持其他脚本类似
        assert server_script.endswith('.py')
        command = "python"
        server_params = StdioServerParameters(
            command=command,
            args=[server_script],
            env=None
        )

        # 启动MCP服务器并建立通信
        stdio, write = await self.exit_stack.enter_async_context(stdio_client(server_params))
        self.session = await self.exit_stack.enter_async_context(ClientSession(stdio, write))

        await self.session.initialize()

        # 获取mcp工具列表
        response = await self.session.list_tools()
        tools = response.tools
        print("---------------------")
        print("成功链接到mcp服务器，支持的工具:", [tool.name for tool in tools])

    async def tools_format(self, available_tools):
        """
        Claude Function call的格式与Openai Function call的参数格式不一致，这里做一个适配
        :param available_tools:
        :return:
        """

        valid_tools = []
        for tool_info in available_tools:
            # 必须要有的字段校验
            if not isinstance(tool_info, dict) or "type" not in tool_info or "function" not in tool_info:
                print(f"工具: {tool_info['name']} 没有 type 和 function 字段， 将会忽略该工具")
                continue

            old_func = tool_info["function"]
            # function字段校验
            if not isinstance(old_func, dict) or "name" not in old_func or "description" not in old_func:
                print(f"工具: {tool_info['name']}的 functon中信息中 没有 name 和 description 字段， 将会忽略该工具")
                continue

            new_func = {
                "name": old_func["name"],
                "description": old_func["description"],
                "parameters": {}
            }

            # 函数的参数对齐
            if "input_schema" in old_func and isinstance(old_func["input_schema"], dict):
                old_schema = old_func["input_schema"]

                new_func["parameters"]["type"] = old_schema.get("type", "object")
                new_func["parameters"]["properties"] = old_schema.get("properties", {})
                new_func["parameters"]["required"] = old_schema.get("required", [])
            new_item = {
                "type": tool_info["type"],
                "function": new_func
            }
            valid_tools.append(new_item)
        
        print(f"提供的工具数量：{len(available_tools)}, 实际可用的工具数量: {len(valid_tools)}")
        print("===============================")
        return valid_tools

    async def execute_tool(self, tool_call):
        tool_name = tool_call.function.name
        tool_args = json.loads(tool_call.function.arguments)

        # 执行工具
        result = await self.session.call_tool(tool_name, tool_args)
        print("---------------------")
        print(f"执行工具: {tool_name}, 参数: {tool_args}")
        print("---------------------")
        print(f"执行结果: {result}...")
        return result

    async def get_tools(self):
        if self.valid_tools:
            return self.valid_tools

        response = await self.session.list_tools()

        available_tools = [{
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description,
                "input_schema": tool.inputSchema
            }
        } for tool in response.tools]
        print("===============================")
        print("available_tools:", available_tools)

        # 进行参数格式转化
        self.valid_tools = await self.tools_format(available_tools)
        return self.valid_tools

    async def qa(self, query: str) -> str:
        """
        执行逻辑:
        1. 先调用大模型决定调用哪个工具, 不能不需要调用工具
        2. 执行工具[如何有需要调用]
        3. 结合工具结果再次调用大模型返回结果[如果有需要调用]
        """
        if not self.messages:
            await self.init_messages()
        self.messages.append({"role": "user", "content": query})
        # print("model:", self.model, "messages:", self.messages)
        tools = await self.get_tools()
        # print("tools:", tools)
        response = self.client.chat.completions.create(
            model=self.model,
            messages=self.messages,
            tools=tools
        )

        # 解析结果
        content = response.choices[0]
        if content.finish_reason == "tool_calls":
            # 解析工具并执行工具
            print("---------------------")
            print("接下来调用工具....")
            tool_call = content.message.tool_calls[0]
            tool_call_result = await self.execute_tool(tool_call)

            self.messages.append(content.message.model_dump())
            self.messages.append({
                "role": "tool",
                "content": tool_call_result.content[0].text,
                "tool_call_id": tool_call.id,
            })

            # 结合mcp工具调用结果，重新调用大模型, 生成最终结果
            response = self.client.chat.completions.create(
                model=self.model,
                messages=self.messages
            )
            return response.choices[0].message.content
        # 无需调用工具，直接返回
        print("---------------------")
        print("无需调用工具....")
        self.messages.append({
            "role": "assistant",
            "content": content.message.content
        })
        return content.message.content

    async def chat(self):
        print("---------------------")
        print("欢迎来到MCP+graphrag体验服务，[restart]: 重新开始新一轮对话， [exit]: 退出智能体")

        while True:
            try:
                query = input("你的输入: ").strip()
                if query.lower() == 'exit':
                    break
                if query == "restart":
                    print("---------------------")
                    print("开启新一轮对话\n")
                    await self.init_messages()
                response = await self.qa(query)
                print("---------------------")
                print(f"智能体: {response}")
            except Exception as e:
                traceback.print_exc()
                print("---------------------")
                print(f"\n 智能体异常: {str(e)}")
                traceback.print_exc()

    async def exit(self):
        """清理资源"""
        await self.exit_stack.aclose()


async def main():
    print("begin......")
    client = McpClient()
    try:
        if len(sys.argv) < 2:
            print("---------------------")
            print("Usage: uv run rag_client.py <path_to_server_script>")
            sys.exit()
        print("begin connect to server")
        await client.connect_to_server(sys.argv[1])
        await client.chat()
    finally:
        await client.exit()

# parser = ArgumentParser(description=__doc__)
# parser.add_argument(
#     "--server_script", type=str, default="rag_server.py")
# args = parser.parse_args()

if __name__ == "__main__":
    asyncio.run(main())
