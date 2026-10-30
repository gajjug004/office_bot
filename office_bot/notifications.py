import frappe
from frappe import _
from frappe.utils import flt, today

from office_bot import channels
from office_bot.command import Reply, count_days, date_range


def on_leave_applied(doc, method=None):
	if doc.leave_approver and doc.leave_approver != get_user(doc.employee):
		frappe.enqueue("office_bot.notifications.notify_approver", leave=doc.name, enqueue_after_commit=True)


def on_leave_change(doc, method=None):
	if doc.has_value_changed("status") and doc.status in ("Approved", "Rejected"):
		frappe.enqueue("office_bot.notifications.notify_employee", leave=doc.name, enqueue_after_commit=True)


def notify_approver(leave: str):
	doc = frappe.get_doc("Leave Application", leave)
	lines = [
		_("**{0}** applied for {1}").format(doc.employee_name, doc.leave_type),
		f"{date_range(doc.from_date, doc.to_date)}, {count_days(doc.total_leave_days)}",
	]
	if doc.description:
		lines.append(_("Reason: {0}").format(doc.description))
	if frappe.get_all("Workflow", filters={"document_type": doc.doctype, "is_active": 1}, limit=1):
		lines.append(_("Open it to approve or reject. In Raven, use the workflow menu on the card."))
	channels.notify_user(doc.leave_approver, Reply("\n".join(lines), link=(doc.doctype, doc.name)))


def notify_employee(leave: str):
	doc = frappe.get_doc("Leave Application", leave)
	if user := get_user(doc.employee):
		text = _("**Your leave was {0}**\n{1}: {2}").format(
			_(doc.status).lower(), doc.leave_type, date_range(doc.from_date, doc.to_date)
		)
		channels.notify_user(user, Reply(text, link=(doc.doctype, doc.name)))


def post_leave_today():
	leaves = frappe.get_all(
		"Leave Application",
		filters={
			"docstatus": 1,
			"status": "Approved",
			"from_date": ["<=", today()],
			"to_date": [">=", today()],
		},
		fields=["employee_name", "leave_type", "from_date", "to_date", "half_day"],
		order_by="employee_name asc",
	)
	lines = [
		f"**{row.employee_name}**, {row.leave_type} ({date_range(row.from_date, row.to_date)}){_(', half day') if row.half_day else ''}"
		for row in leaves
	]
	post_list(_("**On leave today**"), lines)


def post_wfh_today():
	requests = frappe.get_all(
		"Attendance Request",
		filters={
			"docstatus": 1,
			"reason": "Work From Home",
			"from_date": ["<=", today()],
			"to_date": [">=", today()],
		},
		fields=["employee_name", "from_date", "to_date", "custom_total_wfh_days"],
		order_by="employee_name asc",
	)
	lines = [
		f"**{row.employee_name}** ({date_range(row.from_date, row.to_date)}){_(', half day') if row.custom_total_wfh_days == 0.5 else ''}"
		for row in requests
	]
	post_list(_("**Working from home today**"), lines)


def post_list(title, lines):
	if lines:
		channels.broadcast(Reply("\n".join([title, *lines])))


def get_user(employee):
	return frappe.db.get_value("Employee", employee, "user_id")
