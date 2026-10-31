import frappe
from frappe import _

from office_bot import hive_client
from office_bot.command import Choice, Command, Field, Reply, date_choices, show_date

DEFAULT_STATUS = "To Do"
START_DATE_PICKS = [("Today", 0), ("Tomorrow", 1), ("Day after", 2)]
DUE_DATE_PICKS = [("Same day", 0), ("+1 day", 1), ("+2 days", 2), ("+1 week", 7)]


class HiveTask(Command):
	name = "task"
	aliases = ("hive",)
	description = "Create a task in Hive"
	usage = "/task Fix the login page"
	needs_employee = False
	writes = True
	fields = (
		Field(
			"site",
			"**New Hive task**\nWhich Hive site?",
			"choice",
			choices=lambda values, context: site_choices(),
		),
		Field("title", "What is the task title?"),
		Field("description", "Add a description.", optional=True),
		Field(
			"start_date",
			"When does it start?",
			"date",
			choices=lambda values, context: date_choices("start_date", context.today, START_DATE_PICKS),
		),
		Field(
			"due_date",
			"When is it due?",
			"date",
			choices=lambda values, context: date_choices("due_date", values["start_date"], DUE_DATE_PICKS),
			not_before="start_date",
		),
		Field("project", "Which project?", "choice", choices=lambda values, context: project_choices(values)),
		Field(
			"assignees",
			"Who should work on it?",
			"multichoice",
			choices=lambda values, context: member_choices(values),
			optional=True,
		),
	)

	def parse(self, text, context):
		sites = hive_client.active_sites()
		if not sites:
			frappe.throw(_("No Hive sites are set up. Add one under Hive Sites in Office Bot Settings."))

		values = {"site": sites[0].name} if len(sites) == 1 else {}
		if text:
			values["title"] = text
		return values

	def run(self, values, context):
		site = get_site(values["site"])
		task = hive_client.create_task(
			site,
			title=values["title"],
			project=values["project"],
			status=DEFAULT_STATUS,
			start_date=values["start_date"],
			due_date=values["due_date"],
			description=values.get("description"),
		)
		if values.get("assignees"):
			hive_client.assign_task(site, task, values["assignees"])

		return Reply(
			_("**Hive task created**\n**Task:** {0}\n**Due:** {1}\n[Open in Hive]({2})").format(
				values["title"], show_date(values["due_date"]), hive_client.task_url(site, task)
			)
		)

	def progress(self, values, context):
		lines = [_("**New Hive task**")]
		if values.get("site"):
			lines.append(_("**Site:** {0}").format(hive_client.site_label(get_site(values["site"]))))
		if values.get("title"):
			lines.append(_("**Task:** {0}").format(values["title"]))
		if values.get("description"):
			lines.append(_("**Description:** {0}").format(values["description"]))
		if values.get("start_date"):
			lines.append(_("**Starts:** {0}").format(show_date(values["start_date"])))
		if values.get("due_date"):
			lines.append(_("**Due:** {0}").format(show_date(values["due_date"])))
		return "\n".join(lines) if len(lines) > 1 else ""

	def describe(self, values, context):
		return _("**Task:** {0}\n**Due:** {1}").format(
			values["title"], show_date(values["due_date"])
		)


def site_choices():
	return [Choice(hive_client.site_label(site), {"site": site.name}) for site in hive_client.active_sites()]


def project_choices(values):
	projects = hive_client.list_projects(get_site(values["site"]))
	if not projects:
		frappe.throw(_("No open projects found in Hive. Create one first."))
	return [Choice(project["title"] or project["name"], {"project": project["name"]}) for project in projects]


def member_choices(values):
	members = hive_client.list_members(get_site(values["site"]))
	return [
		Choice(member["member_name"] or member["user"], {"assignees": member["user"]}) for member in members
	]


def get_site(name):
	site = next((site for site in hive_client.active_sites() if site.name == name), None)
	if not site:
		frappe.throw(_("This Hive site is no longer active."))
	return site
