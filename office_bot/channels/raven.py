import frappe
from frappe.utils import escape_html, get_url

from office_bot.channels.markup import to_html
from office_bot.command import hint_sentence
from office_bot.conversation import Conversation

CHANNEL = "Raven"


def on_message(doc, method=None):
	"""Raven Message after_insert. Hands bot commands to a job so sending a message never waits on the bot."""
	if doc.is_bot_message or doc.message_type != "Text" or not doc.content:
		return

	bot = get_bot()
	if not bot or not (
		is_bot_dm(bot, doc.channel_id) or is_command_for_bot(bot, doc) or is_mention_of_bot(bot, doc)
	):
		return

	frappe.enqueue(
		"office_bot.channels.raven.handle_message",
		message_id=doc.name,
		enqueue_after_commit=True,
	)


def handle_message(message_id: str):
	message = frappe.get_doc("Raven Message", message_id)
	Conversation(RavenChat(get_bot(), message.channel_id, message.owner)).handle(message.content)


def notify_user(user, reply):
	"""DM a user from the bot. Users who are not on Raven are skipped."""
	bot = get_bot()
	if bot and frappe.db.exists("Raven User", {"user": user, "enabled": 1}):
		RavenChat(bot, bot.create_direct_message_channel(user), user).send(reply)


def broadcast(reply):
	"""Post to every channel the bot was added to. Adding the bot to a channel is the setting."""
	bot = get_bot()
	if not bot:
		return

	member_of = frappe.get_all(
		"Raven Channel Member", filters={"user_id": bot.raven_user}, pluck="channel_id"
	)
	channels = frappe.get_all(
		"Raven Channel",
		filters={"name": ["in", member_of], "is_direct_message": 0, "is_archived": 0},
		pluck="name",
	)
	for channel in channels:
		RavenChat(bot, channel, None).send(reply)


class RavenChat:
	channel = CHANNEL

	def __init__(self, bot, chat_id, user):
		self.bot = bot
		self.chat_id = chat_id
		self.user = user

	@property
	def url(self):
		return get_url(f"/raven/dm-channel/{self.chat_id}") if self.is_private else None

	@property
	def is_private(self):
		return bool(frappe.get_cached_value("Raven Channel", self.chat_id, "is_direct_message"))

	def send(self, reply):
		doctype, name = reply.link or (None, None)
		self.bot.send_message(self.chat_id, render_html(reply), link_doctype=doctype, link_document=name)

	def private_chat(self):
		return RavenChat(self.bot, self.bot.create_direct_message_channel(self.user), self.user)

	def other_chat(self, chat_id):
		return RavenChat(self.bot, chat_id, self.user)


def get_bot():
	name = frappe.db.get_single_value("Office Bot Settings", "raven_bot")
	return frappe.get_cached_doc("Raven Bot", name) if name else None


def is_bot_dm(bot, channel_id):
	channel = frappe.get_cached_value(
		"Raven Channel", channel_id, ["is_direct_message", "dm_user_1", "dm_user_2"], as_dict=True
	)
	return bool(
		channel and channel.is_direct_message and bot.raven_user in (channel.dm_user_1, channel.dm_user_2)
	)


def is_command_for_bot(bot, message):
	return message.content.lstrip().startswith("/") and bool(bot.is_member(message.channel_id))


def is_mention_of_bot(bot, message):
	return any(mention.user == bot.raven_user for mention in message.mentions)


def render_html(reply):
	html = [f"<p>{to_html(line)}</p>" for line in reply.text.split("\n") if line.strip()]
	if reply.choices:
		html.append("<ol>" + "".join(f"<li>{to_html(choice)}</li>" for choice in reply.choices) + "</ol>")
	if hint := hint_sentence(reply, numbered=True):
		html.append(f"<p><em>{escape_html(hint)}</em></p>")
	return "".join(html)
