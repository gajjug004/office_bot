import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

from office_bot.leave_workflow import ensure_leave_workflow

BOT_NAME = "Office Bot"
DEFAULT_CATEGORIES = ["Internet", "Food", "Stationery", "Travel"]

CUSTOM_FIELDS = {
	"Attendance Request": [
		{
			"fieldname": "custom_total_wfh_days",
			"label": "Total WFH Days",
			"fieldtype": "Float",
			"precision": "1",
			"insert_after": "half_day_date",
			"description": "Work from home days. 0.5 for a half day. Used instead of Half Day, which would mark attendance half absent.",
		}
	],
}

TODAY = {"default_value_type": "Jinja", "default_value": "{{ frappe.utils.nowdate() }}"}
FROM_DATE = {"fieldname": "from_date", "label": "From Date", "type": "Date", "is_required": 1, **TODAY}
TO_DATE = {
	"fieldname": "to_date",
	"label": "To Date",
	"type": "Date",
	"helper_text": "Leave empty for one day",
}
HALF_DAY = {"fieldname": "half_day", "label": "Half Day", "type": "Checkbox"}

MESSAGE_ACTIONS = [
	{
		"action_name": "Apply for Work From Home",
		"title": "Work From Home",
		"description": "Submitted right away. You can also type /wfh in any chat with the bot.",
		"custom_function_path": "office_bot.channels.raven_actions.apply_wfh",
		"success_message": "Work from home submitted",
		"fields": [FROM_DATE, TO_DATE, HALF_DAY],
	},
	{
		"action_name": "Apply for Leave",
		"title": "Apply for Leave",
		"description": "Goes to your leave approver. You can also type /leave in any chat with the bot.",
		"custom_function_path": "office_bot.channels.raven_actions.apply_leave",
		"success_message": "Leave applied. Your approver will get a message.",
		"fields": [
			{
				"fieldname": "leave_type",
				"label": "Leave Type",
				"type": "Link",
				"options": "Leave Type",
				"is_required": 1,
			},
			FROM_DATE,
			TO_DATE,
			HALF_DAY,
			{"fieldname": "description", "label": "Reason", "type": "Small Text"},
		],
	},
	{
		"action_name": "Record Petty Cash Expense",
		"title": "Petty Cash Expense",
		"description": "Added to next month's petty cash journal entry. You can also type /expense.",
		"custom_function_path": "office_bot.channels.raven_actions.record_expense",
		"success_message": "Petty cash recorded",
		"fields": [
			{"fieldname": "amount", "label": "Amount", "type": "Number", "is_required": 1},
			{
				"fieldname": "category",
				"label": "Category",
				"type": "Link",
				"options": "Petty Cash Category",
				"is_required": 1,
			},
			{"fieldname": "remarks", "label": "What was it for?", "type": "Small Text", "is_required": 1},
			{"fieldname": "expense_date", "label": "Expense Date", "type": "Date", **TODAY},
		],
	},
]


def after_install():
	after_migrate()


def after_migrate():
	create_custom_fields(CUSTOM_FIELDS, ignore_validate=True)
	ensure_bot()
	ensure_channel_defaults()
	ensure_message_actions()
	ensure_categories()
	ensure_leave_workflow()


def ensure_channel_defaults():
	for field in ("enable_raven", "enable_telegram"):
		if frappe.db.get_single_value("Office Bot Settings", field) is None:
			frappe.db.set_single_value("Office Bot Settings", field, 1)


def ensure_bot():
	if frappe.db.get_single_value("Office Bot Settings", "raven_bot"):
		return

	if not frappe.db.exists("Raven Bot", BOT_NAME):
		frappe.get_doc(
			{
				"doctype": "Raven Bot",
				"bot_name": BOT_NAME,
				"description": "Apply for leave, work from home and more. Type /help.",
			}
		).insert(ignore_permissions=True)
	frappe.db.set_single_value("Office Bot Settings", "raven_bot", BOT_NAME)
	frappe.db.set_single_value("Office Bot Settings", "enable_raven", 1)


def ensure_message_actions():
	for action in MESSAGE_ACTIONS:
		if not frappe.db.exists(
			"Raven Message Action", {"custom_function_path": action["custom_function_path"]}
		):
			frappe.get_doc(
				{"doctype": "Raven Message Action", "action": "Custom Function", "enabled": 1, **action}
			).insert(ignore_permissions=True)


def ensure_categories():
	if not frappe.db.count("Petty Cash Category"):
		for name in DEFAULT_CATEGORIES:
			frappe.get_doc({"doctype": "Petty Cash Category", "category_name": name}).insert(
				ignore_permissions=True
			)
