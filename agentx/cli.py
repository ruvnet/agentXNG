# cli.py

import os
from colorama import init, Fore, Style
from agentx.conversation import chat_with_claude, process_and_display_response
from agentx.config import USER_COLOR, CLAUDE_COLOR, TOOL_COLOR, CONTINUATION_EXIT_PHRASE, MAX_CONTINUATION_ITERATIONS

# Initialize colorama
init()

def print_colored(text, color):
    print(f"{color}{text}{Style.RESET_ALL}")

def main():
    conversation_history = []
    automode = False
    
    print_colored("Welcome to the Claude-3.5-Sonnet Engineer Chat with Image Support!", CLAUDE_COLOR)
    print_colored("Type 'exit' to end the conversation.", CLAUDE_COLOR)
    print_colored("Type 'image' to include an image in your message.", CLAUDE_COLOR)
    print_colored("Type 'automode [number]' to enter Autonomous mode with a specific number of iterations.", CLAUDE_COLOR)
    print_colored("While in automode, press Ctrl+C at any time to exit the automode to return to regular chat.", CLAUDE_COLOR)

    while True:
        user_input = input(f"\n{USER_COLOR}You: {Style.RESET_ALL}")

        if user_input.lower() == 'exit':
            print_colored("Thank you for chatting. Goodbye!", CLAUDE_COLOR)
            break

        if user_input.lower() == 'image':
            image_path = input(f"{USER_COLOR}Drag and drop your image here: {Style.RESET_ALL}").strip().replace("'", "")

            if os.path.isfile(image_path):
                user_input = input(f"{USER_COLOR}You (prompt for image): {Style.RESET_ALL}")
                response, _ = chat_with_claude(user_input, image_path, conversation_history, automode)
                process_and_display_response(response)
            else:
                print_colored("Invalid image path. Please try again.", CLAUDE_COLOR)
                continue
        elif user_input.lower().startswith('automode'):
            parts = user_input.split()
            if len(parts) > 1 and parts[1].isdigit():
                max_iterations = int(parts[1])
            else:
                max_iterations = MAX_CONTINUATION_ITERATIONS

            automode = True
            print_colored(f"Entering automode with {max_iterations} iterations. Press Ctrl+C to exit automode at any time.", TOOL_COLOR)
            user_input = input(f"\n{USER_COLOR}You: {Style.RESET_ALL}")

            iteration_count = 0
            try:
                while automode and iteration_count < max_iterations:
                    response, exit_continuation = chat_with_claude(user_input, None, conversation_history, automode, iteration_count + 1, max_iterations)
                    process_and_display_response(response)

                    if exit_continuation or CONTINUATION_EXIT_PHRASE in response:
                        print_colored("Automode completed.", TOOL_COLOR)
                        automode = False
                    else:
                        print_colored(f"Continuation iteration {iteration_count + 1} completed.", TOOL_COLOR)
                        user_input = "Continue with the next step."

                    iteration_count += 1

                    if iteration_count >= max_iterations:
                        print_colored("Max iterations reached. Exiting automode.", TOOL_COLOR)
                        automode = False
            except KeyboardInterrupt:
                print_colored("\nAutomode interrupted by user. Exiting automode.", TOOL_COLOR)
                automode = False
        else:
            response, _ = chat_with_claude(user_input, None, conversation_history, automode)
            process_and_display_response(response)

if __name__ == "__main__":
    main()
