import hmac
import re

import frappe
from frappe import _
from frappe.utils import escape_html, get_url, get_url_to_form

from office_bot.channels import telegram_api
from office_bot.channels.markup import to_html
from office_bot.channels.telegram_api import TelegramError
from office_bot.command import hint_sentence
from office_bot.commands import COMMANDS
from office_bot.commands.help import ORDER
from office_bot.conversation import Conversation

CHANNEL = "Telegram"
WEBHOOK_PATH = "/api/method/office_bot.channels.telegram.webhook"
BOT_SUFFIX = re.compile(r"^(/\w+)@\w+")
PROMPT_TIMEOUT = 60 * 60


@frappe.whitelist(allow_guest=True, methods=["POST"])
def webhook(**update):
	"""Telegram posts every message and button tap the bot can see here."""
	check_secret()
	if callback := update.get("callback_query"):
		receive_tap(callback)
	elif (message := update.get("message")) and message.get("text"):
		receive_text(message)


@frappe.whitelist(methods=["POST"])
def connect():
	"""Point the bot's webhook at this site and fill its command menu."""
	frappe.only_for("System Manager")
	settings = frappe.get_single("Office Bot Settings")
	bot = telegram_api.call("getMe")
	secret = settings.get_password("telegram_webhook_secret", raise_exception=False) or frappe.generate_hash(
		length=32
	)
	settings.telegram_webhook_secret = secret
	settings.telegram_bot_username = bot["username"]
	settings.save()

	url = get_url(WEBHOOK_PATH)
	telegram_api.call(
		"setWebhook", url=url, secret_token=secret, allowed_updates=["message", "callback_query"]
	)
	commands = [{"command": name, "description": _(COMMANDS[name].description)} for name in ORDER]
	telegram_api.call("setMyCommands", commands=commands)
	return url


def handle(chat_key: str, text: str, tap: dict | None = None):
	if tap:
		telegram_api.show_picked(chat_key.partition(":")[0], tap["message_id"], tap["label"])
	Conversation(TelegramChat(chat_key, frappe.session.user)).handle(text)


def notify_user(user, reply):
	"""DM a user. Telegram only lets bots message people who have opened a chat with them."""
	telegram_id = frappe.db.get_value(
		"Office Bot Telegram User", {"parenttype": "Office Bot Settings", "user": user}, "telegram_user_id"
	)
	if not telegram_id:
		return
	try:
		TelegramChat(telegram_id, user).send(reply)
	except TelegramError:
		frappe.logger("office_bot").warning(
			f"Could not message {user} on Telegram. They may not have started the bot."
		)


def broadcast(reply):
	for chat_id in frappe.get_all(
		"Office Bot Telegram Chat", filters={"parenttype": "Office Bot Settings"}, pluck="chat_id"
	):
		TelegramChat(chat_id, None).send(reply)


class TelegramChat:
	"""A Telegram chat. `chat_id` is "<chat>" or "<chat>:<topic>" for a topic in a forum group."""

	channel = CHANNEL
	url = None

	def __init__(self, chat_id, user):
		self.chat_id = str(chat_id)
		self.user = user

	@property
	def is_private(self):
		return not self.chat_id.startswith("-")

	def send(self, reply):
		text, markup = render(reply, self.is_private)
		sent = telegram_api.send_message(self.chat_id, text, markup)
		if reply.asks:
			frappe.cache.set_value(
				prompt_key(self.chat_id, self.user), sent["message_id"], expires_in_sec=PROMPT_TIMEOUT
			)

	def private_chat(self):
		# A bot cannot message someone who never opened a chat with it, so questions stay in the group.
		return self

	def other_chat(self, chat_id):
		return TelegramChat(chat_id, self.user)


def receive_text(message):
	chat = message["chat"]
	text = BOT_SUFFIX.sub(r"\1", message["text"].strip())
	is_command = text.startswith("/")
	if not is_allowed_chat(chat):
		if is_command:
			telegram_api.send_message(get_chat_key(message), unknown_group_text(chat))
		return
	if not (chat["type"] == "private" or is_command or is_reply_to_bot(message)):
		return

	user = find_user(message["from"])
	if not user:
		if is_command:
			telegram_api.send_message(get_chat_key(message), unknown_user_text(message["from"]))
		return
	enqueue_as(user, chat_key=get_chat_key(message), text=text)


