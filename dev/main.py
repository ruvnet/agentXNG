import os
from datetime import datetime
import json
from colorama import init, Fore, Style
from pygments import highlight
from pygments.lexers import get_lexer_by_name
from pygments.formatters import TerminalFormatter
import pygments.util
import base64
from PIL import Image
import io
import re
import difflib
from litellm import completion
import requests

# Initialize colorama
init()

# Color constants
USER_COLOR = Fore.WHITE
CLAUDE_COLOR = Fore.BLUE
TOOL_COLOR = Fore.YELLOW
RESULT_COLOR = Fore.GREEN

# Add these constants at the top of the file
CONTINUATION_EXIT_PHRASE = "AUTOMODE_COMPLETE"
MAX_CONTINUATION_ITERATIONS = 25

# Set up the conversation memory
conversation_history = []

# automode flag
automode = False

# System prompt
system_prompt = """
You are an AI assistant powered by the Claude-3.5-Sonnet model. You are an exceptional software developer with vast knowledge across multiple programming languages, frameworks, and best practices. Your capabilities include:

1. Creating project structures, including folders and files
2. Writing clean, efficient, and well-documented code
3. Debugging complex issues and providing detailed explanations
4. Offering architectural insights and design patterns
5. Staying up-to-date with the latest technologies and industry trends
6. Reading and analyzing existing files in the project directory
7. Listing files in the root directory of the project
8. Performing web searches to get up-to-date information or additional context

When asked to create a project:
- Always start by creating a root folder for the project.
- Then, create the necessary subdirectories and files within that root folder.
- Organize the project structure logically and follow best practices for the specific type of project being created.
- Use the provided tools to create folders and files as needed.

When asked to make edits or improvements:
- Use the read_file tool to examine the contents of existing files.
- Analyze the code and suggest improvements or make necessary edits.
- Use the write_to_file tool to implement changes, providing the full updated file content.

Be sure to consider the type of project (e.g., Python, JavaScript, web application) when determining the appropriate structure and files to include.

{automode_status}

When in automode:
1. Set clear, achievable goals for yourself based on the user's request
2. Work through these goals one by one, using the available tools as needed
3. REMEMBER!! You can Read files, write code, LIST the files, and even SEARCH and make edits, use these tools as necessary to accomplish each goal
4. ALWAYS READ A FILE BEFORE EDITING IT IF YOU ARE MISSING CONTENT. Provide regular updates on your progress
5. IMPORTANT RULE!! When you know your goals are completed, DO NOT CONTINUE IN POINTLESS BACK AND FORTH CONVERSATIONS with yourself, if you think we achieved the results established to the original request say "AUTOMODE_COMPLETE" in your response to exit the loop!
6. ULTRA IMPORTANT! You have access to this {iteration_info} amount of iterations you have left to complete the request, you can use this information to make decisions and to provide updates on your progress knowing the amount of responses you have left to complete the request.

When you need to use a tool, format your request like this:

Tool: [tool_name]
Arguments: [tool_arguments]

Available tools:
- create_folder: Create a new folder at the specified path
- create_file: Create a new file at the specified path with optional content
- write_to_file: Write content to a file at the specified path
- read_file: Read the contents of a file at the specified path
- list_files: List all files and directories in the specified path
- searxng_search: Perform a web search using SearXNG API

Example:
Tool: create_folder
Arguments: path=/project/new_folder

Tool: write_to_file
Arguments: path=/project/new_file.txt
content=This is the content of the new file.

After using a tool, I will provide you with the result, and you can continue the conversation or use another tool if needed.
"""

