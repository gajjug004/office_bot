import frappe
from frappe.utils import add_months, formatdate, get_first_day, get_last_day, today


def create_monthly_petty_cash_journal_entry():
	"""Book last month's petty cash as one draft Journal Entry: each category's account against cash."""
	settings = frappe.get_single("Office Bot Settings")
	if not settings.default_cash_account or not settings.default_company:
		frappe.log_error(
			"Petty cash journal entry skipped",
			message="Set Default Company and Default Cash Account in Office Bot Settings.",
		)
		return

	month = add_months(today(), -1)
	from_date, to_date = get_first_day(month), get_last_day(month)
	accounts = get_category_rows(from_date, to_date)
	if not accounts:
		return

	total = sum(row["debit_in_account_currency"] for row in accounts)
	accounts.append({"account": settings.default_cash_account, "credit_in_account_currency": total})
	frappe.get_doc(
		{
			"doctype": "Journal Entry",
			"posting_date": to_date,
			"company": settings.default_company,
			"voucher_type": "Journal Entry",
			"user_remark": f"Petty Cash Summary for {formatdate(from_date, 'MMMM yyyy')}",
			"accounts": accounts,
		}
	).insert()


def get_category_rows(from_date, to_date):
	totals = frappe.get_all(
		"Petty Cash Usage",
		filters={"docstatus": 0, "expense_date": ["between", [from_date, to_date]]},
		fields=["category", {"SUM": "amount", "as": "total"}],
		group_by="category",
	)
	rows = []
	for row in totals:
		account = frappe.db.get_value("Petty Cash Category", row.category, "account")
		if not account:
			frappe.log_error(
				"Petty cash category has no account",
				message=f"Petty Cash Category {row.category} has no account, so it was left out of the journal entry.",
			)
			continue
		rows.append({"account": account, "debit_in_account_currency": row.total})
	return rows
