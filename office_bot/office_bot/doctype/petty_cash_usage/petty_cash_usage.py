# Copyright (c) 2026, Gajendra and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class PettyCashUsage(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		amended_from: DF.Link | None
		amount: DF.Currency
		category: DF.Link
		employee: DF.Link
		employee_name: DF.Data | None
		expense_date: DF.Date
		naming_series: DF.Literal["PCU-.YYYY.-.#####"]
		remarks: DF.SmallText
	# end: auto-generated types

	_DOCTYPE_NAME = "Petty Cash Usage"