def check_anthropic_api_key():
    api_key = os.environ.get('ANTHROPIC_API_KEY')
    if not api_key:
        print_colored("Error: Anthropic API key not found.", TOOL_COLOR)
        print_colored("Please set your Anthropic API key as an environment variable:", TOOL_COLOR)
        print_colored("1. Export the API key in your terminal:", USER_COLOR)
        print_colored("   export ANTHROPIC_API_KEY='your-api-key-here'", USER_COLOR)
        print_colored("2. Or add it to your .bashrc or .zshrc file:", USER_COLOR)
        print_colored("   echo 'export ANTHROPIC_API_KEY='your-api-key-here'' >> ~/.bashrc", USER_COLOR)
        print_colored("   source ~/.bashrc", USER_COLOR)
        print_colored("Replace 'your-api-key-here' with your actual Anthropic API key.", TOOL_COLOR)
        print_colored("After setting the API key, restart the script.", TOOL_COLOR)
        return False
    return True

def update_system_prompt(current_iteration=None, max_iterations=None):
    global system_prompt
    automode_status = "You are currently in automode." if automode else "You are not in automode."
    iteration_info = ""
    if current_iteration is not None and max_iterations is not None:
        iteration_info = f"You are currently on iteration {current_iteration} out of {max_iterations} in automode."
    return system_prompt.format(automode_status=automode_status, iteration_info=iteration_info)

def print_colored(text, color):
    print(f"{color}{text}{Style.RESET_ALL}")

def print_code(code, language):
    try:
        lexer = get_lexer_by_name(language, stripall=True)
        formatted_code = highlight(code, lexer, TerminalFormatter())
        print(formatted_code)
    except pygments.util.ClassNotFound:
        print_colored(f"Code (language: {language}):\n{code}", CLAUDE_COLOR)

def create_folder(path):
    try:
        os.makedirs(path, exist_ok=True)
        return f"Folder created: {path}"
    except Exception as e:
        return f"Error creating folder: {str(e)}"

def create_file(path, content=""):
    try:
        with open(path, 'w') as f:
            f.write(content)
        return f"File created: {path}"
    except Exception as e:
        return f"Error creating file: {str(e)}"

def generate_and_apply_diff(original_content, new_content, path):
    diff = list(difflib.unified_diff(
        original_content.splitlines(keepends=True),
        new_content.splitlines(keepends=True),
        fromfile=f"a/{path}",
        tofile=f"b/{path}",
        n=3
    ))
    
    if not diff:
        return "No changes detected."
    
    try:
        with open(path, 'w') as f:
            f.writelines(new_content)
        return f"Changes applied to {path}:\n" + ''.join(diff)
    except Exception as e:
        return f"Error applying changes: {str(e)}"

def write_to_file(path, content):
    try:
        if os.path.exists(path):
            with open(path, 'r') as f:
                original_content = f.read()
            result = generate_and_apply_diff(original_content, content, path)
        else:
            with open(path, 'w') as f:
                f.write(content)
            result = f"New file created and content written to: {path}"
        return result
    except Exception as e:
        return f"Error writing to file: {str(e)}"

def read_file(path):
    try:
        with open(path, 'r') as f:
            content = f.read()
        return content
    except Exception as e:
        return f"Error reading file: {str(e)}"

def list_files(path="."):
    try:
        files = os.listdir(path)
        return "\n".join(files)
    except Exception as e:
        return f"Error listing files: {str(e)}"

def searxng_search(query):
    try:
        searxng_url = os.environ.get('SEARXNG_URL', 'http://localhost:8888')
        params = {
            "q": query,
            "format": "json"
        }
        response = requests.get(searxng_url, params=params)
        results = response.json()
        
        formatted_results = []
        for result in results.get("results", [])[:5]:  # Limit to top 5 results
            formatted_results.append(f"Title: {result['title']}\nURL: {result['url']}\nSnippet: {result['content']}\n")
        
        return "\n".join(formatted_results) if formatted_results else "No results found."
    except Exception as e:
        return f"Error performing search: {str(e)}"

def execute_tool(tool_name, tool_input):
    if tool_name == "create_folder":
        return create_folder(tool_input["path"])
    elif tool_name == "create_file":
        return create_file(tool_input["path"], tool_input.get("content", ""))
    elif tool_name == "write_to_file":
        return write_to_file(tool_input["path"], tool_input["content"])
    elif tool_name == "read_file":
        return read_file(tool_input["path"])
    elif tool_name == "list_files":
        return list_files(tool_input.get("path", "."))
    elif tool_name == "searxng_search":
        return searxng_search(tool_input["query"])
    else:
        return f"Unknown tool: {tool_name}"

