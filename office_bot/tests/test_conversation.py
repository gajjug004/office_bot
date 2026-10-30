from typing import ClassVar

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_to_date, now_datetime

from office_bot.command import Choice, Command, Field, Reply, pick_choice
from office_bot.conversation import STATE_DOCTYPE, Conversation


class Order(Command):
	name = "test_order"
	needs_employee = False
	fields = (
		Field(
			"size",
			"Which size?",
			"choice",
			choices=lambda values, context: [
				Choice("Small (S)", {"size": "S"}),
				Choice("Medium (M)", {"size": "M"}),
				Choice("Medium, extra hot (M)", {"size": "M", "hot": True}),
			],
		),
		Field("count", "How many?", "number"),
	)

	def parse(self, text, context):
		return {"size": text.upper()} if text else {}

	def run(self, values, context):
		if values["count"] > 10:
			frappe.throw("Too many")
		return Reply(f"Ordered {values['count']:g} {values['size']}{' hot' if values.get('hot') else ''}")


class FakeChat:
	channel = "Test"
	chats: ClassVar[dict] = {}

	def __init__(self, chat_id, is_private):
		self.chat_id = chat_id
		self.is_private = is_private
		self.user = "Administrator"
		self.url = None
		self.sent = []
		FakeChat.chats[chat_id] = self

	def send(self, reply):
		self.sent.append(reply.text)

	def private_chat(self):
		return FakeChat.chats.get("dm") or FakeChat("dm", True)

	def other_chat(self, chat_id):
		return FakeChat.chats[chat_id]


class TestConversation(IntegrationTestCase):
	def setUp(self):
		FakeChat.chats = {}
		frappe.db.delete(STATE_DOCTYPE, {"channel": "Test"})

	def say(self, chat, text):
		Conversation(chat).handle(text)
		return chat.sent[-1]

	def test_one_liner_runs_without_questions(self):
		dm = FakeChat("dm", True)
		self.say(dm, "/test_order s")
		self.assertEqual(dm.sent, ["How many?"])
		self.assertEqual(self.say(dm, "2"), "Ordered 2 S")
		self.assertFalse(frappe.db.exists(STATE_DOCTYPE, {"channel": "Test"}))

	def test_channel_command_moves_questions_to_dm_and_posts_result_back(self):
		team = FakeChat("team", False)
		self.say(team, "/test_order")
		dm = FakeChat.chats["dm"]
		self.assertEqual(team.sent, ["I sent you a direct message to finish this."])
		self.assertEqual(dm.sent, ["Which size?"])

		self.assertEqual(
			self.say(team, "3"), "I sent you a direct message to finish this.", "answers only count in the DM"
		)
		self.say(dm, "3")
		self.assertEqual(self.say(dm, "1"), "Ordered 1 M hot")
		self.assertEqual(team.sent[-1], "Ordered 1 M hot")

	def test_bad_answer_asks_again(self):
		dm = FakeChat("dm", True)
		self.say(dm, "/test_order")
		self.assertEqual(self.say(dm, "9"), "Pick a number from the list.\nWhich size?")
		self.say(dm, "small")
		self.assertEqual(self.say(dm, "lots"), "Send the amount as a number, like 250.\nHow many?")

	def test_validation_error_is_reported_and_state_cleared(self):
		dm = FakeChat("dm", True)
		self.say(dm, "/test_order m")
		self.assertEqual(self.say(dm, "50"), "Could not do that: Too many")
		self.assertFalse(frappe.db.exists(STATE_DOCTYPE, {"channel": "Test"}))

	def test_stop_and_expiry(self):
		dm = FakeChat("dm", True)
		self.say(dm, "/test_order")
		self.assertEqual(self.say(dm, "stop"), "Stopped. Nothing was created.")

		self.say(dm, "/test_order")
		frappe.db.set_value(
			STATE_DOCTYPE, {"channel": "Test"}, "expires_at", add_to_date(now_datetime(), minutes=-1)
		)
		self.assertEqual(self.say(dm, "1"), "Type **/help** to see what I can do.")

	def test_unknown_command(self):
		dm = FakeChat("dm", True)
		self.assertIn("I don't know **/nope**", self.say(dm, "/nope"))


class TestPickChoice(IntegrationTestCase):
	choices = (
		Choice("Same day (Fri 30 Oct)", {}),
		Choice("Same day, half day (Fri 30 Oct)", {}),
		Choice("+1 day (Sat 31 Oct)", {}),
		Choice("Sick Leave (6 left)", {}),
	)

	def test_matches(self):
		pick = lambda text: pick_choice(text, list(self.choices))  # noqa: E731
		self.assertIs(pick("2"), self.choices[1])
		self.assertIs(pick("same day"), self.choices[0])
		self.assertIs(pick("+1"), self.choices[2])
		self.assertIs(pick("sick"), self.choices[3])
		self.assertIsNone(pick("same"), "ambiguous prefix")
		self.assertIsNone(pick("5"))
