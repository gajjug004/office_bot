import datetime

from dateutil import parser

RELATIVE_DAYS = {
	"today": 0,
	"tod": 0,
	"tomorrow": 1,
	"tmrw": 1,
	"tmr": 1,
	"tom": 1,
	"yesterday": -1,
}

WEEKDAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]

RANGE_WORDS = {"to", "till", "until", "upto", "-"}

# Longest date phrase we try, e.g. "31 oct 2026" or "next monday".
MAX_PHRASE_WORDS = 3


def parse_date(text: str, today: datetime.date) -> datetime.date | None:
	"""Read one date the way people type it in chat: "tomorrow", "fri", "next mon", "5 nov", "05/11/2026"."""
	words = text.strip().lower().rstrip(".,").split()
	if not words:
		return None

	if len(words) == 1 and words[0] in RELATIVE_DAYS:
		return today + datetime.timedelta(days=RELATIVE_DAYS[words[0]])

	is_next = words[0] == "next"
	day_words = words[1:] if is_next else words
	if len(day_words) == 1 and (weekday := find_weekday(day_words[0])) is not None:
		return next_weekday(today, weekday, strictly_after=is_next)

	# Without a digit dateutil reads lone words like "may" or "march" as a date.
	if is_next or not any(char.isdigit() for char in text):
		return None

	# dayfirst would read "2026-11-05" as 11 May.
	if len(words) == 1 and (iso_date := read_iso_date(words[0])):
		return iso_date

	try:
		default = datetime.datetime(today.year, today.month, today.day)
		return parser.parse(" ".join(words), dayfirst=True, default=default).date()
	except ValueError, OverflowError:
		return None


def extract_dates(text: str, today: datetime.date) -> tuple[list[datetime.date], list[str]]:
	"""Pull every date out of free text. Returns the dates in order and the words that were not dates."""
	words = text.split()
	dates, rest = [], []
	index = 0
	while index < len(words):
		if dates and words[index].lower() in RANGE_WORDS:
			index += 1
			continue

		size, date = longest_date_at(words, index, today)
		if date:
			dates.append(date)
			index += size
		else:
			rest.append(words[index])
			index += 1

	return dates, rest


def longest_date_at(words: list[str], index: int, today: datetime.date):
	for size in range(MAX_PHRASE_WORDS, 0, -1):
		phrase = words[index : index + size]
		# In free text a lone number is a count, like "cab for 2 people", not a day of the month.
		if size == 1 and phrase[0].isdigit():
			continue
		if len(phrase) == size and (date := parse_date(" ".join(phrase), today)):
			return size, date
	return 0, None


def read_iso_date(word: str) -> datetime.date | None:
	try:
		return datetime.date.fromisoformat(word)
	except ValueError:
		return None


def find_weekday(word: str) -> int | None:
	if len(word) < 3:
		return None
	return next((number for number, name in enumerate(WEEKDAYS) if name.startswith(word)), None)


def next_weekday(today: datetime.date, weekday: int, strictly_after: bool) -> datetime.date:
	days_ahead = (weekday - today.weekday()) % 7
	if days_ahead == 0 and strictly_after:
		days_ahead = 7
	return today + datetime.timedelta(days=days_ahead)