def receive_tap(callback):
	message = callback.get("message")
	data = callback.get("data") or ""
	if not message or not data.startswith("pick:"):
		telegram_api.answer_callback(callback["id"])
		return

	user = find_user(callback["from"])
	if not user or not is_allowed_chat(message["chat"]):
		telegram_api.answer_callback(callback["id"], unknown_user_text(callback["from"], html=False))
		return

	# Telegram only accepts an answer to a tap for a few seconds, so answer here, not in the job.
	chat_key = get_chat_key(message)
	if not is_current_prompt(chat_key, user, message["message_id"]):
		telegram_api.answer_callback(callback["id"], _("This question is not for you, or it has timed out."))
		return
	telegram_api.answer_callback(callback["id"])

	tap = {"message_id": message["message_id"], "label": button_label(message, data)}
	enqueue_as(user, chat_key=chat_key, text=data.removeprefix("pick:"), tap=tap)


def enqueue_as(user, **kwargs):
	# The job runs as the session user, so set the sender first. Their own permissions then apply.
	frappe.set_user(user)
	frappe.enqueue("office_bot.channels.telegram.handle", **kwargs)


def check_secret():
	secret = frappe.get_single("Office Bot Settings").get_password(
		"telegram_webhook_secret", raise_exception=False
	)
	sent = frappe.get_request_header("X-Telegram-Bot-Api-Secret-Token") or ""
	if not secret or not hmac.compare_digest(sent, secret):
		frappe.throw(_("Not permitted"), frappe.PermissionError)


def find_user(sender):
	"""The Frappe user mapped to a Telegram sender, by ID, or by username the first time."""
	telegram_id, username = str(sender["id"]), (sender.get("username") or "").lower()
	rows = frappe.get_all(
		"Office Bot Telegram User",
		filters={"parenttype": "Office Bot Settings"},
		fields=["name", "user", "telegram_user_id", "telegram_username"],
	)
	row = next((row for row in rows if row.telegram_user_id == telegram_id), None)
	if not row and username:
		row = next(
			(row for row in rows if (row.telegram_username or "").lstrip("@").lower() == username), None
		)
		if row:
			frappe.db.set_value("Office Bot Telegram User", row.name, "telegram_user_id", telegram_id)
	if row and frappe.db.get_value("User", row.user, "enabled"):
		return row.user


def is_allowed_chat(chat):
	if chat["type"] == "private":
		return True
	return frappe.db.exists(
		"Office Bot Telegram Chat", {"parenttype": "Office Bot Settings", "chat_id": str(chat["id"])}
	)


def is_reply_to_bot(message):
	sender = (message.get("reply_to_message") or {}).get("from") or {}
	return sender.get("is_bot") and sender.get("username") == frappe.db.get_single_value(
		"Office Bot Settings", "telegram_bot_username"
	)


def get_chat_key(message):
	if message.get("is_topic_message") and message.get("message_thread_id"):
		return f"{message['chat']['id']}:{message['message_thread_id']}"
	return str(message["chat"]["id"])


def button_label(message, data):
	rows = (message.get("reply_markup") or {}).get("inline_keyboard") or []
	return next((button["text"] for row in rows for button in row if button.get("callback_data") == data), "")


def is_current_prompt(chat_key, user, message_id):
	"""Taps on an older question's buttons, or on someone else's, must not answer the current one."""
	return frappe.cache.get_value(prompt_key(chat_key, user)) == message_id


def prompt_key(chat_key, user):
	return f"office_bot:telegram_prompt:{chat_key}:{user}"


def unknown_user_text(sender, html=True):
	telegram_id = f"<code>{sender['id']}</code>" if html else sender["id"]
	return _(
		"I don't know who you are yet. Ask HR to add your Telegram ID {0} in Office Bot Settings."
	).format(telegram_id)


def unknown_group_text(chat):
	return _(
		"This group is not set up yet. Ask HR to add chat ID {0} under Telegram Groups in Office Bot Settings."
	).format(f"<code>{chat['id']}</code>")


def render(reply, is_private):
	"""Telegram HTML, plus buttons for the choices, or a reply box for typed answers in groups."""
	lines = [to_html(line, bold_tag="b") for line in reply.text.split("\n") if line.strip()]
	buttons = bool(reply.choices) and not reply.multiple
	if reply.choices and not buttons:
		lines += [f"{number}. {escape_html(choice)}" for number, choice in enumerate(reply.choices, 1)]

	hint = hint_sentence(reply, numbered=not buttons)
	if hint and buttons and not is_private:
		hint += " " + _("Reply to this message to type it.")
	if hint:
		lines.append(f"<i>{escape_html(hint)}</i>")
	if reply.link:
		doctype, name = reply.link
		lines.append(
			f'<a href="{get_url_to_form(doctype, name)}">{escape_html(_(doctype))} {escape_html(name)}</a>'
		)

	markup = None
	if buttons:
		markup = {
			"inline_keyboard": [
				[{"text": choice, "callback_data": f"pick:{number}"}]
				for number, choice in enumerate(reply.choices, 1)
			]
		}
	elif reply.asks and not is_private:
		markup = {"force_reply": True}
	return "\n".join(lines), markup
