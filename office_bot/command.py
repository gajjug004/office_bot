import datetime
from dataclasses import dataclass, field

import frappe
from frappe import _
from frappe.utils import flt, formatdate, get_fullname, getdate

from office_bot.dates import parse_date

COMMANDS = {}

SKIP_WORDS = {"skip", "none", "no", "-"}


@dataclass
class Choice:
	label: str
	values: dict


@dataclass
class Reply:
	"""What the bot says. Lines may use **bold**; each channel renders it its own way."""

	text: str
	choices: list[str] = field(default_factory=list)
	hint: str = ""  # other ways to answer, like "type a date"
	link: tuple[str, str] | None = None
	asks: bool = False
	multiple: bool = False
	actions: list[tuple[str, str]] = field(default_factory=list)  # (label, key) buttons that act on a record


@dataclass
class Context:
	user: str
	employee: str | None
	today: datetime.date

	@classmethod
	def for_user(cls, user):
		employee = frappe.db.get_value("Employee", {"user_id": user, "status": "Active"}, "name")
		return cls(user=user, employee=employee, today=getdate())


@dataclass
class Field:
	key: str
	question: str
	kind: str = "text"  # text, number, date, choice or multichoice
	choices: object = None  # callable(values, context) -> list[Choice]
	optional: bool = False
	not_before: str = ""  # key of an earlier date this date cannot be before

	def get_choices(self, values, context):
		return self.choices(values, context) if self.choices else []

	def prompt(self, values, context):
		return Reply(
			_(self.question),
			choices=[choice.label for choice in self.get_choices(values, context)],
			hint=self.hint(),
			asks=True,
			multiple=self.kind == "multichoice",
		)

	def hint(self):
		parts = []
		if self.kind == "date":
			parts.append(_("type a date like tomorrow, fri or 5 nov"))
		if self.kind == "multichoice":
			parts.append(_("pick several like 1,3"))
		if self.optional:
			parts.append(_("type skip to leave it out"))
		return ", ".join(parts)

	def read(self, text, values, context) -> dict:
		"""Turn an answer into field values. Throws a ValidationError the user can read."""
		text = text.strip()
		if self.optional and text.lower() in SKIP_WORDS:
			return {self.key: None}

		choices = self.get_choices(values, context)
		if self.kind == "multichoice":
			return self.read_many(text, choices)
		if picked := pick_choice(text, choices):
			return picked.values

		match self.kind:
			case "date":
				return {self.key: self.read_date(text, values, context)}
			case "number":
				return {self.key: read_amount(text)}
			case "choice":
				frappe.throw(_("Pick a number from the list."))
		return {self.key: text}

	def read_date(self, text, values, context):
		date = parse_date(text, context.today)
		if not date:
			frappe.throw(
				_("I could not read {0} as a date. Try tomorrow, fri, 5 nov or 05-11-2026.").format(text)
			)
		if self.not_before and date < getdate(values[self.not_before]):
			frappe.throw(_("This date cannot be before {0}.").format(show_date(values[self.not_before])))
		return str(date)

	def read_many(self, text, choices):
		numbers = text.replace(",", " ").split()
		if not numbers or not all(
			number.isdigit() and 1 <= int(number) <= len(choices) for number in numbers
		):
			frappe.throw(_("Pick numbers from the list, like 1,3."))
		return {self.key: [choices[int(number) - 1].values[self.key] for number in numbers]}


class Command:
	"""One chat command. Subclasses declare fields and say how to parse a one-liner and what to create."""

	name = ""
	aliases: tuple[str, ...] = ()
	description = ""
	usage = ""
	needs_employee = True
	writes = False
	fields: tuple[Field, ...] = ()

	def __init_subclass__(cls, **kwargs):
		super().__init_subclass__(**kwargs)
		if cls.name:
			command = cls()
			for name in (cls.name, *cls.aliases):
				COMMANDS[name] = command

	def parse(self, text: str, context: Context) -> dict:
		"""Values the user already gave on the command line, like `/wfh tomorrow`."""
		return {}

	def validate(self, values: dict, context: Context):
		"""Refuse bad values before asking the user to confirm them."""

	def progress(self, values: dict, context: Context) -> str:
		"""Values to keep visible above the current question while a conversation advances."""
		return ""

	def prompt(self, field, values, context):
		reply = field.prompt(values, context)
		if progress := self.progress(values, context):
			reply.text = f"{progress}\n\n{reply.text}"
		return reply

	def run(self, values: dict, context: Context) -> Reply:
		raise NotImplementedError

	def describe(self, values: dict, context: Context) -> str:
		raise NotImplementedError

	def next_field(self, values):
		field = next((field for field in self.fields if field.key not in values), None)
		if not field and self.writes and values.get("confirm") and "confirmed" not in values:
			return ConfirmField(self)
		return field

	def get_field(self, key):
		return next(field for field in (*self.fields, ConfirmField(self)) if field.key == key)


class ConfirmField(Field):
	def __init__(self, command):
		super().__init__(
			"confirmed",
			"",
			"choice",
			choices=lambda values, context: [
				Choice(_("Yes, go ahead"), {"confirmed": True}),
				Choice(_("No"), {"confirmed": False}),
			],
		)
		self.command = command

	def prompt(self, values, context):
		reply = super().prompt(values, context)
		person_label = _("Employee") if context.employee else _("Requested by")
		reply.text = _("**{0}**\n**{1}:** {2}\n\n{3}\n\nShall I go ahead?").format(
			_(self.command.description),
			person_label,
			get_fullname(context.user),
			self.command.describe(values, context),
		)
		return reply


def hint_sentence(reply, numbered):
	"""The hint as a sentence. `numbered` adds "reply with a number" for channels that list choices as text."""
	parts = [_("reply with a number")] if numbered and reply.choices else []
	if reply.hint:
		parts.append(reply.hint)
	sentence = _(", or ").join(parts)
	return f"{sentence[:1].upper()}{sentence[1:]}." if sentence else ""


def pick_choice(text, choices):
	"""Match a number, a whole label, a label without its "(...)" part, or a prefix only one label has."""
	if text.isdigit() and 1 <= int(text) <= len(choices):
		return choices[int(text) - 1]

	text = text.lower()
	labels = [choice.label.lower() for choice in choices]
	heads = [label.split(" (")[0] for label in labels]
	for candidates in (labels, heads):
		if text in candidates:
			return choices[candidates.index(text)]

	prefixed = [choice for choice, label in zip(choices, labels, strict=True) if label.startswith(text)]
	return prefixed[0] if len(prefixed) == 1 else None


def read_amount(text):
	amount = flt(text.replace(",", "").lstrip("₹$").strip())
	if amount <= 0:
		frappe.throw(_("Send the amount as a number, like 250."))
	return amount


def show_date(date):
	return formatdate(date, "EEE d MMM")


def date_range(from_date, to_date):
	if getdate(from_date) == getdate(to_date):
		return show_date(from_date)
	return _("{0} to {1}").format(show_date(from_date), show_date(to_date))


def count_days(days):
	days = flt(days)
	return _("1 day") if days == 1 else _("{0} days").format(f"{days:g}")


def date_choices(key, start, offsets):
	"""Quick picks like "Tomorrow (Sat 31 Oct)" for a date field, counted in days from `start`."""
	choices = []
	for label, days in offsets:
		date = getdate(start) + datetime.timedelta(days=days)
		choices.append(Choice(f"{label} ({show_date(date)})", {key: str(date)}))
	return choices
