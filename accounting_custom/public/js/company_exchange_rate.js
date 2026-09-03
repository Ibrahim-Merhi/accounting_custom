const company_exchange_rate_method =
	"accounting_custom.api.exchange_rate.get_company_exchange_rate";

frappe.ui.form.on("Journal Entry", {
	setup(frm) {
		frm.company_exchange_rate_loading = false;
		frm.set_query("custom_branch", "accounts", () => ({
			filters: frm.doc.company ? { custom_company: frm.doc.company } : { name: ["=", ""] },
		}));
		frm.set_query("account", "accounts", () => ({
			query: "erpnext.controllers.queries.get_account_list",
			filters: frm.doc.company
				? { company: frm.doc.company, disabled: 0, is_group: 0 }
				: { name: ["=", ""] },
		}));
	},
	company(frm) {
		frm.company_currency_cache = null;
		(frm.doc.accounts || []).forEach((row) => {
			frappe.model.set_value(row.doctype, row.name, "custom_branch", null);
		});
		return set_all_journal_exchange_rates(frm);
	},
	posting_date(frm) {
		return set_all_journal_exchange_rates(frm);
	},
	refresh(frm) {
		enable_wide_journal_grid(frm);
		show_more_journal_rows(frm);
		if (frm.is_new()) return set_all_journal_exchange_rates(frm);
	},
	validate(frm) {
		return set_all_journal_exchange_rates(frm, true);
	},
});

function enable_wide_journal_grid(frm) {
	const grid = frm.fields_dict.accounts?.grid;
	if (!grid) return;

	$(frm.fields_dict.accounts.wrapper).addClass("accounting-custom-wide-journal-grid");

	const grid_row_prototype = grid.header_row
		? Object.getPrototypeOf(grid.header_row)
		: null;
	if (!grid_row_prototype || grid_row_prototype._accounting_custom_width_override) return;

	const validate_columns_width = grid_row_prototype.validate_columns_width;
	grid_row_prototype.validate_columns_width = function () {
		if (
			this.frm?.doctype === "Journal Entry" &&
			this.grid?.doctype === "Journal Entry Account"
		) {
			return;
		}
		return validate_columns_width.call(this);
	};
	grid_row_prototype._accounting_custom_width_override = true;
}

function show_more_journal_rows(frm) {
	const pagination = frm.fields_dict.accounts?.grid?.grid_pagination;
	if (!pagination || pagination.page_length >= 25) return;
	pagination.page_length = 25;
	pagination.page_index = 1;
	pagination.total_pages = Math.ceil((frm.doc.accounts || []).length / pagination.page_length);
	pagination.render_pagination();
	frm.refresh_field("accounts");
}

frappe.ui.form.on("Journal Entry Account", {
	account: set_journal_row_exchange_rate,
	account_currency: set_journal_row_exchange_rate,
	accounts_add: set_journal_row_exchange_rate,
});

frappe.ui.form.on("Payment Entry", {
	setup(frm) {
		frm.company_exchange_rate_loading = false;
	},
	company(frm) {
		frm.company_currency_cache = null;
		return set_payment_exchange_rates(frm);
	},
	posting_date(frm) {
		return set_payment_exchange_rates(frm);
	},
	paid_from(frm) {
		return set_payment_exchange_rates(frm);
	},
	paid_to(frm) {
		return set_payment_exchange_rates(frm);
	},
	paid_from_account_currency(frm) {
		return set_payment_exchange_rates(frm);
	},
	paid_to_account_currency(frm) {
		return set_payment_exchange_rates(frm);
	},
	refresh(frm) {
		if (frm.is_new()) return set_payment_exchange_rates(frm);
	},
	validate(frm) {
		return set_payment_exchange_rates(frm, true);
	},
});

