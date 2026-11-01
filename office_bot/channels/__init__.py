import frappe
from frappe.utils import cint

from office_bot.channels import raven, telegram


def notify_user(user, reply):
	for channel in enabled_channels():
		try:
			channel.notify_user(user, reply)
		except Exception:
			frappe.log_error("Office Bot notification failed", message=f"{channel.CHANNEL}: {user}")


def broadcast(reply):
	for channel in enabled_channels():
		try:
			channel.broadcast(reply)
		except Exception:
			frappe.log_error("Office Bot notification failed", message=f"{channel.CHANNEL}: broadcast")


def enabled_channels():
	settings = frappe.get_cached_doc("Office Bot Settings")
	enabled = (
		(raven, cint(settings.enable_raven) and settings.raven_bot),
		(telegram, cint(settings.enable_telegram) and settings.telegram_bot_username),
	)
	return [channel for channel, configured in enabled if configured]
