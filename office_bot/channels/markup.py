import re

from frappe.utils import escape_html

BOLD = re.compile(r"\*\*(.+?)\*\*")
# Only http(s) links, so text a user typed cannot become a javascript: link.
LINK = re.compile(r"\[([^\]]+)\]\((https?://[^)\s]+)\)")


def to_html(text, bold_tag="strong"):
	"""Render the bot's **bold** and [label](url) markup as escaped HTML."""
	text = BOLD.sub(rf"<{bold_tag}>\1</{bold_tag}>", escape_html(text))
	return LINK.sub(r'<a href="\2">\1</a>', text)
