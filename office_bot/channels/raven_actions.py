"""Raven Message Action functions. They open as a form from any message's Actions menu."""

import frappe
from frappe import _
from frappe.utils import strip_html

from office_bot.command import Context
from office_bot.commands import COMMANDS


@frappe.whitelist(methods=["POST"])
def apply_wfh(from_date: str, to_date: str | None = None, half_day: bool = False):
	return run_command("wfh", {"from_date": from_date, "to_date": to_date or from_date, "half_day": half_day})


@frappe.whitelist(methods=["POST"])
def apply_leave(
	leave_type: str,
	from_date: str,
	to_date: str | None = None,
	half_day: bool = False,
	description: str | None = None,
):
	values = {
		"leave_type": leave_type,
		"from_date": from_date,
		"to_date": to_date or from_date,
		"half_day": half_day,
		"description": description,
	}
	return run_command("leave", values)


@frappe.whitelist(methods=["POST"])
def record_expense(amount: float, category: str, remarks: str, expense_date: str | None = None):
	values = {"amount": amount, "category": category, "remarks": remarks, "expense_date": expense_date}
	return run_command("expense", values)


def run_command(name, values):
	from raven.api.document_link import get as get_document_link

	context = Context.for_user(frappe.session.user)
	if not context.employee:
		frappe.throw(_("Your user is not linked to an active Employee. Ask HR to link it."))

	command = COMMANDS[name]
	command.validate(values, context)
	reply = command.run(values, context)
	doctype, docname = reply.link
	return {
		"message": strip_html(reply.text).replace("**", ""),
		"doctype": doctype,
		"document": docname,
		"link": get_document_link(doctype, docname, with_site_url=False),
	}