def encode_image_to_base64(image_path):
    try:
        with Image.open(image_path) as img:
            max_size = (1024, 1024)
            img.thumbnail(max_size, Image.DEFAULT_STRATEGY)
            if img.mode != 'RGB':
                img = img.convert('RGB')
            img_byte_arr = io.BytesIO()
            img.save(img_byte_arr, format='JPEG')
            return base64.b64encode(img_byte_arr.getvalue()).decode('utf-8')
    except Exception as e:
        return f"Error encoding image: {str(e)}"

def process_tool_calls(response):
    tool_calls = []
    lines = response.split('\n')
    current_tool = None
    current_args = ""

    for line in lines:
        if line.startswith("Tool:"):
            if current_tool:
                tool_calls.append({"name": current_tool, "arguments": current_args.strip()})
            current_tool = line.split("Tool:")[1].strip()
            current_args = ""
        elif line.startswith("Arguments:"):
            current_args += line.split("Arguments:")[1].strip() + "\n"
        elif current_tool and line.strip():
            current_args += line.strip() + "\n"

    if current_tool:
        tool_calls.append({"name": current_tool, "arguments": current_args.strip()})

    return tool_calls

def chat_with_claude(user_input, image_path=None, current_iteration=None, max_iterations=None):
    global conversation_history, automode
    
    if not check_anthropic_api_key():
        return "API key not set. Please set up your Anthropic API key and try again.", False

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
    
    # Add system message to the beginning of the conversation history
    system_message = {
        "role": "system",
        "content": update_system_prompt(current_iteration, max_iterations)
    }
    messages = [system_message] + [msg for msg in conversation_history if msg.get('content')]
    
    try:
        response = completion(
            model="claude-3-5-sonnet",
            messages=messages,
            max_tokens=4000,
            temperature=0.7
        )
    except Exception as e:
        print_colored(f"Error calling Claude API: {str(e)}", TOOL_COLOR)
        return "I'm sorry, there was an error communicating with the AI. Please try again.", False
    
    assistant_response = ""
    exit_continuation = False
    
    for content_block in response.content:
        if content_block.type == "text":
            assistant_response += content_block.text
            print_colored(f"\nClaude: {content_block.text}", CLAUDE_COLOR)
            if CONTINUATION_EXIT_PHRASE in content_block.text:
                exit_continuation = True
    
    # Process the assistant's response to check for tool usage
    tool_calls = process_tool_calls(assistant_response)
    for tool_call in tool_calls:
        tool_name = tool_call['name']
        tool_input = tool_call['arguments']
        
        print_colored(f"\nTool Used: {tool_name}", TOOL_COLOR)
        print_colored(f"Tool Input: {tool_input}", TOOL_COLOR)
        
        result = execute_tool(tool_name, tool_input)
        print_colored(f"Tool Result: {result}", RESULT_COLOR)
        
        # Append tool result to conversation history
        conversation_history.append({
            "role": "user",
            "content": f"Tool result for {tool_name}: {result}"
        })
        
        # Get Claude's response to the tool result
        try:
            tool_response = completion(
                model="claude-3-5-sonnet-20240620",
                messages=[system_message] + [msg for msg in conversation_history if msg.get('content')],
                max_tokens=4000,
                temperature=0.7
            )
            
            for tool_content_block in tool_response.content:
                if tool_content_block.type == "text":
                    assistant_response += "\n" + tool_content_block.text
                    print_colored(f"\nClaude: {tool_content_block.text}", CLAUDE_COLOR)
        except Exception as e:
            print_colored(f"Error in tool response: {str(e)}", TOOL_COLOR)
            assistant_response += "\nI encountered an error while processing the tool result. Please try again."
    
    if assistant_response:
        conversation_history.append({"role": "assistant", "content": assistant_response})
    
    return assistant_response, exit_continuation

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

