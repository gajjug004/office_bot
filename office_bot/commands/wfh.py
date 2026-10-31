import frappe
from frappe import _

from office_bot.command import Command, Reply, count_days, date_range, show_date
from office_bot.commands.time_off import from_date_field, parse_time_off, to_date_field, total_days


class WorkFromHome(Command):
	name = "wfh"
	description = "Apply for work from home"
	usage = "/wfh tomorrow, /wfh 3 nov to 5 nov, /wfh today half"
	writes = True
	fields = (
		from_date_field("**Work from home**\nFrom which date?"),
		to_date_field(),
	)

	def parse(self, text, context):
		values, _rest = parse_time_off(text, context)
		return values

	def validate(self, values, context):
		check_no_leave(context.employee, values["from_date"], values["to_date"])
		check_no_attendance_request(context.employee, values["from_date"], values["to_date"])

	def progress(self, values, context):
		if not values.get("from_date"):
			return ""
		return _("**Work from home**\n**From:** {0}").format(show_date(values["from_date"]))

	def run(self, values, context):
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
			_("**WFH request submitted**\n**Employee:** {0}\n{1}").format(
				request.employee_name, self.describe(values, context)
			),
			link=(request.doctype, request.name),
		)

	def describe(self, values, context):
		return "\n".join(
			(
				_("**From:** {0}").format(show_date(values["from_date"])),
				_("**To:** {0}").format(show_date(values["to_date"])),
				_("**Duration:** {0}").format(count_days(total_days(values))),
				_("**Type:** {0}").format(_("Half day") if values.get("half_day") else _("Full day")),
			)
		)


def check_no_leave(employee, from_date, to_date):
	"""HRMS skips WFH on leave days, and a pending leave under WFH attendance can never be approved or rejected."""
	leave = frappe.db.get_value(
		"Leave Application",
		{
			"employee": employee,
			"docstatus": ["<", 2],
			"status": ["in", ("Open", "Approved")],
			"from_date": ["<=", to_date],
			"to_date": [">=", from_date],
		},
		["leave_type", "from_date", "to_date", "status"],
		as_dict=True,
	)
	if not leave:
		return

	dates = date_range(leave.from_date, leave.to_date)
	if leave.status == "Approved":
		frappe.throw(
			_("You are on approved {0} on {1}. Ask HR to cancel it before applying for work from home.").format(
				leave.leave_type, dates
			)
		)
	frappe.throw(
		_("You have a pending {0} on {1}. Withdraw it with /cancel first.").format(leave.leave_type, dates)
	)


def check_no_attendance_request(employee, from_date, to_date):
	request = frappe.db.get_value(
		"Attendance Request",
		{
			"employee": employee,
			"docstatus": ["<", 2],
			"from_date": ["<=", to_date],
			"to_date": [">=", from_date],
		},
		["reason", "from_date", "to_date"],
		as_dict=True,
	)
	if request:
		frappe.throw(
			_("You already have a {0} request on {1}.").format(
				_(request.reason), date_range(request.from_date, request.to_date)
			)
		)
