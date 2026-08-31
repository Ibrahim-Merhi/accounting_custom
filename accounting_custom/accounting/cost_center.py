import json
import re
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

import frappe


TRANSLATE_URL = "https://translate.googleapis.com/translate_a/single"
ARABIC_RE = re.compile(r"[\u0600-\u06ff]")


def translate_to_arabic(text):
	text = (text or "").strip()
	if not text or ARABIC_RE.search(text):
		return text
	query = urllib.parse.urlencode({
		"client": "gtx", "sl": "en", "tl": "ar", "dt": "t", "q": text,
	})
	request = urllib.request.Request(
		f"{TRANSLATE_URL}?{query}",
		headers={"User-Agent": "ERPNext accounting_custom/1.0"},
	)
	with urllib.request.urlopen(request, timeout=15) as response:
		payload = json.loads(response.read(200_000))
	translation = "".join(part[0] for part in payload[0] if part and part[0]).strip()
	if not translation or not ARABIC_RE.search(translation):
		raise ValueError("Translation service did not return Arabic text")
	return translation


@frappe.whitelist()
def get_arabic_translation(source_text=None, cost_center_name=None):
	return translate_to_arabic(source_text or cost_center_name)


def _set_arabic_name(doc, source_field, arabic_field, error_title):
	source = (doc.get(source_field) or "").strip()
	if doc.get(arabic_field) and not doc.custom_arabic_name_source:
		doc.custom_arabic_name_source = source
		return
	if not source or (doc.get(arabic_field) and doc.custom_arabic_name_source == source):
		return
	try:
		doc.set(arabic_field, translate_to_arabic(source))
		doc.custom_arabic_name_source = source
	except Exception:
		frappe.log_error(frappe.get_traceback(), error_title)


def set_arabic_cost_center_name(doc, method=None):
	_set_arabic_name(
		doc, "cost_center_name", "custom_cost_center_name_arabic",
		"Arabic Cost Center Translation",
	)


def set_arabic_account_name(doc, method=None):
	_set_arabic_name(doc, "account_name", "custom_account_name_arabic", "Arabic Account Translation")


def set_arabic_company_name(doc, method=None):
	_set_arabic_name(doc, "company_name", "custom_company_name_arabic", "Arabic Company Translation")


def translate_many_to_arabic(values):
	values = list(dict.fromkeys(value.strip() for value in values if value and value.strip()))
	translations = {}
	for start in range(0, len(values), 30):
		batch = values[start:start + 30]
		try:
			translated = translate_to_arabic("\n".join(batch)).splitlines()
			if len(translated) != len(batch):
				raise ValueError("Translation service changed the batch line count")
			translations.update(zip(batch, (value.strip() for value in translated)))
		except Exception:
			for value in batch:
				try:
					translations[value] = translate_to_arabic(value)
				except Exception:
					frappe.log_error(frappe.get_traceback(), "Arabic Name Translation")
	return translations


def backfill_arabic_names():
	backfill_arabic_cost_center_names()
	_backfill_names("Account", "account_name", "custom_account_name_arabic")
	_backfill_names("Company", "company_name", "custom_company_name_arabic")
	backfill_arabic_parent_names()


def _backfill_names(doctype, source_field, arabic_field):
	if not frappe.db.has_column(doctype, arabic_field):
		return
	rows = frappe.get_all(
		doctype,
		fields=["name", source_field, arabic_field, "custom_arabic_name_source"],
	)
	pending = [row for row in rows if row.get(source_field) and not row.get(arabic_field)]
	translations = translate_many_to_arabic(row.get(source_field) for row in pending)
	for row in pending:
		source = row.get(source_field).strip()
		if source not in translations:
			continue
		frappe.db.set_value(
			doctype, row.name,
			{arabic_field: translations[source], "custom_arabic_name_source": source},
			update_modified=False,
		)


def backfill_arabic_cost_center_names():
	if not frappe.db.has_column("Cost Center", "custom_cost_center_name_arabic"):
		return
	rows = frappe.get_all(
		"Cost Center",
		fields=["name", "cost_center_name", "custom_cost_center_name_arabic", "custom_arabic_name_source"],
	)
	pending = [
		row for row in rows
		if row.cost_center_name and not row.custom_cost_center_name_arabic
	]
	if not pending:
		backfill_arabic_parent_names()
		return
	translations = {}
	with ThreadPoolExecutor(max_workers=6) as executor:
		jobs = {executor.submit(translate_to_arabic, row.cost_center_name): row for row in pending}
		for job in as_completed(jobs):
			row = jobs[job]
			try:
				translations[row.name] = (job.result(), row.cost_center_name)
			except Exception:
				frappe.log_error(frappe.get_traceback(), "Arabic Cost Center Translation")
	for name, (arabic_name, source) in translations.items():
		frappe.db.set_value(
			"Cost Center", name,
			{"custom_cost_center_name_arabic": arabic_name, "custom_arabic_name_source": source},
			update_modified=False,
		)
	backfill_arabic_parent_names()


def backfill_arabic_parent_names():
	frappe.db.sql(
		"""
		update `tabCost Center` child
		left join `tabCost Center` parent on parent.name = child.parent_cost_center
		set child.custom_parent_cost_center_arabic = coalesce(parent.custom_cost_center_name_arabic, '')
		where coalesce(child.custom_parent_cost_center_arabic, '') = ''
			and coalesce(parent.custom_cost_center_name_arabic, '') != ''
		"""
	)
	if frappe.db.has_column("Cost Center", "custom_company_name_arabic"):
		frappe.db.sql(
			"""
			update `tabCost Center` cost_center
			inner join `tabCompany` company on company.name = cost_center.company
			set cost_center.custom_company_name_arabic = company.custom_company_name_arabic
			where coalesce(cost_center.custom_company_name_arabic, '') = ''
				and coalesce(company.custom_company_name_arabic, '') != ''
			"""
		)
	if frappe.db.has_column("Account", "custom_parent_account_arabic"):
		frappe.db.sql(
			"""
			update `tabAccount` child
			left join `tabAccount` parent on parent.name = child.parent_account
			set child.custom_parent_account_arabic = coalesce(parent.custom_account_name_arabic, '')
			where coalesce(child.custom_parent_account_arabic, '') = ''
				and coalesce(parent.custom_account_name_arabic, '') != ''
			"""
		)


def extend_bootinfo(bootinfo):
	for doctype, fieldname, key in (
		("Account", "custom_account_name_arabic", "account_arabic_names"),
		("Company", "custom_company_name_arabic", "company_arabic_names"),
		("Cost Center", "custom_cost_center_name_arabic", "cost_center_arabic_names"),
	):
		if not frappe.db.has_column(doctype, fieldname):
			continue
		bootinfo[key] = {
			row.name: row.get(fieldname)
			for row in frappe.get_all(doctype, fields=["name", fieldname])
			if row.get(fieldname)
		}
