import chainlit as cl

@cl.on_chat_start
async def start():
    await cl.Message(content="Test started").send()

@cl.on_message
async def main(msg: cl.Message):
    # Method 1: cl.Step
    step = cl.Step(name="Processing")
    step.output = "Logs..."
    await step.send()
    
    await cl.Message(content="Response to Method 1").send()
    
    # Method 2: System Message
    sys_msg = cl.Message(content="Processing logs...", author="System")
    await sys_msg.send()
    
    await cl.Message(content="Response to Method 2").send()
