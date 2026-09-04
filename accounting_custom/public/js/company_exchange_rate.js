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
	install_journal_width_validation_override(grid);

	$(frm.fields_dict.accounts.wrapper).addClass("accounting-custom-wide-journal-grid");
	install_wide_column_renderer(grid);
	requestAnimationFrame(() => enable_journal_grid_wheel_scroll(frm));
	install_journal_link_dropdown_space(frm);
}

function install_journal_link_dropdown_space(frm) {
	const wrapper = $(frm.fields_dict.accounts?.wrapper);
	if (wrapper.data("accounting-custom-dropdown-space")) return;

	wrapper.data("accounting-custom-dropdown-space", true);
	wrapper.on("focusin.accountingCustom input.accountingCustom", ".awesomplete input", (event) => {
		requestAnimationFrame(() => position_journal_link_dropdown(event.currentTarget));
	});
	wrapper.on("focusout.accountingCustom", ".awesomplete input", (event) => {
		setTimeout(() => {
			const menu = $(event.currentTarget).closest(".awesomplete").children("ul").get(0);
			if (menu) menu.removeAttribute("style");
		}, 250);
	});
}

function position_journal_link_dropdown(input) {
	const menu = $(input).closest(".awesomplete").children("ul").get(0);
	if (!menu) return;
	const input_rect = input.getBoundingClientRect();
	menu.style.setProperty("position", "fixed", "important");
	menu.style.setProperty("left", `${input_rect.left}px`, "important");
	menu.style.setProperty("top", `${input_rect.bottom + 2}px`, "important");
	menu.style.setProperty("width", `${Math.max(input_rect.width, 320)}px`, "important");
	menu.style.setProperty("max-height", "260px", "important");
	menu.style.setProperty("overflow-y", "auto", "important");
	menu.style.setProperty("z-index", "1060", "important");
}

function install_journal_width_validation_override(grid) {
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

function enable_journal_grid_wheel_scroll(frm) {
	const field = $(frm.fields_dict.accounts?.wrapper);
	const container = field.find(".form-grid-container").get(0);
	const form_grid = field.find(".form-grid").get(0);
	if (!container || !form_grid) return;

	field.find(".journal-grid-horizontal-scroll").remove();
	form_grid.style.transform = "none";

	if (container._accounting_custom_wheel_handler) {
		container.removeEventListener("wheel", container._accounting_custom_wheel_handler);
	}
	container._accounting_custom_wheel_handler = (event) => {
		if (container.scrollWidth <= container.clientWidth) return;
		const distance = Math.abs(event.deltaX) > Math.abs(event.deltaY)
			? event.deltaX
			: event.deltaY;
		if (!distance) return;
		const previous_position = container.scrollLeft;
		container.scrollLeft = Math.max(
			0,
			Math.min(container.scrollWidth - container.clientWidth, previous_position + distance)
		);
		if (container.scrollLeft === previous_position) return;
		event.preventDefault();
	};
	container.addEventListener("wheel", container._accounting_custom_wheel_handler, {
		passive: false,
	});
}

function install_wide_column_renderer(grid) {
	const grid_prototype = Object.getPrototypeOf(grid);
	if (!grid_prototype._accounting_custom_wide_columns_override) {
		const setup_visible_columns = grid_prototype.setup_visible_columns;
		grid_prototype.setup_visible_columns = function () {
			const result = setup_visible_columns.call(this);
			if (
				this.frm?.doctype !== "Journal Entry" ||
				this.doctype !== "Journal Entry Account" ||
				!this.user_defined_columns?.length
			) {
				return result;
			}

			const rendered_fields = new Set(
				(this.visible_columns || []).map(([field]) => field.fieldname)
			);
			for (const field of this.user_defined_columns) {
				if (
					rendered_fields.has(field.fieldname) ||
					field.hidden ||
					frappe.model.layout_fields.includes(field.fieldtype) ||
					!this.frm.get_perm(field.permlevel, "read")
				) {
					continue;
				}
				field.colsize = cint(field.columns) || 1;
				this.visible_columns.push([field, field.colsize]);
			}
			const total_width = this.visible_columns.reduce(
				(total, [, width]) => total + cint(width),
				0
			);
			this.form_grid.css("width", `${total_width * 120 + 150}px`);
			return result;
		};
		grid_prototype._accounting_custom_wide_columns_override = true;
	}

	if (!grid._accounting_custom_wide_columns_initialized) {
		grid._accounting_custom_wide_columns_initialized = true;
		grid.visible_columns = [];
		grid.reset_grid();
	}
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
