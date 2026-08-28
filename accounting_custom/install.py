from accounting_custom.setup.custom_fields import ensure_donor_account_fields


def after_install():
	ensure_donor_account_fields()


def after_migrate():
	ensure_donor_account_fields()
