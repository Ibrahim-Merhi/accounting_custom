app_name = "accounting_custom"
app_title = "Accounting Custom"
app_publisher = "Ibrahim Merhi"
app_description = "Custom accounting and donation management extensions for ERPNext"
app_email = "ibrahim.m.merhy@gmail.com"
app_license = "mit"
required_apps = ["erpnext", "non_profit"]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
app_include_css = "/assets/accounting_custom/css/accounting_custom.css"
app_include_js = [
	"/assets/accounting_custom/js/cost_center_arabic.js",
	"/assets/accounting_custom/js/general_ledger.js",
]

# include js, css files in header of web template
# web_include_css = "/assets/accounting_custom/css/accounting_custom.css"
# web_include_js = "/assets/accounting_custom/js/accounting_custom.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "accounting_custom/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
doctype_js = {
	"Account": "public/js/arabic_name.js",
	"Company": "public/js/arabic_name.js",
	"Cost Center": "public/js/arabic_name.js",
	"Donor": "public/js/donor.js",
	"Journal Entry": "public/js/company_exchange_rate.js",
	"Payment Entry": "public/js/company_exchange_rate.js",
	"Sales Order": "public/js/company_exchange_rate.js",
	"Purchase Order": "public/js/company_exchange_rate.js",
	"Purchase Invoice": "public/js/company_exchange_rate.js",
	"Sales Invoice": "public/js/company_exchange_rate.js",
}

extend_bootinfo = "accounting_custom.accounting.cost_center.extend_bootinfo"
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "accounting_custom/public/icons.svg"

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "accounting_custom.utils.jinja_methods",
# 	"filters": "accounting_custom.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "accounting_custom.install.before_install"
after_install = "accounting_custom.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "accounting_custom.uninstall.before_uninstall"
# after_uninstall = "accounting_custom.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "accounting_custom.utils.before_app_install"
# after_app_install = "accounting_custom.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "accounting_custom.utils.before_app_uninstall"
# after_app_uninstall = "accounting_custom.utils.after_app_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "accounting_custom.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

permission_query_conditions = {
	"Donation Entry": "accounting_custom.permissions.donation_query",
	"Collector Handover": "accounting_custom.permissions.handover_query",
	"Payment Memo": "accounting_custom.permissions.payment_memo_query",
}
#
has_permission = {
	"Donation Entry": "accounting_custom.permissions.donation_permission",
	"Collector Handover": "accounting_custom.permissions.handover_permission",
	"Payment Memo": "accounting_custom.permissions.payment_memo_permission",
}

# DocType Class
# ---------------
# Override standard doctype classes

# override_doctype_class = {
# 	"ToDo": "custom_app.overrides.CustomToDo"
# }

# Document Events
# ---------------
# Hook on document methods and events

doc_events = {
	"Accounting Payment Entry": {
		"before_naming": "accounting_custom.naming.company_series.set_accounting_payment_entry_series",
	},
	"Accounting Receipt Entry": {
		"before_naming": "accounting_custom.naming.company_series.set_accounting_receipt_entry_series",
	},
	"Account": {
		"validate": "accounting_custom.accounting.cost_center.set_arabic_account_name",
	},
	"Company": {
		"validate": "accounting_custom.accounting.cost_center.set_arabic_company_name",
	},
	"Cost Center": {
		"validate": "accounting_custom.accounting.cost_center.set_arabic_cost_center_name",
	},
	"Donation Entry": {
		"before_naming": "accounting_custom.naming.company_series.set_donation_entry_series",
	},
	"Journal Entry": {
		"before_naming": "accounting_custom.naming.company_series.set_journal_entry_series",
		"before_validate": "accounting_custom.accounting.standard_exchange_rate.apply_journal_entry_exchange_rates",
		"validate": "accounting_custom.accounting.branch.validate_journal_entry_branch",
	},
	"Payment Entry": {
		"before_naming": "accounting_custom.naming.company_series.set_payment_entry_series",
		"before_validate": "accounting_custom.accounting.standard_exchange_rate.apply_payment_entry_exchange_rates",
	},
	"Sales Order": {
		"before_validate": "accounting_custom.accounting.standard_exchange_rate.apply_transaction_exchange_rate",
	},
	"Purchase Order": {
		"before_validate": "accounting_custom.accounting.standard_exchange_rate.apply_transaction_exchange_rate",
	},
	"Purchase Invoice": {
		"before_validate": "accounting_custom.accounting.standard_exchange_rate.apply_transaction_exchange_rate",
	},
	"Sales Invoice": {
		"before_validate": "accounting_custom.accounting.standard_exchange_rate.apply_transaction_exchange_rate",
	},
	"GL Entry": {
		"before_insert": "accounting_custom.accounting.branch.set_gl_entry_branch",
	},
}

# Scheduled Tasks
# ---------------

# scheduler_events = {
# 	"all": [
# 		"accounting_custom.tasks.all"
# 	],
# 	"daily": [
# 		"accounting_custom.tasks.daily"
# 	],
# 	"hourly": [
# 		"accounting_custom.tasks.hourly"
# 	],
# 	"weekly": [
# 		"accounting_custom.tasks.weekly"
# 	],
# 	"monthly": [
# 		"accounting_custom.tasks.monthly"
# 	],
# }

# Testing
# -------

# before_tests = "accounting_custom.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "accounting_custom.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "accounting_custom.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["accounting_custom.utils.before_request"]
# after_request = ["accounting_custom.utils.after_request"]

# Job Events
# ----------
# before_job = ["accounting_custom.utils.before_job"]
# after_job = ["accounting_custom.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"accounting_custom.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }



after_migrate = "accounting_custom.install.after_migrate"

fixtures = [
	{
		"dt": "Print Format",
		"filters": [["name", "in", ["سند قبض", "سند صرف", "Journal Voucher"]]],
	},
	{
		"dt": "Property Setter",
		"filters": [
			["doc_type", "=", "Donor"],
			["field_name", "=", "email"],
			["property", "=", "unique"],
		],
	},
]
