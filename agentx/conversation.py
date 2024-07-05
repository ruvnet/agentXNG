# conversation.py

import os
import time
from anthropic import Anthropic
from agentx.utils import update_system_prompt, execute_tool, encode_image_to_base64, print_colored
from agentx.config import CONTINUATION_EXIT_PHRASE, TOOL_COLOR, RESULT_COLOR, CLAUDE_COLOR

client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

def chat_with_claude(user_input, image_path, conversation_history, automode, current_iteration=None, max_iterations=None):
    if image_path:
        print_colored(f"Processing image at path: {image_path}", TOOL_COLOR)
        image_base64 = encode_image_to_base64(image_path)

        if image_base64.startswith("Error"):
            print_colored(f"Error encoding image: {image_base64}", TOOL_COLOR)
            return "I'm sorry, there was an error processing the image. Please try again.", False

        image_message = {
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/jpeg",
                        "data": image_base64
                    }
                },
                {
                    "type": "text",
                    "text": f"User input for image: {user_input}"
                }
            ]
        }
        conversation_history.append(image_message)
        print_colored("Image message added to conversation history", TOOL_COLOR)
    else:
        conversation_history.append({"role": "user", "content": user_input})

    # Ensure that roles alternate between "user" and "assistant"
    messages = []
    for msg in conversation_history:
        if msg.get('content'):
            if len(messages) == 0 or messages[-1]['role'] != msg['role']:
                messages.append(msg)
            else:
                # Merge consecutive user messages into one
                messages[-1]['content'] += "\n" + msg['content']

    try:
        assistant_response = ""
        with client.messages.stream(
            model="claude-3-5-sonnet-20240620",
            max_tokens=4000,
            system=update_system_prompt(current_iteration, max_iterations),
            messages=messages,
            tools=tools,
            tool_choice={"type": "auto"}
        ) as stream:
            exit_continuation = False

            for event in stream:
                if event.type == "text":
                    # Print each character with a delay to simulate typing
                    for char in event.text:
                        print(char, end='', flush=True)
                        time.sleep(0.01)
                    assistant_response += event.text
                    if CONTINUATION_EXIT_PHRASE in event.text:
                        exit_continuation = True
                        break
                elif event.type == "tool_use":
                    tool_name = event.name
                    tool_input = event.input
                    tool_use_id = event.id

                    print_colored(f"\nTool Used: {tool_name}", TOOL_COLOR)
                    print_colored(f"Tool Input: {tool_input}", TOOL_COLOR)

                    result = execute_tool(tool_name, tool_input)
                    print_colored(f"Tool Result: {result}", RESULT_COLOR)

                    conversation_history.append({"role": "assistant", "content": [event]})
                    conversation_history.append({
                        "role": "user",
                        "content": [
                            {
                                "type": "tool_result",
                                "tool_use_id": tool_use_id,
                                "content": result
                            }
                        ]
                    })

                    tool_response = client.messages.create(
                        model="claude-3-5-sonnet-20240620",
                        max_tokens=4000,
                        system=update_system_prompt(current_iteration, max_iterations),
                        messages=[msg for msg in conversation_history if msg.get('content')],
                        tools=tools,
                        tool_choice={"type": "auto"}
                    )

                    for tool_content_block in tool_response.content:
                        if tool_content_block.type == "text":
                            for char in tool_content_block.text:
                                print(char, end='', flush=True)
                                time.sleep(0.01)
                            assistant_response += tool_content_block.text

    except Exception as e:
        print_colored(f"Error calling Claude API: {str(e)}", TOOL_COLOR)
        return "I'm sorry, there was an error communicating with the AI. Please try again.", False

    if assistant_response:
        conversation_history.append({"role": "assistant", "content": assistant_response.strip()})

    return "", exit_continuation  # Return empty string to avoid reprinting the response


def process_and_display_response(response):
    if response.startswith("Error") or response.startswith("I'm sorry"):
        print_colored(response, TOOL_COLOR)
    else:
        if "```" in response:
            parts = response.split("```")
            for i, part in enumerate(parts):
                if i % 2 == 0:
                    print_colored(part, CLAUDE_COLOR)
                else:
                    lines = part.split('\n')
                    language = lines[0].strip() if lines else ""
                    code = '\n'.join(lines[1:]) if len(lines) > 1 else ""

                    if language and code:
                        print_code(code, language)
                    elif code:
                        print_colored(f"Code:\n{code}", CLAUDE_COLOR)
                    else:
                        print_colored(part, CLAUDE_COLOR)
        else:
            print_colored(response, CLAUDE_COLOR)
