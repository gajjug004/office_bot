import traceback
from itertools import count
from unittest.mock import patch

import frappe
import requests
from frappe.tests import IntegrationTestCase

from office_bot.channels import telegram
from office_bot.channels.telegram_api import TelegramError
from office_bot.channels.telegram_api import call as real_call
from office_bot.command import Reply
from office_bot.conversation import STATE_DOCTYPE
from office_bot.tests import test_conversation  # registers /test_order

SECRET = "test-secret"
GROUP = -100500
ME = {"id": 4242, "username": "tester", "is_bot": False}


class TestTelegram(IntegrationTestCase):
	def setUp(self):
		settings = frappe.get_single("Office Bot Settings")
		settings.telegram_webhook_secret = SECRET
		settings.telegram_bot_username = "office_test_bot"
		settings.set("telegram_users", [{"user": "Administrator", "telegram_username": "@Tester"}])
		settings.set("telegram_chats", [{"chat_id": str(GROUP), "label": "Team"}])
		settings.save()
		frappe.db.delete(STATE_DOCTYPE, {"channel": "Telegram"})

		self.calls = []
		message_ids = count(1)

		def fake_call(method, **payload):
			self.calls.append((method, payload))
			return {"message_id": next(message_ids)}

		patcher = patch("office_bot.channels.telegram_api.call", side_effect=fake_call)
		patcher.start()
		self.addCleanup(patcher.stop)

	def post(self, update, secret=SECRET):
		with (
			patch("office_bot.channels.telegram.frappe.get_request_header", return_value=secret),
			patch("office_bot.channels.telegram.frappe.enqueue") as enqueue,
		):
			telegram.webhook(**update)
		for call in enqueue.call_args_list:
			telegram.handle(**call.kwargs)
		return enqueue

	def text(self, chat_id, text, sender=ME, reply_to_bot=False, secret=SECRET):
		chat_type = "private" if chat_id > 0 else "supergroup"
		message = {"message_id": 1, "chat": {"id": chat_id, "type": chat_type}, "from": sender, "text": text}
		if reply_to_bot:
			message["reply_to_message"] = {"from": {"is_bot": True, "username": "office_test_bot"}}
		return self.post({"update_id": 1, "message": message}, secret=secret)

	def tap(self, chat_id, message_id, number, sender=ME):
		message = {
			"message_id": message_id,
			"chat": {"id": chat_id, "type": "private" if chat_id > 0 else "supergroup"},
			"reply_markup": {"inline_keyboard": [[{"text": "Small (S)", "callback_data": "pick:1"}]]},
		}
		callback = {"id": "cb1", "from": sender, "message": message, "data": f"pick:{number}"}
		return self.post({"update_id": 2, "callback_query": callback})

	def sent(self, method="sendMessage"):
		return [payload for name, payload in self.calls if name == method]

	def test_wrong_secret_is_refused(self):
		with self.assertRaises(frappe.PermissionError):
			self.text(ME["id"], "/test_order", secret="nope")

	def test_unknown_sender_is_told_their_id(self):
		stranger = {"id": 777, "username": "someone"}
		self.assertFalse(self.text(777, "/test_order", sender=stranger).called)
		self.assertIn("<code>777</code>", self.sent()[-1]["text"])

	def test_username_match_saves_the_telegram_id(self):
		self.text(ME["id"], "/test_order")
		self.assertEqual(
			frappe.db.get_value("Office Bot Telegram User", {"user": "Administrator"}, "telegram_user_id"),
			"4242",
		)

	def test_choices_become_buttons_and_a_tap_answers(self):
		self.text(ME["id"], "/test_order")
		question = self.sent()[-1]
		self.assertEqual(
			question["reply_markup"]["inline_keyboard"][0][0],
			{"text": "Small (S)", "callback_data": "pick:1"},
		)

		self.tap(ME["id"], message_id=1, number=1)
		self.assertEqual(
			self.sent("editMessageReplyMarkup")[-1]["reply_markup"]["inline_keyboard"][0][0]["text"],
			"✓ Small (S)",
		)
		self.assertEqual(self.sent()[-1]["text"], "How many?")

		self.text(ME["id"], "3")
		self.assertEqual(self.sent()[-1]["text"], "Ordered 3 S")

	def test_tap_on_an_old_question_is_refused(self):
		self.text(ME["id"], "/test_order")
		self.text(ME["id"], "/test_order")
		self.tap(ME["id"], message_id=1, number=1)
		self.assertIn("not for you", self.sent("answerCallbackQuery")[-1]["text"])

	def test_group_keeps_questions_in_the_group(self):
		self.text(GROUP, "/test_order@office_test_bot s")
		self.assertEqual(
			self.sent()[-1],
			{
				"chat_id": str(GROUP),
				"text": "How many?",
				"parse_mode": "HTML",
				"link_preview_options": {"is_disabled": True},
				"reply_markup": {"force_reply": True},
			},
		)

		self.assertFalse(self.text(GROUP, "2").called, "plain group chatter is ignored")
		self.text(GROUP, "2", reply_to_bot=True)
		self.assertEqual(self.sent()[-1]["text"], "Ordered 2 S")

	def test_unlisted_group_is_told_its_id(self):
		self.assertFalse(self.text(-999, "/test_order").called)
		self.assertIn("<code>-999</code>", self.sent()[-1]["text"])

	def test_unreachable_telegram_error_does_not_carry_the_token(self):
		frappe.get_single("Office Bot Settings").update({"telegram_bot_token": "123:SECRET"}).save()
		leak = requests.ConnectionError("https://api.telegram.org/bot123:SECRET/getMe")
		with patch("office_bot.channels.telegram_api.requests.post", side_effect=leak):
			with self.assertRaises(TelegramError) as raised:
				real_call("getMe")
		self.assertIsNone(raised.exception.__context__)
		self.assertNotIn("SECRET", "".join(traceback.format_exception(raised.exception)))

	def test_connection_status(self):
		ours = frappe.utils.get_url(telegram.WEBHOOK_PATH)
		for url, expected in (("", False), ("https://other.example.com/hook", False), (ours, True)):
			with patch("office_bot.channels.telegram_api.call", return_value={"url": url}):
				self.assertEqual(telegram.connection_status(), {"url": url, "this_site": expected})

	def test_render_link_and_numbered_multiple_choice(self):
		text, markup = telegram.render(
			Reply("**Done** <ok>", link=("User", "Administrator")), is_private=True
		)
		self.assertTrue(text.startswith("<b>Done</b> &lt;ok&gt;\n<a href="))
		self.assertIsNone(markup)

		text, markup = telegram.render(
			Reply("Who?", choices=["Ann", "Bo"], asks=True, multiple=True), is_private=True
		)
		self.assertIn("1. Ann\n2. Bo", text)
		self.assertIsNone(markup)
