import frappe
from frappe import _
from frappe.utils import flt, get_fullname

from office_bot.command import Choice, Command, Field, Reply, count_days, show_date
from office_bot.commands.time_off import from_date_field, parse_time_off, to_date_field, total_days


class ApplyLeave(Command):
	name = "leave"
	aliases = ("leave_application",)
	description = "Apply for leave"
	usage = "/leave casual tomorrow, /leave sick 3 nov to 5 nov fever, /leave casual fri half"
	writes = True
	fields = (
		Field(
			"leave_type",
			"**Apply for leave**\nWhich leave type?",
			"choice",
			choices=lambda values, context: leave_type_choices(context),
		),
		from_date_field("From which date?"),
		to_date_field(),
	)

	def parse(self, text, context):
		values, rest = parse_time_off(text, context)
		leave_types = [choice.values["leave_type"] for choice in leave_type_choices(context)]
		if not leave_types:
			frappe.throw(_("You have no leave allocated for today. Ask HR to allocate your leave."))
		if rest and (leave_type := match_leave_type(rest[0], leave_types)):
			values["leave_type"] = leave_type
			rest = rest[1:]
		if rest:
			values["description"] = " ".join(rest)
		return values

	def run(self, values, context):
		application = frappe.get_doc(
			{
				"doctype": "Leave Application",
				"employee": context.employee,
				"leave_type": values["leave_type"],
				"from_date": values["from_date"],
				"to_date": values["to_date"],
				"half_day": values.get("half_day"),
				"half_day_date": values["from_date"] if values.get("half_day") else None,
				"description": values.get("description"),
				"leave_approver": get_leave_approver(context.employee),
				"status": "Open",
				"follow_via_email": 0,
			}
		).insert()

		return Reply(
			_("**Leave applied**\n**Employee:** {0}\n{1}\n**Approval:** Waiting for {2}.").format(
				application.employee_name,
				self.describe(values, context),
				get_fullname(application.leave_approver)
				if application.leave_approver
				else _("your approver"),
			),
			link=(application.doctype, application.name),
		)

	def progress(self, values, context):
		lines = [_("**Apply for leave**")]
		if values.get("leave_type"):
			lines.append(_("**Leave type:** {0}").format(values["leave_type"]))
		if values.get("from_date"):
			lines.append(_("**From:** {0}").format(show_date(values["from_date"])))
		return "\n".join(lines) if len(lines) > 1 else ""

	def describe(self, values, context):
		lines = [
			_("**Leave type:** {0}").format(values["leave_type"]),
			_("**From:** {0}").format(show_date(values["from_date"])),
			_("**To:** {0}").format(show_date(values["to_date"])),
			_("**Duration:** {0}").format(count_days(total_days(values))),
		]
		if values.get("description"):
			lines.append(_("**Reason:** {0}").format(values["description"]))
		return "\n".join(lines)


def leave_type_choices(context):
	return [
		Choice(f"{row['leave_type']} ({flt(row['balance']):g} left)", {"leave_type": row["leave_type"]})
		for row in get_leave_balances(context.employee, context.today)
	]


def get_leave_balances(employee, date):
	from hrms.hr.doctype.leave_application.leave_application import get_leave_balance_on

	leave_types = frappe.get_all(
		"Leave Allocation",
		filters={"employee": employee, "docstatus": 1, "from_date": ["<=", date], "to_date": [">=", date]},
		pluck="leave_type",
		distinct=True,
		order_by="leave_type",
	)
	return [
		{"leave_type": leave_type, "balance": get_leave_balance_on(employee, leave_type, date)}
		for leave_type in leave_types
	]


def match_leave_type(word, leave_types):
	"""Match "casual", "sick" or "cl" to a leave type name like "Casual Leave"."""
	word = word.lower()
	for leave_type in leave_types:
		name_words = [part for part in leave_type.lower().split() if part != "leave"]
		initials = "".join(part[0] for part in leave_type.lower().split())
		if word in name_words or word == initials:
			return leave_type


def get_leave_approver(employee):
	"""Fill the approver like the desk form does. HR Settings can make it mandatory."""
	from hrms.hr.doctype.leave_application.leave_application import get_employee_leave_approver

	approver = get_employee_leave_approver(employee)
	if not approver and frappe.db.get_single_value(
		"HR Settings", "leave_approver_mandatory_in_leave_application"
	):
		frappe.throw(
			_("No leave approver is set for you. Ask HR to set one on your Employee record or department.")
		)
	return approver
