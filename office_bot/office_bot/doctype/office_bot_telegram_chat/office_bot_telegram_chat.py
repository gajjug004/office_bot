# Copyright (c) 2026, Gajendra and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class OfficeBotTelegramChat(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		chat_id: DF.Data
		label: DF.Data | None
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
	# end: auto-generated types

	_DOCTYPE_NAME = "Office Bot Telegram Chat"
