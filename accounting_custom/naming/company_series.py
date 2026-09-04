import re

import frappe
from frappe import _


_VALID_ABBREVIATION = re.compile(r"^[A-Za-z0-9]+$")


def set_journal_entry_series(doc, method=None):
	set_company_series(doc, "JV")


def set_payment_entry_series(doc, method=None):
	set_company_series(doc, "PAY")


def set_accounting_payment_entry_series(doc, method=None):
	set_company_series(doc, "APE")


def set_donation_entry_series(doc, method=None):
	set_company_series(doc, "DON")


def set_company_series(doc, transaction_code):
	if not doc.company:
		frappe.throw(_("Company is required before naming {0}.").format(doc.doctype))
	abbreviation = frappe.get_cached_value("Company", doc.company, "abbr")
	if not abbreviation:
		frappe.throw(_("Company abbreviation is required for company {0}.").format(doc.company))
	abbreviation = abbreviation.strip().upper()
	if not _VALID_ABBREVIATION.fullmatch(abbreviation):
		frappe.throw(_("Company abbreviation may contain only letters and numbers."))
	doc.naming_series = f"{abbreviation}-ACC-{transaction_code}-.YYYY.-.#####"
