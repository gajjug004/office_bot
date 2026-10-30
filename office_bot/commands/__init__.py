from office_bot.command import COMMANDS
from office_bot.commands import expense, help, leave, mine, task, wfh

# Use COMMANDS from here: importing the modules above is what registers them.
__all__ = ["COMMANDS", "expense", "help", "leave", "mine", "task", "wfh"]
