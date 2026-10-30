# Copyright (c) 2026, Gajendra and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class OfficeBotSettings(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from office_bot.office_bot.doctype.office_bot_hive_site.office_bot_hive_site import OfficeBotHiveSite

		default_cash_account: DF.Link | None
		default_company: DF.Link | None
		hive_sites: DF.Table[OfficeBotHiveSite]
		raven_bot: DF.Link | None
	# end: auto-generated types

	_DOCTYPE_NAME = "Office Bot Settings"
