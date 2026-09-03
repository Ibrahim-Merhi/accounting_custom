frappe.ui.form.on("Accounting Payment Entry", {
	setup(frm) {
		set_payment_queries(frm);
	},

	refresh(frm) {
		set_payment_queries(frm);
		add_payment_approval_actions(frm);
		if (frm.doc.posting_date) set_hijri_date(frm);
		if (frm.is_new()) refresh_currency_totals(frm);
		setTimeout(() => ensure_initial_payment_row(frm), 0);
		add_accounting_buttons(frm);
	},

	company(frm) {
		frm.set_value("custom_branch", null);
		frm.clear_table("custom_accounting_rows_copy");
		frm.clear_table("currency_totals");
		frm.refresh_field("currency_totals");
		frappe.db.get_value("Company", frm.doc.company, "default_currency").then((r) => {
			frm.set_value("custom_company_currency", r.message?.default_currency || null);
			ensure_initial_payment_row(frm);
		});
	},

	posting_date(frm) {
		set_hijri_date(frm);
		(frm.doc.custom_accounting_rows_copy || []).forEach((row) => update_row_rate(frm, row));
	},
});

function add_payment_approval_actions(frm) {
	if (frm.is_new() || frm.doc.docstatus !== 0) return;
	const roles = frappe.user_roles || [];
	const move = (action) => frappe.call({
		method: "accounting_custom.accounting_custom.doctype.accounting_payment_entry.accounting_payment_entry.set_approval_status",
		args: { name: frm.doc.name, action, notes: frm.doc.finance_notes },
		freeze: true,
		callback: () => frm.reload_doc(),
	});
	if (["Draft", "Returned"].includes(frm.doc.approval_status)) {
		frm.add_custom_button(__("Submit for Finance Approval"), () => move("Submit for Finance Approval"), __("Approval"));
	}
	if (frm.doc.approval_status === "Pending Finance Approval" && roles.some((role) => ["Finance Officer", "Accounts Manager", "System Manager"].includes(role))) {
		["Approve", "Return", "Reject"].forEach((action) => {
			frm.add_custom_button(__(action), () => move(action), __("Approval"));
		});
	}
}

function add_accounting_buttons(frm) {
	if (frm.is_new() || frm.doc.docstatus === 0) return;

	frm.add_custom_button(
		__("Ledger"),
		() => {
			frappe.route_options = {
				company: frm.doc.company,
				from_date: frm.doc.posting_date,
				to_date: moment(frm.doc.modified).format("YYYY-MM-DD"),
				voucher_no: frm.doc.name,
				group_by: "",
				show_cancelled_entries: frm.doc.docstatus === 2,
			};
			frappe.set_route("query-report", "General Ledger");
		},
		"fa fa-table"
	);

	if (frm.doc.docstatus === 1) {
		frm.add_custom_button(
			__("UnReconcile"),
			() => show_unreconcile_result(frm),
			__("Actions")
		);
	}
}

function show_unreconcile_result(frm) {
	frappe.call({
		method: "erpnext.accounts.doctype.unreconcile_payment.unreconcile_payment.doc_has_references",
		args: {
			doctype: frm.doc.doctype,
			docname: frm.doc.name,
		},
		freeze: true,
		callback(r) {
			if (!r.message) {
				frappe.msgprint(__("No reconciled allocations were found for this Accounting Payment Entry."));
				return;
			}

			frappe.msgprint(
				__("Unreconciliation is not available for Accounting Payment Entry allocations yet.")
			);
		},
	});
}

frappe.ui.form.on("Accounting Payment Detail", {
	cost_center(frm, cdt, cdn) {
		refresh_payment_row(frm, locals[cdt][cdn]);
	},

	account(frm, cdt, cdn) {
		refresh_payment_row(frm, locals[cdt][cdn]);
	},

	party_type(frm, cdt, cdn) {
		frappe.model.set_value(cdt, cdn, "party", null);
		frappe.model.set_value(cdt, cdn, "party_name", null);
		refresh_payment_row(frm, locals[cdt][cdn]);
	},

	party(frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		if (!row.party_type || !row.party) return;
		const fields = {
			Employee: "employee_name", Supplier: "supplier_name",
			Institution: "institution_name", Beneficiary: "full_name_ar",
		};
		frappe.db.get_value(row.party_type, row.party, fields[row.party_type]).then((r) => {
			frappe.model.set_value(cdt, cdn, "party_name", r.message?.[fields[row.party_type]] || row.party);
		});
	},

	mode_of_payment(frm, cdt, cdn) {
		set_row_currency(frm, locals[cdt][cdn]);
	},

	currency(frm, cdt, cdn) {
		update_row_rate(frm, locals[cdt][cdn]);
		refresh_currency_totals(frm);
	},

	amount(frm, cdt, cdn) {
		update_row_rate(frm, locals[cdt][cdn]);
		refresh_currency_totals(frm);
	},
});

