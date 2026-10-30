import frappe

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
	return [
		channel
		for channel, enabled in ((raven, settings.raven_bot), (telegram, settings.telegram_bot_username))
		if enabled
	]