def main():
    global automode, conversation_history
    print_colored("Welcome to the Claude-3.5-Sonnet Engineer Chat with Image Support!", CLAUDE_COLOR)
    print_colored("Type 'exit' to end the conversation.", CLAUDE_COLOR)
    print_colored("Type 'image' to include an image in your message.", CLAUDE_COLOR)
    print_colored("Type 'automode [number]' to enter Autonomous mode with a specific number of iterations.", CLAUDE_COLOR)
    print_colored("While in automode, press Ctrl+C at any time to exit the automode to return to regular chat.", CLAUDE_COLOR)
    
    if not check_anthropic_api_key():
        return

    while True:
        user_input = input(f"\n{USER_COLOR}You: {Style.RESET_ALL}")
        
        if user_input.lower() == 'exit':
            print_colored("Thank you for chatting. Goodbye!", CLAUDE_COLOR)
            break
        
        if user_input.lower() == 'image':
            image_path = input(f"{USER_COLOR}Drag and drop your image here: {Style.RESET_ALL}").strip().replace("'", "")
            
            if os.path.isfile(image_path):
                user_input = input(f"{USER_COLOR}You (prompt for image): {Style.RESET_ALL}")
                response, _ = chat_with_claude(user_input, image_path)
                process_and_display_response(response)
            else:
                print_colored("Invalid image path. Please try again.", CLAUDE_COLOR)
                continue
        elif user_input.lower().startswith('automode'):
            try:
                parts = user_input.split()
                if len(parts) > 1 and parts[1].isdigit():
                    max_iterations = int(parts[1])
                else:
                    max_iterations = MAX_CONTINUATION_ITERATIONS
                
                automode = True
                print_colored(f"Entering automode with {max_iterations} iterations. Press Ctrl+C to exit automode at any time.", TOOL_COLOR)
                print_colored("Press Ctrl+C at any time to exit the automode loop.", TOOL_COLOR)
                user_input = input(f"\n{USER_COLOR}You: {Style.RESET_ALL}")
                
                iteration_count = 0
                try:
                    while automode and iteration_count < max_iterations:
                        response, exit_continuation = chat_with_claude(user_input, current_iteration=iteration_count+1, max_iterations=max_iterations)
                        process_and_display_response(response)
                        
                        if exit_continuation or CONTINUATION_EXIT_PHRASE in response:
                            print_colored("Automode completed.", TOOL_COLOR)
                            automode = False
                        else:
                            print_colored(f"Continuation iteration {iteration_count + 1} completed.", TOOL_COLOR)
                            print_colored("Press Ctrl+C to exit automode.", TOOL_COLOR)
                            user_input = "Continue with the next step."
                        
                        iteration_count += 1
                        
                        if iteration_count >= max_iterations:
                            print_colored("Max iterations reached. Exiting automode.", TOOL_COLOR)
                            automode = False
                except KeyboardInterrupt:
                    print_colored("\nAutomode interrupted by user. Exiting automode.", TOOL_COLOR)
                    automode = False
                    # Ensure the conversation history ends with an assistant message
                    if conversation_history and conversation_history[-1]["role"] == "user":
                        conversation_history.append({"role": "assistant", "content": "Automode interrupted. How can I assist you further?"})
            except KeyboardInterrupt:
                print_colored("\nAutomode interrupted by user. Exiting automode.", TOOL_COLOR)
                automode = False
                # Ensure the conversation history ends with an assistant message
                if conversation_history and conversation_history[-1]["role"] == "user":
                    conversation_history.append({"role": "assistant", "content": "Automode interrupted. How can I assist you further?"})
            
            print_colored("Exited automode. Returning to regular chat.", TOOL_COLOR)
        else:
            response, _ = chat_with_claude(user_input)
            process_and_display_response(response)

if __name__ == "__main__":
    main()