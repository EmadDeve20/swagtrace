import builtins

from prompt_toolkit import prompt

original_input = builtins.input

builtins.input = prompt

