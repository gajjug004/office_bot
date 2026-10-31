import frappe
from frappe import _

from office_bot.command import COMMANDS, Command, Reply

ORDER = ("wfh", "leave", "expense", "task", "balance", "my", "cancel", "help")


class Help(Command):
	name = "help"
	aliases = (
		"start",
		"ping",
	)
	description = "Show what I can do"
	usage = "/help"
	needs_employee = False

	def run(self, values, context):
		commands = [COMMANDS[name] for name in ORDER]
		lines = [_("**Here is what I can do**")]
		lines += [f"**/{command.name}**: {_(command.description)}. {command.usage}" for command in commands]
		lines.append(_("Leave something out and I will ask for it. Type **stop** to end a question."))
		if frappe.db.get_single_value("Office Bot Settings", "enable_ai"):
			lines.append(
				_("Or just tell me in your own words, like **wfh tomorrow** or **sick leave today, fever**.")
			)
		return Reply("\n".join(lines))
