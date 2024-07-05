# config.py

from colorama import Fore

USER_COLOR = Fore.WHITE
CLAUDE_COLOR = Fore.BLUE
TOOL_COLOR = Fore.YELLOW
RESULT_COLOR = Fore.GREEN

CONTINUATION_EXIT_PHRASE = "AUTOMODE_COMPLETE"
MAX_CONTINUATION_ITERATIONS = 25

def print_colored(text, color):
    print(f"{color}{text}{Style.RESET_ALL}")
