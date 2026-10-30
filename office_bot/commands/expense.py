import frappe
from frappe import _
from frappe.utils import flt, fmt_money

from office_bot.command import Choice, Command, Field, Reply, read_amount, show_date
from office_bot.dates import extract_dates


class PettyCashExpense(Command):
	name = "expense"
	aliases = (
		"use_petty_cash",
		"petty_cash",
	)
	description = "Record a petty cash expense"
	usage = "/expense 250 food team lunch, /expense 1200 travel cab to client yesterday"
	fields = (
		Field("amount", "**Petty cash expense**\nHow much did you spend?", "number"),
		Field("category", "Which category?", "choice", choices=lambda values, context: category_choices()),
		Field("remarks", "What was it for?"),
	)

	def parse(self, text, context):
		words = text.split()
		values = {}
		if words and flt(words[0].replace(",", "").lstrip("₹$")) > 0:
			values["amount"] = read_amount(words.pop(0))

		categories = [choice.values["category"] for choice in category_choices()]
		if words and (
			category := next((name for name in categories if name.lower() == words[0].lower()), None)
		):
			values["category"] = category
			words.pop(0)

		dates, rest = extract_dates(" ".join(words), context.today)
		if dates:
			values["expense_date"] = str(dates[0])
		if rest:
			values["remarks"] = " ".join(rest)
		return values

	def run(self, values, context):
		usage = frappe.get_doc(
			{
				"doctype": "Petty Cash Usage",
				"employee": context.employee,
				"amount": values["amount"],
				"category": values["category"],
				"remarks": values["remarks"],
				"expense_date": values.get("expense_date") or str(context.today),
			}
		).insert()

		return Reply(
			_("**Petty cash recorded** by {0}\n{1} for {2} on {3}: {4}").format(
				usage.employee_name,
				fmt_money(usage.amount, currency=frappe.db.get_default("currency")),
				usage.category,
				show_date(usage.expense_date),
				usage.remarks,
			),
			link=(usage.doctype, usage.name),
		)


def category_choices():
	return [
		Choice(name, {"category": name})
		for name in frappe.get_all("Petty Cash Category", pluck="name", order_by="creation asc")
	]
