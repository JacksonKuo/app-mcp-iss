import asyncio
from typing import Optional
from typing import Any
from contextlib import AsyncExitStack

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from openai import OpenAI
import json
import os

# uses responses api
class MCPClient:
    def __init__(self):
        # Initialize session and client objects
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()
        self.openai = OpenAI()

    async def connect_to_server(self):
        server_params = StdioServerParameters(
            command="python3",
            args=["mcp-server-iss.py"],
            env=None
        )

        stdio_transport = await self.exit_stack.enter_async_context(stdio_client(server_params))
        self.stdio, self.write = stdio_transport
        self.session = await self.exit_stack.enter_async_context(ClientSession(self.stdio, self.write))

        await self.session.initialize()

    async def list_tools(self):
        response = await self.session.list_tools()
        tools = response.tools
        print("List tools:", [tool.name for tool in tools])
        return response

    async def call_tool(self, tool_name: str):
        #class 'mcp.types.CallToolResult'
        response = await self.session.call_tool(tool_name)
        print(f"Calling tool [{tool_name}]:", response)
        return response

    async def cleanup(self):
        """Clean up resources"""
        await self.exit_stack.aclose()

    async def send_request(self, messages:list) -> Any:
        response = await self.list_tools()
        #diff
        available_tools = [{
            "type": "function",
            "name": tool.name,
            "description": tool.description
        } for tool in response.tools]

        #class 'openai.types.chat.chat_completion.ChatCompletion' 
        response = self.openai.responses.create(
            model="gpt-4o-mini",
            input=messages,
            tools=available_tools,
        )
        print("ChatGPT response:", response.to_dict())
        return response

    async def process_query(self, query: str) -> str:
        # initial query
        messages = [
            {
                "role": "developer",
                "content": query
            }
        ]
        response = await self.send_request(messages)
        tool_call = response.output[0]

        # check for tool calls
        if tool_call.type == "function_call":
            # append chatgpt tool call
            # tool_call = list
            messages.append(tool_call)
            
            tool_name = tool_call.name 
            tool_result = await self.call_tool(tool_name)
            coordinate = tool_result.content[0].text
            print("Tool results:", coordinate)   

            messages.append({
                "type": "function_call_output",
                "call_id": tool_call.call_id,
                "output": coordinate
            })         

            print("Messages:", messages)
            response = await self.send_request(messages)
            print("ChatGPT answer:", response.output_text)


async def main():
    if len(sys.argv) < 1:
        print("Usage: python client.py")
        sys.exit(1)
    
    if not os.environ['OPENAI_API_KEY']:
        print("Missing OpenAI API key")
        sys.exit(1)

    client = MCPClient()
    try:
        await client.connect_to_server()
        await client.list_tools()
        await client.process_query("What's the current geolocation of the ISS and what city is closest to that position? Don't add formatting to the coordinates")
        #await client.chat_loop()
    finally:
        await client.cleanup()

if __name__ == "__main__":
    import sys
    asyncio.run(main())