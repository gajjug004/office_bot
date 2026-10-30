from frappe.utils import date_diff

from office_bot.command import Field, date_choices
from office_bot.dates import extract_dates

HALF_DAY_WORDS = {"half", "halfday", "half-day"}

FROM_DATE_PICKS = [("Today", 0), ("Tomorrow", 1), ("Day after", 2)]
TO_DATE_PICKS = [("Same day", 0), ("+1 day", 1), ("+2 days", 2), ("+4 days", 4)]


def from_date_field(question):
	return Field(
		"from_date",
		question,
		"date",
		choices=lambda values, context: date_choices("from_date", context.today, FROM_DATE_PICKS),
	)


def to_date_field():
	return Field("to_date", "Till which date?", "date", choices=to_date_choices, not_before="from_date")


def to_date_choices(values, context):
	choices = date_choices("to_date", values["from_date"], TO_DATE_PICKS)
	half_day = date_choices("to_date", values["from_date"], [("Same day, half day", 0)])[0]
	half_day.values["half_day"] = True
	return [choices[0], half_day, *choices[1:]]


def parse_time_off(text, context):
	"""Read "3 nov to 5 nov half family function" into values and the leftover words."""
	words = text.split()
	half_day = any(word.lower() in HALF_DAY_WORDS for word in words)
	words = [word for word in words if word.lower() not in HALF_DAY_WORDS]
	dates, rest = extract_dates(" ".join(words), context.today)

	values = {"half_day": half_day}
	if dates:
		values["from_date"] = str(dates[0])
		values["to_date"] = str(dates[-1] if len(dates) > 1 else dates[0])
	return values, rest


def total_days(values):
	days = date_diff(values["to_date"], values["from_date"]) + 1
	return days - 0.5 if values.get("half_day") else days
