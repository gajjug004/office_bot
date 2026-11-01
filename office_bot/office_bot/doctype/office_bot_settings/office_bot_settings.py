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
		from office_bot.office_bot.doctype.office_bot_telegram_chat.office_bot_telegram_chat import (
			OfficeBotTelegramChat,
		)
		from office_bot.office_bot.doctype.office_bot_telegram_user.office_bot_telegram_user import (
			OfficeBotTelegramUser,
		)

		ai_api_key: DF.Password | None
		ai_base_url: DF.Data | None
		ai_model: DF.Data | None
		default_cash_account: DF.Link | None
		default_company: DF.Link | None
		enable_ai: DF.Check
		enable_raven: DF.Check
		enable_telegram: DF.Check
		hive_sites: DF.Table[OfficeBotHiveSite]
		raven_bot: DF.Link | None
		telegram_bot_token: DF.Password | None
		telegram_bot_username: DF.Data | None
		telegram_chats: DF.Table[OfficeBotTelegramChat]
		telegram_users: DF.Table[OfficeBotTelegramUser]
		telegram_webhook_secret: DF.Password | None
	# end: auto-generated types

	_DOCTYPE_NAME = "Office Bot Settings"
