import frappe
from frappe import _

from office_bot.command import Command, Reply, count_days, date_range
from office_bot.commands.time_off import from_date_field, parse_time_off, to_date_field, total_days


class WorkFromHome(Command):
	name = "wfh"
	description = "Apply for work from home"
	usage = "/wfh tomorrow, /wfh 3 nov to 5 nov, /wfh today half"
	fields = (
		from_date_field("**Work from home**\nFrom which date?"),
		to_date_field(),
	)

	def parse(self, text, context):
		values, _rest = parse_time_off(text, context)
		return values

	def run(self, values, context):
		check_no_pending_leave(context.employee, values["from_date"], values["to_date"])
		days = total_days(values)
		# Store the WFH days in a custom field, not Half Day: Half Day would mark
		# the attendance half present, half absent.
		request = frappe.get_doc(
			{
				"doctype": "Attendance Request",
				"employee": context.employee,
				"from_date": values["from_date"],
				"to_date": values["to_date"],
				"reason": "Work From Home",
				"custom_total_wfh_days": days,
			}
		).insert()
		# Employees can create but not submit Attendance Requests; WFH from the bot is auto-approved.
		request.flags.ignore_permissions = True
		request.submit()

		return Reply(
			_("**Work from home submitted** for {0}\n{1}, {2}").format(
				request.employee_name, date_range(values["from_date"], values["to_date"]), count_days(days)
			),
			link=(request.doctype, request.name),
		)


def check_no_pending_leave(employee, from_date, to_date):
	"""HRMS marks WFH attendance over a pending leave, and that leave can then never be approved or rejected."""
	leave = frappe.db.get_value(
		"Leave Application",
		{
			"employee": employee,
			"docstatus": 0,
			"status": "Open",
			"from_date": ["<=", to_date],
			"to_date": [">=", from_date],
		},
		["leave_type", "from_date", "to_date"],
		as_dict=True,
	)
	if leave:
		frappe.throw(
			_("You have a pending {0} on {1}. Withdraw it with /cancel first.").format(
				leave.leave_type, date_range(leave.from_date, leave.to_date)
			)
		)
