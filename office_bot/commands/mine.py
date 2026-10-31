import frappe
from frappe import _
from frappe.utils import flt

from office_bot.command import Choice, Command, Field, Reply, date_range, show_date
from office_bot.commands.leave import get_leave_balances


class LeaveBalance(Command):
	name = "balance"
	description = "Show your leave balance"
	usage = "/balance"

	def run(self, values, context):
		balances = get_leave_balances(context.employee, context.today)
		if not balances:
			return Reply(_("You have no leave allocated for today."))
		lines = [_("**Your leave balance**")]
		lines += [f"{row['leave_type']}: {flt(row['balance']):g}" for row in balances]
		return Reply("\n".join(lines))


class MyRequests(Command):
	name = "my"
	description = "Show your upcoming leave and work from home"
	usage = "/my"

	def run(self, values, context):
		requests = get_upcoming_requests(context)
		if not requests:
			return Reply(_("You have no upcoming leave or work from home."))
		return Reply("\n".join([_("**Your upcoming requests**"), *(request.label for request in requests)]))


class CancelRequest(Command):
	name = "cancel"
	aliases = ("withdraw",)
	description = "Withdraw an upcoming work from home or a pending leave"
	usage = "/cancel"
	writes = True
	fields = (
		Field(
			"request",
			"**Withdraw a request**\nWhich one?",
			"choice",
			choices=lambda values, context: [
				Choice(request.label, {"request": [request.doctype, request.name]})
				for request in get_upcoming_requests(context)
				if request.can_withdraw
			],
		),
	)

	def parse(self, text, context):
		if not any(request.can_withdraw for request in get_upcoming_requests(context)):
			frappe.throw(_("You have nothing to withdraw. Approved leave can only be cancelled by HR."))
		return {}

	def run(self, values, context):
		doctype, name = values["request"]
		doc = frappe.get_doc(doctype, name)
		if doc.employee != context.employee:
			frappe.throw(_("You can only withdraw your own requests."), frappe.PermissionError)

		# Employees may not cancel or delete these doctypes; withdrawing your own upcoming request is allowed by policy.
		if doctype == "Attendance Request":
			doc.flags.ignore_permissions = True
			doc.cancel()
		else:
			doc.delete(ignore_permissions=True)
		return Reply(_("**Withdrawn** {0} {1}").format(_(doctype), show_date(doc.from_date)))

	def describe(self, values, context):
		name = values["request"][1]
		return next(request.label for request in get_upcoming_requests(context) if request.name == name)


def get_upcoming_requests(context):
	"""The employee's work from home and leave that end today or later, soonest first."""
	upcoming = {"employee": context.employee, "to_date": [">=", context.today]}
	wfh = frappe.get_all(
		"Attendance Request",
		filters={**upcoming, "docstatus": 1, "reason": "Work From Home"},
		fields=["name", "from_date", "to_date"],
	)
	leaves = frappe.get_all(
		"Leave Application",
		filters={**upcoming, "docstatus": ["<", 2], "status": ["in", ["Open", "Approved"]]},
		fields=["name", "from_date", "to_date", "leave_type", "status", "docstatus"],
	)

	requests = [
		frappe._dict(
			doctype="Attendance Request",
			name=row.name,
			from_date=row.from_date,
			can_withdraw=row.from_date >= context.today,
			label=_("Work from home: {0}").format(date_range(row.from_date, row.to_date)),
		)
		for row in wfh
	]
	requests += [
		frappe._dict(
			doctype="Leave Application",
			name=row.name,
			from_date=row.from_date,
			can_withdraw=row.docstatus == 0,
			label=f"{row.leave_type}: {date_range(row.from_date, row.to_date)} ({_(row.status)})",
		)
		for row in leaves
	]
	return sorted(requests, key=lambda request: request.from_date)
