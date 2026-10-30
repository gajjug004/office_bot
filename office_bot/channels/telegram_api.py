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


def send_message(chat_key, text, reply_markup=None):
	chat_id, _separator, thread_id = chat_key.partition(":")
	payload = {
		"chat_id": chat_id,
		"text": text,
		"parse_mode": "HTML",
		"link_preview_options": {"is_disabled": True},
	}
	if thread_id:
		payload["message_thread_id"] = int(thread_id)
	if reply_markup:
		payload["reply_markup"] = reply_markup
	return call("sendMessage", **payload)


def answer_callback(callback_query_id, text=None):
	"""Stop the tapped button's spinner. Only cosmetic, so a failure must not stop the answer itself."""
	try:
		call("answerCallbackQuery", callback_query_id=callback_query_id, text=text, show_alert=bool(text))
	except TelegramError as error:
		frappe.logger("office_bot").warning(str(error))


def show_picked(chat_id, message_id, label):
	"""Swap a question's buttons for the one that was tapped, so the chat shows the answer. Only cosmetic too."""
	keyboard = [[{"text": f"✓ {label}", "callback_data": "noop"}]]
	try:
		call(
			"editMessageReplyMarkup",
			chat_id=chat_id,
			message_id=message_id,
			reply_markup={"inline_keyboard": keyboard},
		)
	except TelegramError as error:
		frappe.logger("office_bot").warning(str(error))
