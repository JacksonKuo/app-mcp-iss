import asyncio
from typing import Optional
from contextlib import AsyncExitStack

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from openai import OpenAI
import json

class MCPClient:
    def __init__(self):
        # Initialize session and client objects
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()
        self.openai = OpenAI()

    async def connect_to_server(self):
        """Connect to an MCP server"""

        server_params = StdioServerParameters(
            command="python3",
            args=["iss.py"],
            env=None
        )

        stdio_transport = await self.exit_stack.enter_async_context(stdio_client(server_params))
        self.stdio, self.write = stdio_transport
        self.session = await self.exit_stack.enter_async_context(ClientSession(self.stdio, self.write))

        await self.session.initialize()

        # List available tools
        response = await self.session.list_tools()
        tools = response.tools
        print("\nConnected to server with tools:", [tool.name for tool in tools])

    async def cleanup(self):
        """Clean up resources"""
        await self.exit_stack.aclose()

    async def process_query(self, query: str) -> str:
        """Process a query using OpenAI and available tools"""
        messages = [
            {
                "role": "developer",
                "content": query
            }
        ]
        #print("messages:",messages)

        response = await self.session.list_tools()
        available_tools = [{
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description,
                }
            #"input_schema": tool.inputSchema
        } for tool in response.tools]
        #print("available_tools",available_tools)

        response = self.openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            tools=available_tools,
            tool_choice="auto"
        )
        #print("response:",response)
    
        # Process response and handle tool calls
        final_text = []

        assistant_message_content = []

        content = response
        print(content)
        if content.choices[0].finish_reason == "tool_calls":
            tool_name = content.choices[0].message.tool_calls[0].function.name 
        
            # Execute tool call
            result = await self.session.call_tool(tool_name)
            final_text.append(f"[Calling tool {tool_name}")

            assistant_message_content.append(content)
            # appending to the original question
            # content is if chatgpt should tool call. and putting decision
            '''
            messages.append({
                "role": "assistant",
                "content": json.dumps(repr(assistant_message_content))
            })
            '''

            # result of the tool call
            messages.append({
                "role": "user",
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": content.id,
                        "content": json.dumps(repr(result.content))
                    }
                ]
            })

            print("messages:",messages)
            response = self.openai.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                tools=available_tools,
                tool_choice="auto"
            )
            #print("response:",response)
        


async def main():
    if len(sys.argv) < 1:
        print("Usage: python client.py")
        sys.exit(1)

    client = MCPClient()
    try:
        await client.connect_to_server()
        await client.process_query("What's the current geolocation of the ISS?")
       #await client.chat_loop()
    finally:
        await client.cleanup()




if __name__ == "__main__":
    import sys
    asyncio.run(main())