function ensure_initial_payment_row(frm) {
	if (!frm.is_new() || (frm.doc.custom_accounting_rows_copy || []).length) return;
	const grid = frm.fields_dict.custom_accounting_rows_copy?.grid;
	if (grid) grid.add_new_row(null, null, true, null, true);
}

function refresh_currency_totals(frm) {
	const totals = {};
	(frm.doc.custom_accounting_rows_copy || []).forEach((row) => {
		if (row.currency) totals[row.currency] = (totals[row.currency] || 0) + flt(row.amount);
	});
	frm.clear_table("currency_totals");
	Object.entries(totals).forEach(([currency, amount]) => {
		const total = frm.add_child("currency_totals");
		total.currency = currency;
		total.total_debit = amount;
		total.total_credit = amount;
	});
	frm.refresh_field("currency_totals");
}

function set_hijri_date(frm) {
	if (!frm.doc.posting_date) return;
	const [year, month, day] = frm.doc.posting_date.split("-").map(Number);
	const parts = new Intl.DateTimeFormat("en-US-u-ca-islamic-umalqura", {
		year: "numeric", month: "numeric", day: "numeric",
	}).formatToParts(new Date(year, month - 1, day, 12));
	const value = Object.fromEntries(parts.map((part) => [part.type, part.value]));
	frm.set_value("custom_hijri_date", value.year + "/" + value.month + "/" + value.day);
}

function set_payment_queries(frm) {
	frm.set_query("custom_branch", () => ({
		filters: frm.doc.company ? { custom_company: frm.doc.company } : { name: ["=", ""] },
	}));
	frm.set_query("mode_of_payment", "custom_accounting_rows_copy", () => ({
		query: "accounting_custom.api.queries.mode_of_payment_by_company",
		filters: { company: frm.doc.company },
	}));
	frm.set_query("account", "custom_accounting_rows_copy", () => ({
		query: "erpnext.controllers.queries.get_account_list",
		filters: frm.doc.company ? { company: ["=", frm.doc.company], disabled: 0, is_group: 0 } : { name: ["=", ""] },
	}));
	frm.set_query("cost_center", "custom_accounting_rows_copy", () => ({
		filters: frm.doc.company ? { company: frm.doc.company, is_group: 0 } : { name: ["=", ""] },
	}));
	frm.set_query("party", "custom_accounting_rows_copy", (_doc, cdt, cdn) => {
		const row = locals[cdt][cdn];
		if (row.party_type === "Beneficiary") return { filters: {}, ignore_user_permissions: 1 };
		if (!frm.doc.company) return { filters: { name: ["=", ""] } };
		if (row.party_type === "Employee") return { filters: { company: frm.doc.company } };
		if (row.party_type === "Supplier") return {
			query: "accounting_custom.accounting_custom.doctype.accounting_payment_entry.accounting_payment_entry.supplier_by_company_query",
			filters: { company: frm.doc.company },
		};
		if (row.party_type === "Institution") return { filters: { company: frm.doc.company, disabled: 0 } };
		return { filters: { name: ["=", ""] } };
	});
}

function set_row_currency(frm, row) {
	if (!frm.doc.company || !row.mode_of_payment) {
		frappe.model.set_value(row.doctype, row.name, "currency", null);
		return;
	}
	frappe.call({
		method: "accounting_custom.accounting_custom.doctype.donation_entry.donation_entry.get_payment_currency",
		args: { mode_of_payment: row.mode_of_payment, company: frm.doc.company },
		callback(r) {
			frappe.model.set_value(row.doctype, row.name, "currency", r.message).then(() => {
				refresh_payment_row(frm, row);
				refresh_currency_totals(frm);
			});
		},
	});
}

function refresh_payment_row(frm, row) {
	setTimeout(() => {
		const grid_row = frm.fields_dict.custom_accounting_rows_copy.grid.grid_rows_by_docname[row.name];
		if (!grid_row) return;
		grid_row.refresh();
		grid_row.toggle_editable_row(true);
	}, 0);
}

function update_row_rate(frm, row) {
	if (!frm.doc.company || !frm.doc.custom_company_currency || !frm.doc.posting_date || !row.currency) return;
	frappe.call({
		method: "accounting_custom.api.exchange_rate.get_company_exchange_rate",
		args: { company: frm.doc.company, from_currency: row.currency, to_currency: frm.doc.custom_company_currency, transaction_date: frm.doc.posting_date },
		callback(r) {
			const rate = flt(r.message?.exchange_rate || 0);
			frappe.model.set_value(row.doctype, row.name, "exchange_rate", rate);
			frappe.model.set_value(row.doctype, row.name, "base_amount", flt(row.amount) * rate);
		},
	});
}
