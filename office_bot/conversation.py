import difflib
import json

import frappe
from frappe import _
from frappe.utils import add_to_date, getdate, now_datetime, strip_html

from office_bot import understand
from office_bot.command import ConfirmField, Context, Reply
from office_bot.commands import COMMANDS

STATE_DOCTYPE = "Office Bot Conversation"
STOP_WORDS = {"stop", "cancel", "quit", "exit"}
TIMEOUT_MINUTES = 60


class Conversation:
	"""Runs commands for one user in one chat. The chat is a channel adapter, see channels/raven.py.

	A chat needs: `channel`, `chat_id`, `user`, `is_private`, `url` (or None), `send(reply)`,
	`private_chat()` for where to ask follow-up questions, and `other_chat(chat_id)`.
	"""

	def __init__(self, chat):
		self.chat = chat

	def handle(self, text: str):
		text = text.strip()
		if text.startswith("/"):
			self.start(text[1:])
		elif state := self.get_state():
			self.answer(state, text)
		elif understand.is_enabled():
			self.run_plain_english(text)
		elif self.chat.is_private:
			self.chat.send(Reply(_("Type **/help** to see what I can do.")))

	def run_plain_english(self, text):
		try:
			command = understand.to_command(text, getdate())
		except understand.NotUnderstood as error:
			self.chat.send(Reply(str(error)))
			return
		self.start(command, confirm=True)

	def start(self, text, confirm=False):
		name, _separator, args = text.partition(" ")
		command = COMMANDS.get(name.lower())
		if not command:
			self.chat.send(Reply(unknown_command_text(name)))
			return

		context = Context.for_user(self.chat.user)
		if command.needs_employee and not context.employee:
			self.chat.send(Reply(_("Your user is not linked to an active Employee. Ask HR to link it.")))
			return

		values = self.run_safely(lambda: command.parse(args.strip(), context))
		if values is not None:
			if confirm:
				values["confirm"] = True
			self.advance(command, values, context, origin=self.chat.chat_id)

	def answer(self, state, text):
		if text.lower() in STOP_WORDS:
			frappe.delete_doc(STATE_DOCTYPE, state.name, ignore_permissions=True)
			self.chat.send(Reply(_("Stopped. Nothing was created.")))
			return

		command = COMMANDS[state.command]
		context = Context.for_user(self.chat.user)
		values = json.loads(state.data)
		field = command.get_field(state.step)
		try:
			values.update(field.read(text, values, context))
		except frappe.ValidationError as error:
			self.ask(self.chat, command, field, values, context, problem=error_text(error))
			return

		self.advance(command, values, context, origin=state.origin_chat)

	def advance(self, command, values, context, origin):
		field = command.next_field(values)
		if (field is None or isinstance(field, ConfirmField)) and not self.run_safely(
			lambda: command.validate(values, context) or True
		):
			self.clear_states()
			return

		if not field:
			self.clear_states()
			self.finish(command, values, context, origin)
			return

		chat = self.chat if self.chat.is_private else self.chat.private_chat()
		if chat.chat_id != self.chat.chat_id:
			notice = _("I sent you a direct message to finish this.")
			if chat.url:
				notice += " [" + _("Open chat") + f"]({chat.url})"
			self.chat.send(Reply(notice))

		if self.ask(chat, command, field, values, context):
			self.save_state(chat.chat_id, command.name, field.key, values, origin)
		else:
			self.clear_states()

	def ask(self, chat, command, field, values, context, problem=""):
		prompt = self.run_safely(
			lambda: command.prompt(field, values, context)
			if getattr(chat, "edit_prompts", False)
			else field.prompt(values, context)
		)
		if prompt:
			if problem:
				prompt.text = f"{problem}\n{prompt.text}"
			chat.send(prompt)
		return prompt

	def finish(self, command, values, context, origin):
		if values.get("confirmed") is False:
			self.chat.send(Reply(_("Stopped. Nothing was created.")))
			return

		reply = self.run_safely(lambda: command.run(values, context))
		if not reply:
			return

		self.chat.send(reply)
		if origin != self.chat.chat_id:
			self.chat.other_chat(origin).send(reply)

	def run_safely(self, action):
		"""Run command code and tell the user when it fails, instead of failing the background job."""
		frappe.db.savepoint("office_bot_command")
		try:
			return action()
		except (frappe.ValidationError, frappe.PermissionError) as error:
			frappe.db.rollback(save_point="office_bot_command")
			self.chat.send(Reply(_("Could not do that: {0}").format(error_text(error))))
		except Exception:
			frappe.db.rollback(save_point="office_bot_command")
			frappe.log_error("Office Bot command failed")
			self.chat.send(Reply(_("Something went wrong. The error is logged for your admin.")))

	def get_state(self):
		name = frappe.db.get_value(
			STATE_DOCTYPE,
			{"channel": self.chat.channel, "user": self.chat.user, "chat_id": self.chat.chat_id},
		)
		if not name:
			return None

		state = frappe.get_doc(STATE_DOCTYPE, name)
		if state.expires_at < now_datetime():
			state.delete(ignore_permissions=True)
			return None
		return state

	def save_state(self, chat_id, command, step, values, origin):
		self.clear_states()
		frappe.get_doc(
			{
				"doctype": STATE_DOCTYPE,
				"channel": self.chat.channel,
				"user": self.chat.user,
				"chat_id": chat_id,
				"command": command,
				"step": step,
				"data": json.dumps(values),
				"origin_chat": origin,
				"expires_at": add_to_date(now_datetime(), minutes=TIMEOUT_MINUTES),
			}
		).insert(ignore_permissions=True)

	def clear_states(self):
		frappe.db.delete(STATE_DOCTYPE, {"channel": self.chat.channel, "user": self.chat.user})


def unknown_command_text(name):
	if close := difflib.get_close_matches(name.lower(), COMMANDS, n=1):
		return _("I don't know **/{0}**. Did you mean **/{1}**?").format(name, close[0])
	return _("I don't know **/{0}**. Type **/help** to see the commands.").format(name)


def error_text(error):
	message = error.args[0] if error.args else ""
	if isinstance(message, list | tuple):
		# frappe.msgprint(as_table=True) raises with the rows themselves; its title is only in the message log.
		rows = [", ".join(map(str, row)) if isinstance(row, list | tuple) else str(row) for row in message]
		message = "\n".join([message_title(error), *rows])
	return strip_html(str(message)).strip() or _("Unknown error")


def message_title(error):
	exc_id = getattr(error, "__frappe_exc_id", None)
	return next(
		(
			entry.get("title")
			for entry in frappe.message_log
			if exc_id and entry.get("__frappe_exc_id") == exc_id
		),
		"",
	)
