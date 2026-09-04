frappe.ui.form.on("Accounting Receipt Entry", {
	setup(frm) {
		set_receipt_queries(frm);
	},
	refresh(frm) {
		set_receipt_queries(frm);
		add_receipt_actions(frm);
		if (frm.doc.posting_date) set_receipt_hijri_date(frm);
		setTimeout(() => ensure_receipt_row(frm), 0);
		if (!frm.is_new() && frm.doc.docstatus !== 0) {
			frm.add_custom_button(__("Ledger"), () => {
				frappe.route_options = {
					company: frm.doc.company,
					from_date: frm.doc.posting_date,
					to_date: moment(frm.doc.modified).format("YYYY-MM-DD"),
					voucher_no: frm.doc.name,
					group_by: "",
					show_cancelled_entries: frm.doc.docstatus === 2,
				};
				frappe.set_route("query-report", "General Ledger");
			}, "fa fa-table");
		}
	},
	company(frm) {
		frm.set_value("custom_branch", null);
		frm.clear_table("custom_accounting_rows_copy");
		frm.clear_table("currency_totals");
		frappe.db.get_value("Company", frm.doc.company, "default_currency").then((r) => {
			frm.set_value("custom_company_currency", r.message?.default_currency || null);
			ensure_receipt_row(frm);
		});
	},
	posting_date(frm) {
		set_receipt_hijri_date(frm);
		(frm.doc.custom_accounting_rows_copy || []).forEach((row) => update_receipt_rate(frm, row));
	},
});

frappe.ui.form.on("Accounting Payment Detail", {
	mode_of_payment(frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		if (frm.doctype !== "Accounting Receipt Entry") return;
		frappe.call({
			method: "accounting_custom.accounting_custom.doctype.donation_entry.donation_entry.get_payment_currency",
			args: { mode_of_payment: row.mode_of_payment, company: frm.doc.company },
			callback: (r) => frappe.model.set_value(cdt, cdn, "currency", r.message),
		});
	},
	currency(frm, cdt, cdn) {
		if (frm.doctype === "Accounting Receipt Entry") update_receipt_rate(frm, locals[cdt][cdn]);
	},
	amount(frm, cdt, cdn) {
		if (frm.doctype !== "Accounting Receipt Entry") return;
		update_receipt_rate(frm, locals[cdt][cdn]);
		refresh_receipt_totals(frm);
	},
	party_type(frm, cdt, cdn) {
		if (frm.doctype !== "Accounting Receipt Entry") return;
		frappe.model.set_value(cdt, cdn, "party", null);
		frappe.model.set_value(cdt, cdn, "party_name", null);
	},
	party(frm, cdt, cdn) {
		if (frm.doctype !== "Accounting Receipt Entry") return;
		const row = locals[cdt][cdn];
		const fields = { Employee: "employee_name", Supplier: "supplier_name", Institution: "institution_name", Beneficiary: "full_name_ar" };
		if (row.party_type && row.party && fields[row.party_type]) {
			frappe.db.get_value(row.party_type, row.party, fields[row.party_type]).then((r) => {
				frappe.model.set_value(cdt, cdn, "party_name", r.message?.[fields[row.party_type]] || row.party);
			});
		}
	},
});

function set_receipt_queries(frm) {
	const child = "custom_accounting_rows_copy";
	frm.set_query("custom_branch", () => ({ filters: frm.doc.company ? { custom_company: frm.doc.company } : { name: ["=", ""] } }));
	frm.set_query("mode_of_payment", child, () => ({ query: "accounting_custom.api.queries.mode_of_payment_by_company", filters: { company: frm.doc.company } }));
	frm.set_query("account", child, () => ({ query: "erpnext.controllers.queries.get_account_list", filters: frm.doc.company ? { company: ["=", frm.doc.company], disabled: 0, is_group: 0 } : { name: ["=", ""] } }));
	frm.set_query("cost_center", child, () => ({ filters: frm.doc.company ? { company: frm.doc.company, is_group: 0 } : { name: ["=", ""] } }));
	frm.set_query("party", child, (_doc, cdt, cdn) => {
		const row = locals[cdt][cdn];
		if (row.party_type === "Beneficiary") return { filters: {}, ignore_user_permissions: 1 };
		if (row.party_type === "Employee") return { filters: { company: frm.doc.company } };
		if (row.party_type === "Supplier") return { query: "accounting_custom.accounting_custom.doctype.accounting_payment_entry.accounting_payment_entry.supplier_by_company_query", filters: { company: frm.doc.company } };
		if (row.party_type === "Institution") return { filters: { company: frm.doc.company, disabled: 0 } };
		return { filters: { name: ["=", ""] } };
	});
}

function ensure_receipt_row(frm) {
	if (!frm.is_new() || (frm.doc.custom_accounting_rows_copy || []).length) return;
	frm.fields_dict.custom_accounting_rows_copy?.grid.add_new_row(null, null, true, null, true);
}

function update_receipt_rate(frm, row) {
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

function refresh_receipt_totals(frm) {
	const totals = {};
	(frm.doc.custom_accounting_rows_copy || []).forEach((row) => {
		if (row.currency) totals[row.currency] = (totals[row.currency] || 0) + flt(row.amount);
	});
	frm.clear_table("currency_totals");
	Object.entries(totals).forEach(([currency, amount]) => {
		const total = frm.add_child("currency_totals", { currency, total_debit: amount, total_credit: amount });
		total.currency = currency;
	});
	frm.refresh_field("currency_totals");
}

function add_receipt_actions(frm) {
	if (frm.is_new() || frm.doc.docstatus !== 0) return;
	const move = (action) => frappe.call({
		method: "accounting_custom.accounting_custom.doctype.accounting_receipt_entry.accounting_receipt_entry.set_approval_status",
		args: { name: frm.doc.name, action, notes: frm.doc.finance_notes }, freeze: true,
		callback: () => frm.reload_doc(),
	});
	if (["Draft", "Returned"].includes(frm.doc.approval_status)) frm.add_custom_button(__("Submit for Finance Approval"), () => move("Submit for Finance Approval"), __("Approval"));
	if (frm.doc.approval_status === "Pending Finance Approval" && (frappe.user_roles || []).some((role) => ["Finance Officer", "Accounts Manager", "System Manager"].includes(role))) {
		["Approve", "Return", "Reject"].forEach((action) => frm.add_custom_button(__(action), () => move(action), __("Approval")));
	}
}

function set_receipt_hijri_date(frm) {
	if (!frm.doc.posting_date) return;
	const [year, month, day] = frm.doc.posting_date.split("-").map(Number);
	const parts = new Intl.DateTimeFormat("en-US-u-ca-islamic-umalqura", { year: "numeric", month: "numeric", day: "numeric" }).formatToParts(new Date(year, month - 1, day, 12));
	const value = Object.fromEntries(parts.map((part) => [part.type, part.value]));
	frm.set_value("custom_hijri_date", `${value.year}/${value.month}/${value.day}`);
}
