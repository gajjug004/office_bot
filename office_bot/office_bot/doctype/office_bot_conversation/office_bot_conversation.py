# Copyright (c) 2026, Gajendra and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class OfficeBotConversation(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		channel: DF.Data
		chat_id: DF.Data
		command: DF.Data
		data: DF.JSON | None
		expires_at: DF.Datetime
		origin_chat: DF.Data | None
		step: DF.Data
		user: DF.Link
	# end: auto-generated types

	_DOCTYPE_NAME = "Office Bot Conversation"
