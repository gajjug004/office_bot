"""Thin client for the Telegram Bot API. Plain HTTP, so the app needs no Telegram library."""

import frappe
import requests
from frappe import _

API_URL = "https://api.telegram.org/bot{token}/{method}"
# A chat user waits on every call, so fail fast.
TIMEOUT = 10


class TelegramError(frappe.ValidationError):
	pass


def call(method, **payload):
	token = frappe.get_single("Office Bot Settings").get_password("telegram_bot_token", raise_exception=False)
	if not token:
		frappe.throw(
			_("Set the Telegram bot token in Office Bot Settings."), TelegramError, title=_("Telegram")
		)

	try:
		response = requests.post(API_URL.format(token=token, method=method), json=payload, timeout=TIMEOUT)
		body = response.json()
	except requests.RequestException, ValueError:
		body = None
	# Throw outside the except block: the requests error holds the URL, and the URL holds the token.
	if body is None:
		frappe.throw(
			_("Could not reach Telegram for {0}.").format(method), TelegramError, title=_("Telegram")
		)

	if not body.get("ok"):
		frappe.throw(
			_("Telegram {0} failed: {1}").format(method, body.get("description")),
			TelegramError,
			title=_("Telegram"),
		)
	return body["result"]


def send_message(chat_key, text, reply_markup=None, reply_to_message_id=None):
	chat_id, _separator, thread_id = chat_key.partition(":")
	payload = {
		"chat_id": chat_id,
		"text": text,
		"parse_mode": "HTML",
		"link_preview_options": {"is_disabled": True},
	}
	if thread_id:
		payload["message_thread_id"] = int(thread_id)
	if reply_to_message_id:
		payload["reply_to_message_id"] = reply_to_message_id
	if reply_markup:
		payload["reply_markup"] = reply_markup
	return call("sendMessage", **payload)


def edit_message_text(chat_key, message_id, text, reply_markup=None):
	"""Edit the current Telegram prompt and remove its buttons when the flow ends."""
	chat_id, _separator, _thread_id = chat_key.partition(":")
	return call(
		"editMessageText",
		chat_id=chat_id,
		message_id=message_id,
		text=text,
		parse_mode="HTML",
		link_preview_options={"is_disabled": True},
		reply_markup=reply_markup or {"inline_keyboard": []},
	)


def edit_message_reply_markup(chat_key, message_id, picked=None):
	"""Swap a superseded prompt's buttons for the tapped answer, or remove them after a typed reply."""
	chat_id, _separator, _thread_id = chat_key.partition(":")
	keyboard = [[{"text": f"✓ {picked}", "callback_data": "noop"}]] if picked else []
	return call(
		"editMessageReplyMarkup",
		chat_id=chat_id,
		message_id=message_id,
		reply_markup={"inline_keyboard": keyboard},
	)


def answer_callback(callback_query_id, text=None):
	"""Stop the tapped button's spinner. Only cosmetic, so a failure must not stop the answer itself."""
	try:
		# Telegram shows a null text as "null" over the chat, so leave it out.
		alert = {"text": text, "show_alert": True} if text else {}
		call("answerCallbackQuery", callback_query_id=callback_query_id, **alert)
	except TelegramError as error:
		frappe.logger("office_bot").warning(str(error))