for (const doctype of ["Sales Order", "Purchase Order", "Purchase Invoice", "Sales Invoice"]) {
	frappe.ui.form.on(doctype, {
		setup(frm) {
			frm.company_exchange_rate_loading = false;
		},
		company(frm) {
			frm.company_currency_cache = null;
			return set_transaction_exchange_rate(frm);
		},
		currency(frm) {
			return set_transaction_exchange_rate(frm);
		},
		posting_date(frm) {
			return set_transaction_exchange_rate(frm);
		},
		transaction_date(frm) {
			return set_transaction_exchange_rate(frm);
		},
		refresh(frm) {
			if (frm.is_new()) return set_transaction_exchange_rate(frm);
		},
		validate(frm) {
			return set_transaction_exchange_rate(frm, true);
		},
	});
}

async function get_company_currency(frm) {
	if (frm.company_currency_cache) return frm.company_currency_cache;
	if (!frm.doc.company) return null;

	const result = await frappe.db.get_value("Company", frm.doc.company, "default_currency");
	frm.company_currency_cache = result?.message?.default_currency;
	return frm.company_currency_cache;
}

async function fetch_company_rate(frm, from_currency, transaction_date, mandatory) {
	const company_currency = await get_company_currency(frm);
	if (!company_currency) {
		frappe.throw(__("Default Currency is not configured for company {0}.", [frm.doc.company]));
	}

	if (from_currency === company_currency) return 1;

	const result = await frappe.call({
		method: company_exchange_rate_method,
		args: {
			company: frm.doc.company,
			from_currency,
			to_currency: company_currency,
			transaction_date,
		},
		freeze: mandatory,
		freeze_message: __("Getting company exchange rate..."),
	});
	const rate = Number(result.message?.exchange_rate || 0);
	if (rate <= 0) {
		frappe.throw(__("No valid Company Exchange Rate exists for {0} to {1}.", [
			from_currency,
			company_currency,
		]));
	}
	return rate;
}

async function set_all_journal_exchange_rates(frm, mandatory = false) {
	if (frm.company_exchange_rate_loading || !frm.doc.company || !frm.doc.posting_date) return;
	frm.company_exchange_rate_loading = true;
	try {
		for (const row of frm.doc.accounts || []) {
			if (!row.account_currency) continue;
			const rate = await fetch_company_rate(frm, row.account_currency, frm.doc.posting_date, mandatory);
			await frappe.model.set_value(row.doctype, row.name, "exchange_rate", rate);
		}
		frm.refresh_field("accounts");
	} catch (error) {
		if (mandatory) frappe.validated = false;
		throw error;
	} finally {
		frm.company_exchange_rate_loading = false;
	}
}

async function set_journal_row_exchange_rate(frm, cdt, cdn) {
	const row = locals[cdt][cdn];
	if (!row?.account_currency || !frm.doc.company || !frm.doc.posting_date) return;
	const rate = await fetch_company_rate(frm, row.account_currency, frm.doc.posting_date, false);
	await frappe.model.set_value(cdt, cdn, "exchange_rate", rate);
}

async function set_payment_exchange_rates(frm, mandatory = false) {
	if (frm.company_exchange_rate_loading || !frm.doc.company || !frm.doc.posting_date) return;
	frm.company_exchange_rate_loading = true;
	try {
		if (frm.doc.paid_from_account_currency) {
			await frm.set_value("source_exchange_rate", await fetch_company_rate(
				frm, frm.doc.paid_from_account_currency, frm.doc.posting_date, mandatory
			));
		}
		if (frm.doc.paid_to_account_currency) {
			await frm.set_value("target_exchange_rate", await fetch_company_rate(
				frm, frm.doc.paid_to_account_currency, frm.doc.posting_date, mandatory
			));
		}
	} catch (error) {
		if (mandatory) frappe.validated = false;
		throw error;
	} finally {
		frm.company_exchange_rate_loading = false;
	}
}

async function set_transaction_exchange_rate(frm, mandatory = false) {
	const transaction_date = frm.doc.posting_date || frm.doc.transaction_date;
	if (frm.company_exchange_rate_loading || !frm.doc.company || !frm.doc.currency || !transaction_date) return;
	frm.company_exchange_rate_loading = true;
	try {
		await frm.set_value("conversion_rate", await fetch_company_rate(
			frm, frm.doc.currency, transaction_date, mandatory
		));
	} catch (error) {
		if (mandatory) frappe.validated = false;
		throw error;
	} finally {
		frm.company_exchange_rate_loading = false;
	}
}
