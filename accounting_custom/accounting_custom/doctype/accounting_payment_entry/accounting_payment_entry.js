frappe.ui.form.on("Accounting Payment Entry", {
	setup(frm) {
		set_payment_queries(frm);
	},

	refresh(frm) {
		set_payment_queries(frm);
	},

	company(frm) {
		frm.set_value("custom_branch", null);
		frm.clear_table("accounts");
		frappe.db.get_value("Company", frm.doc.company, "default_currency").then((r) => {
			frm.set_value("custom_company_currency", r.message?.default_currency || null);
		});
	},

	posting_date(frm) {
		(frm.doc.accounts || []).forEach((row) => update_row_rate(frm, row));
	},
});

frappe.ui.form.on("Accounting Payment Detail", {
	party_type(frm, cdt, cdn) {
		frappe.model.set_value(cdt, cdn, "party", null);
		frappe.model.set_value(cdt, cdn, "party_name", null);
	},

	party(frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		if (!row.party_type || !row.party) return;
		const fields = {
			Employee: "employee_name", Supplier: "supplier_name",
			Institution: "institution_name", Beneficiary: "beneficiary_name",
		};
		frappe.db.get_value(row.party_type, row.party, fields[row.party_type]).then((r) => {
			frappe.model.set_value(cdt, cdn, "party_name", r.message?.[fields[row.party_type]] || row.party);
		});
	},

	currency(frm, cdt, cdn) {
		update_row_rate(frm, locals[cdt][cdn]);
	},

	debit(frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		if (flt(row.debit)) frappe.model.set_value(cdt, cdn, "credit", 0);
		update_row_rate(frm, row);
	},

	credit(frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		if (flt(row.credit)) frappe.model.set_value(cdt, cdn, "debit", 0);
		update_row_rate(frm, row);
	},
});

function set_payment_queries(frm) {
	frm.set_query("custom_branch", () => ({
		filters: frm.doc.company ? { custom_company: frm.doc.company } : { name: ["=", ""] },
	}));
	frm.set_query("account", "accounts", () => ({
		query: "erpnext.controllers.queries.get_account_list",
		filters: frm.doc.company ? { company: frm.doc.company, disabled: 0, is_group: 0 } : { name: ["=", ""] },
	}));
	frm.set_query("cost_center", "accounts", () => ({
		filters: frm.doc.company ? { company: frm.doc.company, is_group: 0 } : { name: ["=", ""] },
	}));
	frm.set_query("party", "accounts", (_doc, cdt, cdn) => {
		const row = locals[cdt][cdn];
		if (["Employee", "Beneficiary"].includes(row.party_type)) return { filters: { company: frm.doc.company } };
		if (["Supplier", "Institution"].includes(row.party_type)) return { filters: { disabled: 0 } };
		return { filters: { name: ["=", ""] } };
	});
}

function update_row_rate(frm, row) {
	if (!frm.doc.company || !frm.doc.custom_company_currency || !frm.doc.posting_date || !row.currency) return;
	frappe.call({
		method: "accounting_custom.api.exchange_rate.get_company_exchange_rate",
		args: { company: frm.doc.company, from_currency: row.currency, to_currency: frm.doc.custom_company_currency, transaction_date: frm.doc.posting_date },
		callback(r) {
			const rate = flt(r.message?.exchange_rate || 0);
			frappe.model.set_value(row.doctype, row.name, "exchange_rate", rate);
			frappe.model.set_value(row.doctype, row.name, "base_debit", flt(row.debit) * rate);
			frappe.model.set_value(row.doctype, row.name, "base_credit", flt(row.credit) * rate);
		},
	});
}
