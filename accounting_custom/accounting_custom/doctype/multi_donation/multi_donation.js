frappe.ui.form.on("Multi Donation", {
	setup(frm) {
		set_queries(frm);
	},

	refresh(frm) {
		set_queries(frm);
		add_approval_actions(frm);
		if (frm.doc.journal_entry) {
			frm.add_custom_button(__("View Journal Entry"), () => {
				frappe.set_route("Form", "Journal Entry", frm.doc.journal_entry);
			});
		}
	},

	company(frm) {
		frm.set_value("custom_branch", null);
		frm.set_value("cost_center", null);
		frm.set_value("donor_account", null);
		frm.set_value("received_in_account", null);
		frm.clear_table("donations");
		frm.refresh_field("donations");
		set_queries(frm);
		if (frm.doc.company) {
			frappe.db.get_value("Company", frm.doc.company, "default_currency").then((r) => {
				frm.set_value("custom_company_currency", r.message?.default_currency || null);
			});
		}
	},

	posting_date(frm) {
		refresh_rates(frm);
	},
});

frappe.ui.form.on("Multi Donation Detail", {
	donor(frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		if (!row.donor || !frm.doc.company) return;
		frappe.db.get_doc("Donor", row.donor).then((donor) => {
			const match = (donor.custom_accounts || []).find((item) => item.company === frm.doc.company);
			frappe.model.set_value(cdt, cdn, "donor_account", match?.account || null);
			if (!frm.doc.donor_account && match?.account) frm.set_value("donor_account", match.account);
		});
	},

	mode_of_payment(frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		if (!frm.doc.company || !row.mode_of_payment) return;
		frappe.call({
			method: "accounting_custom.accounting_custom.doctype.donation_entry.donation_entry.get_payment_currency",
			args: {mode_of_payment: row.mode_of_payment, company: frm.doc.company},
			callback(r) {
				frappe.model.set_value(cdt, cdn, "currency", r.message).then(() => set_rate(frm, row));
			},
		});
	},

	donation_amount(frm, cdt, cdn) {
		set_rate(frm, locals[cdt][cdn]);
	},
});

function set_queries(frm) {
	frm.set_query("custom_branch", () => ({
		filters: frm.doc.company ? {custom_company: frm.doc.company} : {name: ["=", ""]},
	}));
	frm.set_query("cost_center", () => ({
		filters: frm.doc.company ? {company: frm.doc.company, is_group: 0} : {name: ["=", ""]},
	}));
	["donor_account", "received_in_account"].forEach((fieldname) => {
		frm.set_query(fieldname, () => ({
			query: "erpnext.controllers.queries.get_account_list",
			filters: frm.doc.company ? {company: frm.doc.company, disabled: 0, is_group: 0} : {name: ["=", ""]},
		}));
	});
	frm.set_query("mode_of_payment", "donations", () => ({
		query: "accounting_custom.api.queries.mode_of_payment_by_company",
		filters: {company: frm.doc.company},
	}));
}

function set_rate(frm, row) {
	if (!frm.doc.company || !frm.doc.posting_date || !frm.doc.custom_company_currency || !row.currency) return;
	frappe.call({
		method: "accounting_custom.api.exchange_rate.get_company_exchange_rate",
		args: {
			company: frm.doc.company,
			from_currency: row.currency,
			to_currency: frm.doc.custom_company_currency,
			transaction_date: frm.doc.posting_date,
		},
		callback(r) {
			const rate = flt(r.message?.exchange_rate || 0);
			frappe.model.set_value(row.doctype, row.name, "exchange_rate", rate);
			frappe.model.set_value(row.doctype, row.name, "base_amount", flt(row.donation_amount) * rate);
		},
	});
}

function refresh_rates(frm) {
	(frm.doc.donations || []).forEach((row) => set_rate(frm, row));
}

function add_approval_actions(frm) {
	if (frm.is_new() || frm.doc.docstatus !== 0) return;
	const roles = frappe.user_roles || [];
	const call_action = (action) => frappe.call({
		method: "accounting_custom.accounting_custom.doctype.multi_donation.multi_donation.set_approval_status",
		args: {name: frm.doc.name, action, notes: frm.doc.finance_notes},
		freeze: true,
		callback: () => frm.reload_doc(),
	});
	if (["Draft", "Returned"].includes(frm.doc.approval_status)
		&& roles.some((role) => ["Accounts User", "Finance Officer", "Accounts Manager", "Treasurer", "System Manager"].includes(role))) {
		frm.add_custom_button(__("Submit for Finance Approval"), () => call_action("Submit for Finance Approval"), __("Approval"));
	}
	if (frm.doc.approval_status === "Pending Finance Approval"
		&& roles.some((role) => ["Finance Officer", "Accounts Manager", "Treasurer", "System Manager"].includes(role))) {
		["Approve", "Return", "Reject"].forEach((action) => {
			frm.add_custom_button(__(action), () => call_action(action), __("Approval"));
		});
	}
}
