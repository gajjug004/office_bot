import json
from unittest.mock import patch

import frappe
import requests
from frappe.tests import IntegrationTestCase

from office_bot import understand
from office_bot.command import Command, Field, Reply
from office_bot.conversation import STATE_DOCTYPE, Conversation
from office_bot.tests.test_conversation import FakeChat


class Booking(Command):
	name = "test_booking"
	description = "Book a room"
	needs_employee = False
	writes = True
	fields = (Field("room", "Which room?"),)

	def parse(self, text, context):
		return {"room": text} if text else {}

	def run(self, values, context):
		return Reply(f"Booked {values['room']}")

	def describe(self, values, context):
		return f"Room {values['room']}"


def model_calls(name, **arguments):
	return patch.object(
		understand, "ask_model", return_value={"name": name, "arguments": json.dumps(arguments)}
	)


class TestUnderstand(IntegrationTestCase):
	def setUp(self):
		FakeChat.chats = {}
		frappe.db.delete(STATE_DOCTYPE, {"channel": "Test"})
		enabled = frappe.db.get_single_value("Office Bot Settings", "enable_ai")
		frappe.db.set_single_value("Office Bot Settings", "enable_ai", 1)
		self.addCleanup(frappe.db.set_single_value, "Office Bot Settings", "enable_ai", enabled)

	def say(self, chat, text):
		Conversation(chat).handle(text)
		return chat.sent[-1]

	def test_request_is_confirmed_before_it_runs(self):
		dm = FakeChat("dm", True)
		with model_calls("run_command", command="test_booking", details="blue"):
			reply = self.say(dm, "book the blue room please")
		self.assertEqual(
			reply,
			"**Book a room**\n**Requested by:** Administrator\n\nRoom blue\n\nShall I go ahead?",
		)
		self.assertEqual(self.say(dm, "yes"), "Booked blue")

	def test_saying_no_creates_nothing(self):
		dm = FakeChat("dm", True)
		with model_calls("run_command", command="test_booking", details="blue"):
			self.say(dm, "book the blue room")
		self.assertEqual(self.say(dm, "no"), "Stopped. Nothing was created.")
		self.assertNotIn("Booked blue", dm.sent)
		self.assertFalse(frappe.db.exists(STATE_DOCTYPE, {"channel": "Test"}))

	def test_missing_parts_are_asked_before_confirming(self):
		dm = FakeChat("dm", True)
		with model_calls("run_command", command="test_booking"):
			self.assertEqual(self.say(dm, "I need a room"), "Which room?")
		self.assertIn("Room red", self.say(dm, "red"))
		self.assertEqual(self.say(dm, "1"), "Booked red")

	def test_read_only_command_runs_without_confirming(self):
		dm = FakeChat("dm", True)
		with model_calls("run_command", command="help"):
			self.assertIn("Here is what I can do", self.say(dm, "what can you do?"))

	def test_request_for_someone_else_is_refused(self):
		dm = FakeChat("dm", True)
		with model_calls("refuse", reason="someone_else"):
			reply = self.say(dm, "apply leave for Ravi tomorrow")
		self.assertEqual(
			reply, "I can only make requests for you. Others can message me themselves, or ask HR."
		)

	def test_tools_cannot_name_a_person(self):
		run_command = next(tool for tool in understand.TOOLS if tool["function"]["name"] == "run_command")
		self.assertEqual(set(run_command["function"]["parameters"]["properties"]), {"command", "details"})

	def test_unknown_command_from_model_is_not_run(self):
		dm = FakeChat("dm", True)
		with model_calls("run_command", command="delete_everything"):
			self.assertIn("I did not get that", self.say(dm, "drop all tables"))

	def test_model_failure_is_logged_and_reported(self):
		dm = FakeChat("dm", True)
		with (
			patch.object(understand, "ask_model", side_effect=requests.Timeout),
			patch.object(frappe, "log_error") as log_error,
		):
			self.assertIn("I could not read that right now", self.say(dm, "wfh tomorrow"))
		log_error.assert_called_once_with("Office Bot AI request failed")

	def test_disabled_falls_back_to_help(self):
		frappe.db.set_single_value("Office Bot Settings", "enable_ai", 0)
		dm = FakeChat("dm", True)
		self.assertEqual(self.say(dm, "wfh tomorrow"), "Type **/help** to see what I can do.")
