"""Leave approval workflow, so approvers can approve or reject from the Raven card's workflow menu."""

import frappe

WORKFLOW_NAME = "Leave Approval"
APPROVER_ONLY = "doc.leave_approver == frappe.session.user"

STATES = [
	("Open", 0, "Employee"),
	("Open", 0, "HR User"),
	("Approved", 1, "Leave Approver"),
	("Approved", 1, "HR Manager"),
	("Rejected", 1, "Leave Approver"),
	("Rejected", 1, "HR Manager"),
	("Cancelled", 2, "HR Manager"),
]

TRANSITIONS = [
	("Open", "Approve", "Approved", "Leave Approver", APPROVER_ONLY),
	("Open", "Reject", "Rejected", "Leave Approver", APPROVER_ONLY),
	("Open", "Approve", "Approved", "HR Manager", ""),
	("Open", "Reject", "Rejected", "HR Manager", ""),
	("Approved", "Cancel", "Cancelled", "HR Manager", ""),
]


def ensure_leave_workflow():
	"""Add the workflow once. A site that already has its own leave workflow keeps it."""
	if frappe.db.exists("Workflow", {"document_type": "Leave Application"}):
		return

	for state in {state for state, *_rest in STATES}:
		ensure_master("Workflow State", "workflow_state_name", state)
	for action in {action for _state, action, *_rest in TRANSITIONS}:
		ensure_master("Workflow Action Master", "workflow_action_name", action)

	frappe.get_doc(
		{
			"doctype": "Workflow",
			"workflow_name": WORKFLOW_NAME,
			"document_type": "Leave Application",
			# The status field is the state, so HRMS list views and reports keep working.
			"workflow_state_field": "status",
			"is_active": 1,
			"send_email_alert": 0,
			"states": [
				{"state": state, "doc_status": str(doc_status), "allow_edit": role}
				for state, doc_status, role in STATES
			],
			"transitions": [
				{
					"state": state,
					"action": action,
					"next_state": next_state,
					"allowed": role,
					"condition": condition,
					"allow_self_approval": 0,
				}
				for state, action, next_state, role, condition in TRANSITIONS
			],
		}
	).insert(ignore_permissions=True)


def ensure_master(doctype, fieldname, name):
	if not frappe.db.exists(doctype, name):
		frappe.get_doc({"doctype": doctype, fieldname: name}).insert(ignore_permissions=True)
