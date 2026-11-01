import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, getdate

from office_bot import notifications

EMPLOYEE_USER = "office-bot-leave@example.com"
APPROVER = "office-bot-approver@example.com"
STRANGER = "office-bot-stranger@example.com"
LEAVE_TYPE = "Office Bot Test Leave"


class TestLeaveApproval(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		for email, role in (
			(EMPLOYEE_USER, "Employee"),
			(APPROVER, "Leave Approver"),
			(STRANGER, "Leave Approver"),
		):
			frappe.get_doc(
				{
					"doctype": "User",
					"email": email,
					"first_name": email.split("@")[0],
					"roles": [{"role": role}],
				}
			).insert(ignore_permissions=True)
		frappe.get_doc({"doctype": "Leave Type", "leave_type_name": LEAVE_TYPE}).insert(
			ignore_permissions=True
		)
		cls.employee = frappe.get_doc(
			{
				"doctype": "Employee",
				"first_name": "Leave",
				"gender": "Female",
				"date_of_birth": "1990-01-01",
				"date_of_joining": "2020-01-01",
				"company": frappe.db.get_value("Company", {}, "name"),
				"user_id": EMPLOYEE_USER,
				"leave_approver": APPROVER,
			}
		).insert(ignore_permissions=True)
		today = getdate()
		frappe.get_doc(
			{
				"doctype": "Leave Allocation",
				"employee": cls.employee.name,
				"leave_type": LEAVE_TYPE,
				"from_date": add_days(today, -30),
				"to_date": add_days(today, 60),
				"new_leaves_allocated": 10,
			}
		).submit()
		cls.next_day = 1

	def setUp(self):
		self.addCleanup(frappe.set_user, "Administrator")

	def apply(self):
		date = add_days(getdate(), self.next_day)
		type(self).next_day += 1
		frappe.set_user(EMPLOYEE_USER)
		leave = frappe.get_doc(
			{
				"doctype": "Leave Application",
				"employee": self.employee.name,
				"leave_type": LEAVE_TYPE,
				"from_date": date,
				"to_date": date,
				"leave_approver": APPROVER,
				"status": "Open",
			}
		).insert()
		frappe.set_user("Administrator")
		return leave.name

	def test_approver_message_has_approve_and_reject(self):
		leave = self.apply()
		sent = []
		with self.patch_notify(sent):
			notifications.notify_approver(leave)
		user, reply = sent[0]
		self.assertEqual(user, APPROVER)
		self.assertEqual(
			reply.actions,
			[("Approve", f"leave:Approve:{leave}"), ("Reject", f"leave:Reject:{leave}")],
		)

	def test_approver_rejects_and_a_second_tap_is_told(self):
		leave = self.apply()
		frappe.set_user(APPROVER)
		reply = notifications.decide_leave(leave, notifications.REJECT)
		self.assertTrue(reply.text.startswith("**Leave rejected**"))
		self.assertEqual(frappe.db.get_value("Leave Application", leave, "status"), "Rejected")

		reply = notifications.decide_leave(leave, notifications.APPROVE)
		self.assertTrue(reply.text.startswith("**Leave already rejected**"))

	def test_someone_else_cannot_decide(self):
		leave = self.apply()
		frappe.set_user(STRANGER)
		self.assertRaises(frappe.PermissionError, notifications.decide_leave, leave, notifications.APPROVE)
		self.assertEqual(frappe.db.get_value("Leave Application", leave, "status"), "Open")

	def patch_notify(self, sent):
		from unittest.mock import patch

		return patch.object(
			notifications.channels, "notify_user", side_effect=lambda user, reply: sent.append((user, reply))
		)
