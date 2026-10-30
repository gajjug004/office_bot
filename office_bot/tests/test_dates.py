import datetime
import unittest

from office_bot.dates import extract_dates, parse_date

# A Friday.
TODAY = datetime.date(2026, 10, 30)


def day(month, number, year=2026):
	return datetime.date(year, month, number)


class TestParseDate(unittest.TestCase):
	def test_relative_words(self):
		self.assertEqual(parse_date("today", TODAY), TODAY)
		self.assertEqual(parse_date("Tomorrow", TODAY), day(10, 31))
		self.assertEqual(parse_date("yesterday", TODAY), day(10, 29))

	def test_weekdays(self):
		self.assertEqual(parse_date("fri", TODAY), TODAY)
		self.assertEqual(parse_date("next fri", TODAY), day(11, 6))
		self.assertEqual(parse_date("monday", TODAY), day(11, 2))
		self.assertEqual(parse_date("next mon", TODAY), day(11, 2))

	def test_written_dates_are_day_first(self):
		self.assertEqual(parse_date("5 nov", TODAY), day(11, 5))
		self.assertEqual(parse_date("05/11/2026", TODAY), day(11, 5))
		self.assertEqual(parse_date("2026-11-05", TODAY), day(11, 5))

	def test_rejects_words_that_are_not_dates(self):
		for text in ("fever", "may", "next", "mo", "", "casual"):
			self.assertIsNone(parse_date(text, TODAY), text)


class TestExtractDates(unittest.TestCase):
	def test_range_with_rest(self):
		dates, rest = extract_dates("casual 3 nov to 5 nov family function", TODAY)
		self.assertEqual(dates, [day(11, 3), day(11, 5)])
		self.assertEqual(rest, ["casual", "family", "function"])

	def test_single_relative_date(self):
		self.assertEqual(extract_dates("tomorrow half", TODAY), ([day(10, 31)], ["half"]))

	def test_range_word_kept_without_a_date_before_it(self):
		self.assertEqual(extract_dates("to the doctor", TODAY), ([], ["to", "the", "doctor"]))
