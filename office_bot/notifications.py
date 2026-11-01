import frappe
from frappe import _
from frappe.utils import flt, get_fullname, today

from office_bot import channels
from office_bot.command import Reply, count_days, date_range, show_date

APPROVE = "Approve"
REJECT = "Reject"


def on_leave_applied(doc, method=None):
	if doc.leave_approver and doc.leave_approver != get_user(doc.employee):
		frappe.enqueue("office_bot.notifications.notify_approver", leave=doc.name, enqueue_after_commit=True)


def on_leave_change(doc, method=None):
	if doc.has_value_changed("status") and doc.status in ("Approved", "Rejected"):
		frappe.enqueue("office_bot.notifications.notify_employee", leave=doc.name, enqueue_after_commit=True)


def notify_approver(leave: str):
	doc = frappe.get_doc("Leave Application", leave)
	lines = [
		_("**Leave request**"),
		_("**Employee:** {0}").format(doc.employee_name),
		_("**Type:** {0}").format(doc.leave_type),
		_("**From:** {0}").format(show_date(doc.from_date)),
		_("**To:** {0}").format(show_date(doc.to_date)),
		_("**Duration:** {0}").format(count_days(doc.total_leave_days)),
	]
	if doc.description:
		lines.append(_("**Reason:** {0}").format(doc.description))
	actions = [
		(_("Approve"), f"leave:{APPROVE}:{doc.name}"),
		(_("Reject"), f"leave:{REJECT}:{doc.name}"),
	]
	channels.notify_user(
		doc.leave_approver, Reply("\n".join(lines), link=(doc.doctype, doc.name), actions=actions)
	)


def decide_leave(leave: str, action: str):
	"""Approve or reject as the session user. The workflow and HRMS decide whether they may."""
	if action not in (APPROVE, REJECT):
		frappe.throw(_("Unknown action."))
	doc = frappe.get_doc("Leave Application", leave)
	if doc.docstatus != 0 or doc.status != "Open":
		return leave_decided_reply(doc, _("**Leave already {0}**").format(_(doc.status).lower()))

	if frappe.session.user != doc.leave_approver and "HR Manager" not in frappe.get_roles():
		frappe.throw(
			_("Only {0} can decide this leave.").format(get_fullname(doc.leave_approver)),
			frappe.PermissionError,
		)

	if frappe.get_all("Workflow", filters={"document_type": doc.doctype, "is_active": 1}, limit=1):
		from frappe.model.workflow import apply_workflow

		doc = apply_workflow(doc, action)
	else:
		doc.status = "Approved" if action == APPROVE else "Rejected"
		doc.submit()
	return leave_decided_reply(
		doc, _("**Leave {0}** by {1}").format(_(doc.status).lower(), get_fullname(frappe.session.user))
	)


def leave_decided_reply(doc, title):
	lines = [
		title,
		_("**Employee:** {0}").format(doc.employee_name),
		_("**Type:** {0}").format(doc.leave_type),
		_("**Dates:** {0}").format(date_range(doc.from_date, doc.to_date)),
	]
	return Reply("\n".join(lines), link=(doc.doctype, doc.name))


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
