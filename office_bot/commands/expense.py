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
	writes = True
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
				"expense_date": expense_date(values, context),
			}
		).insert()

		return Reply(
			_("**Petty cash recorded** by {0}\n{1}").format(
				usage.employee_name, self.describe(values, context)
			),
			link=(usage.doctype, usage.name),
		)

	def describe(self, values, context):
		return _("{0} for {1} on {2}: {3}").format(
			fmt_money(values["amount"], currency=frappe.db.get_default("currency")),
			values["category"],
			show_date(expense_date(values, context)),
			values["remarks"],
		)


def expense_date(values, context):
	return values.get("expense_date") or str(context.today)


def category_choices():
	return [
		Choice(name, {"category": name})
		for name in frappe.get_all("Petty Cash Category", pluck="name", order_by="creation asc")
	]
