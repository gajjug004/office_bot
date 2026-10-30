import json

import frappe
from frappe import _
from frappe.utils import add_to_date, now_datetime, strip_html

from office_bot.command import Context, Reply
from office_bot.commands import COMMANDS

STATE_DOCTYPE = "Office Bot Conversation"
STOP_WORDS = {"stop", "cancel", "quit", "exit"}
TIMEOUT_MINUTES = 60


class Conversation:
	"""Runs commands for one user in one chat. The chat is a channel adapter, see channels/raven.py.

	A chat needs: `channel`, `chat_id`, `user`, `is_private`, `url` (or None), `send(reply)`,
	`private_chat()` for the user's DM with the bot, and `other_chat(chat_id)`.
	"""

	def __init__(self, chat):
		self.chat = chat

	def handle(self, text: str):
		text = text.strip()
		if text.startswith("/"):
			self.start(text[1:])
		elif state := self.get_state():
			self.answer(state, text)
		elif self.chat.is_private:
			self.chat.send(Reply(_("Type **/help** to see what I can do.")))

	def start(self, text):
		name, _separator, args = text.partition(" ")
		command = COMMANDS.get(name.lower())
		if not command:
			self.chat.send(
				Reply(_("I don't know **/{0}**. Type **/help** to see the commands.").format(name))
			)
			return

		context = Context.for_user(self.chat.user)
		if command.needs_employee and not context.employee:
			self.chat.send(Reply(_("Your user is not linked to an active Employee. Ask HR to link it.")))
			return

		values = self.run_safely(lambda: command.parse(args.strip(), context))
		if values is not None:
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
			self.ask(self.chat, field, values, context, problem=error_text(error))
			return

		self.advance(command, values, context, origin=state.origin_chat)

	def advance(self, command, values, context, origin):
		field = command.next_field(values)
		if not field:
			self.clear_states()
			self.finish(command, values, context, origin)
			return

		chat = self.chat
		if not chat.is_private:
			chat = self.chat.private_chat()
			notice = _("I sent you a direct message to finish this.")
			if chat.url:
				notice += " [" + _("Open chat") + f"]({chat.url})"
			self.chat.send(Reply(notice))

		if self.ask(chat, field, values, context):
			self.save_state(chat.chat_id, command.name, field.key, values, origin)
		else:
			self.clear_states()

	def ask(self, chat, field, values, context, problem=""):
		prompt = self.run_safely(lambda: field.prompt(values, context))
		if prompt:
			if problem:
				prompt.text = f"{problem}\n{prompt.text}"
			chat.send(prompt)
		return prompt

	def finish(self, command, values, context, origin):
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


def error_text(error):
	return strip_html(str(error)) or _("Unknown error")
