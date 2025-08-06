from mcp.server.fastmcp import FastMCP
from typing import Any
import httpx
import asyncio

mcp = FastMCP("weather")

weather_url = "http://api.weatherapi.com/v1/current.json"
weather_api = ""


# 具体工具功能实现
async def get_weather(city: str) -> dict[str, Any]:
    url = weather_url
    api_key = weather_api
    parameter = {
        "q": city,
        "key": api_key
    }
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, params=parameter)
            return response.json()
        except Exception as err:
            return {"error": f"请求失败: {str(err)}"}

async def format_data(data):
    city = data.get("location", {}).get("name", "未知")
    country = data.get("location", {}).get("country", "未知")
    temp = data.get("current", {}).get("temp_c", "N/A")
    humidity = data.get("current", {}).get("humidity", "N/A")
    wind_speed = data.get("current", {}).get("wind_kph", "N/A")

    return (
        f"🌍 {city}, {country}\n"
        f"🌡 温度: {temp}°C\n"
        f"💧 湿度: {humidity}%\n"
        f"🌬 风速: {wind_speed} m/s\n"
    )


# 工具调用定义
@mcp.tool()
async def query_weather(city: str) -> str:
    """
    输入指定城市的英文名称，返回今日天气查询结果。
    :param city: 城市名称（需使用英文）
    :return: 格式化后的天气信息
    """
    data = await get_weather(city)
    # print(data)
    return await format_data(data)


if __name__ == "__main__":
    # print(asyncio.run(query_weather("shenzhen")))
    mcp.run(transport="stdio") # server 和 client 都在本地（或同一个服务器上），stdio即可，不需要网络通信。否则用sse
