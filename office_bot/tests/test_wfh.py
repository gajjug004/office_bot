import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, getdate

from office_bot.command import Context
from office_bot.commands import COMMANDS

USER = "office-bot-wfh@example.com"


class TestWorkFromHome(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		frappe.get_doc(
			{"doctype": "User", "email": USER, "first_name": "Wfh", "roles": [{"role": "Employee"}]}
		).insert(ignore_permissions=True)
		cls.start = add_days(getdate(), 2)
		holiday_list = frappe.get_doc(
			{
				"doctype": "Holiday List",
				"holiday_list_name": "Office Bot WFH Test",
				"from_date": add_days(cls.start, -30),
				"to_date": add_days(cls.start, 30),
				"holidays": [
					{"holiday_date": add_days(cls.start, offset), "description": "Test holiday"}
					for offset in (1, 11)
				],
			}
		).insert(ignore_permissions=True)
		cls.employee = frappe.get_doc(
			{
				"doctype": "Employee",
				"first_name": "Wfh",
				"gender": "Female",
				"date_of_birth": "1990-01-01",
				"date_of_joining": "2020-01-01",
				"company": frappe.db.get_value("Company", {}, "name"),
				"user_id": USER,
			}
		).insert(ignore_permissions=True)
		frappe.get_doc(
			{
				"doctype": "Holiday List Assignment",
				"applicable_for": "Employee",
				"assigned_to": cls.employee.name,
				"holiday_list": holiday_list.name,
				"from_date": holiday_list.from_date,
			}
		).submit()

	def setUp(self):
		self.addCleanup(frappe.set_user, "Administrator")
		frappe.set_user(USER)
		self.context = Context.for_user(USER)

	def apply(self, from_offset, to_offset):
		values = {
			"from_date": str(add_days(self.start, from_offset)),
			"to_date": str(add_days(self.start, to_offset)),
		}
		COMMANDS["wfh"].validate(values, self.context)
		return COMMANDS["wfh"].run(values, self.context).link[1]

	def test_holidays_are_not_counted(self):
		request = self.apply(0, 2)
		self.assertEqual(frappe.db.get_value("Attendance Request", request, "custom_total_wfh_days"), 2)

	def test_only_holidays_is_refused(self):
		self.assertRaisesRegex(frappe.ValidationError, "is a holiday", self.apply, 11, 11)

	def test_marked_attendance_is_refused(self):
		frappe.get_doc(
			{
				"doctype": "Attendance",
				"employee": self.employee.name,
				"attendance_date": add_days(self.start, 25),
				"status": "Present",
			}
		).insert(ignore_permissions=True)
		self.assertRaisesRegex(frappe.ValidationError, "already marked as Present", self.apply, 25, 25)

	def test_employee_withdraws_wfh_with_marked_attendance(self):
		request = self.apply(20, 20)
		self.assertTrue(frappe.db.exists("Attendance", {"attendance_request": request, "docstatus": 1}))

		reply = COMMANDS["cancel"].run({"request": ["Attendance Request", request]}, self.context)

		self.assertIn("**Request withdrawn**", reply.text)
		self.assertEqual(frappe.db.get_value("Attendance Request", request, "docstatus"), 2)
		self.assertFalse(frappe.db.exists("Attendance", {"attendance_request": request, "docstatus": 1}))
