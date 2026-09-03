frappe.ui.form.on("Donation Entry", {
	setup(frm) {
		set_queries(frm);
	},

	refresh(frm) {
		prepare_compact_layout(frm);
		add_approval_actions(frm);
		add_quick_donor_action(frm);
		set_queries(frm);
		if (frm.doc.donor) load_donor_accounts(frm);
		if (frm.doc.company) fetch_company_currency(frm);
		if (!frm.is_new() && [1, 2].includes(frm.doc.docstatus)) add_ledger_button(frm);
	},

	onload(frm) {
		if (frm.is_new() && frm.doc.posting_date && !frm.doc.custom_hijri_date) set_hijri_date(frm);
	},

	donor(frm) {
		frm.set_value("company", null);
		frm.set_value("donor_account", null);
		if (frm.doc.donor) load_donor_accounts(frm, true);
	},

	company(frm) {
		frm.set_value("donor_account", null);
		frm.clear_table("payments");
		frm.refresh_field("payments");
		if (frm.doc.company) {
			load_donor_accounts(frm);
			fetch_company_currency(frm);
		}
	},

	posting_date(frm) {
		set_hijri_date(frm);
		refresh_payment_rates(frm);
	},

	validate(frm) {
		sync_legacy_payment_fields(frm);
	},
});

function prepare_compact_layout(frm) {
	frm.wrapper.addClass("accounting-custom-donation-entry");
	$(frm.fields_dict.payments?.wrapper).addClass("donation-payments-grid");
}

function sync_legacy_payment_fields(frm) {
	const first_payment = (frm.doc.payments || [])[0];
	if (!first_payment) return;
	[
		"mode_of_payment",
		"cost_center",
		"currency",
		"donation_amount",
		"exchange_rate",
		"received_in_account",
	].forEach((fieldname) => {
		frm.doc[fieldname] = first_payment[fieldname] || null;
	});
}

function add_quick_donor_action(frm) {
	if (!frm.is_new() && frm.doc.docstatus !== 0) return;
	if (!(frappe.user_roles || []).includes("Collector")) return;
	frm.add_custom_button(__("Quick Donor"), () => {
		const dialog = new frappe.ui.Dialog({
			title: __("Quick Donor"),
			fields: [
				{ fieldname: "donor_name", fieldtype: "Data", label: __("Donor Name"), reqd: 1 },
				{ fieldname: "phone_number", fieldtype: "Data", label: __("Phone Number"), reqd: 1 },
				{ fieldname: "company", fieldtype: "Link", label: __("Company"), options: "Company", reqd: 1, default: frm.doc.company },
			],
			primary_action_label: __("Create and Select"),
			primary_action(values) {
				frappe.call({
					method: "accounting_custom.accounting_custom.doctype.donation_entry.donation_entry.quick_create_donor",
					args: values,
					freeze: true,
					callback(r) {
						dialog.hide();
						frm.set_value("donor", r.message.name);
						frm.set_value("donor_name", r.message.donor_name);
						frm.set_value("company", values.company);
					},
				});
			},
		});
		dialog.show();
	});
}

function add_approval_actions(frm) {
	if (frm.is_new() || frm.doc.docstatus !== 0) return;
	const roles = frappe.user_roles || [];
	const call_action = (action) => {
		frappe.call({
			method: "accounting_custom.accounting_custom.doctype.donation_entry.donation_entry.set_approval_status",
			args: { name: frm.doc.name, action, notes: frm.doc.finance_notes },
			freeze: true,
			callback: () => frm.reload_doc(),
		});
	};
	if (["Draft", "Returned"].includes(frm.doc.approval_status) && roles.some((r) => ["Collector", "Finance Officer", "Accounts Manager", "System Manager"].includes(r))) {
		frm.add_custom_button(__("Submit for Finance Approval"), () => call_action("Submit for Finance Approval"), __("Approval"));
	}
	if (frm.doc.approval_status === "Pending Finance Approval" && roles.some((r) => ["Finance Officer", "Accounts Manager", "System Manager"].includes(r))) {
		["Approve", "Return", "Reject"].forEach((action) => {
			frm.add_custom_button(__(action), () => call_action(action), __("Approval"));
		});
	}
}

frappe.ui.form.on("Donation Payment Detail", {
	mode_of_payment(frm, cdt, cdn) {
		set_payment_currency(frm, locals[cdt][cdn]);
	},

	currency(frm, cdt, cdn) {
		set_payment_rate(frm, locals[cdt][cdn]);
	},

	donation_amount(frm, cdt, cdn) {
		set_payment_rate(frm, locals[cdt][cdn]);
	},

});

function set_queries(frm) {
	frm.donor_companies = frm.donor_companies || [];
	frm.set_query("company", () => ({
		filters: frm.donor_companies.length ? { name: ["in", frm.donor_companies] } : { name: ["=", ""] },
	}));
	frm.set_query("donor_account", () => account_query(frm.doc.company));
	frm.set_query("project", () => ({ filters: frm.doc.company ? { company: frm.doc.company } : { name: ["=", ""] } }));
	frm.set_query("mode_of_payment", "payments", () => mode_of_payment_query(frm.doc.company));
	frm.set_query("cost_center", "payments", () => ({
		filters: { company: frm.doc.company, is_group: 0 },
	}));
	frm.set_query("received_in_account", "payments", () => account_query(frm.doc.company));
}

function mode_of_payment_query(company) {
	return {
		query: "accounting_custom.api.queries.mode_of_payment_by_company",
		filters: { company },
	};
}

function account_query(company) {
	return {
		query: "erpnext.controllers.queries.get_account_list",
		filters: company ? { company, disabled: 0, is_group: 0 } : { name: ["=", ""] },
	};
}

function load_donor_accounts(frm, auto_select = false) {
	if (!frm.doc.donor) return;
	frappe.db.get_doc("Donor", frm.doc.donor).then((donor) => {
		const rows = donor.custom_accounts || [];
		const companies = [...new Set(rows.map((row) => row.company).filter(Boolean))];
		frm.donor_companies = companies;
		set_queries(frm);
		if (auto_select && companies.length === 1) frm.set_value("company", companies[0]);
		const match = rows.find((row) => row.company === frm.doc.company);
		if (match?.account) frm.set_value("donor_account", match.account);
	});
}

function fetch_company_currency(frm) {
	frappe.db.get_value("Company", frm.doc.company, "default_currency").then((r) => {
		if (r.message?.default_currency) {
			frm.set_value("custom_company_currency", r.message.default_currency);
			refresh_payment_rates(frm);
		}
	});
}

function set_payment_currency(frm, row) {
	if (!frm.doc.company || !row.mode_of_payment) {
		frappe.model.set_value(row.doctype, row.name, "currency", null);
		return;
	}
	frappe.call({
		method: "accounting_custom.accounting_custom.doctype.donation_entry.donation_entry.get_payment_currency",
		args: { mode_of_payment: row.mode_of_payment, company: frm.doc.company },
		callback(r) {
			frappe.model.set_value(row.doctype, row.name, "currency", r.message);
		},
	});
}

function refresh_payment_rates(frm) {
	(frm.doc.payments || []).forEach((row) => set_payment_rate(frm, row));
}

function set_payment_rate(frm, row) {
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

function set_hijri_date(frm) {
	if (!frm.doc.posting_date) return;
	const [year, month, day] = frm.doc.posting_date.split("-").map(Number);
	const parts = new Intl.DateTimeFormat("en-US-u-ca-islamic-umalqura", {
		year: "numeric", month: "numeric", day: "numeric",
	}).formatToParts(new Date(year, month - 1, day, 12));
	const value = Object.fromEntries(parts.map((part) => [part.type, part.value]));
	frm.set_value("custom_hijri_date", `${value.year}/${value.month}/${value.day}`);
}

function add_ledger_button(frm) {
	frm.add_custom_button(__("Accounting Ledger"), () => {
		frappe.set_route("query-report", "General Ledger", {
			company: frm.doc.company,
			from_date: frm.doc.posting_date,
			to_date: frm.doc.posting_date,
			voucher_no: frm.doc.name,
			add_values_in_transaction_currency: 1,
			show_cancelled_entries: frm.doc.docstatus === 2 ? 1 : 0,
		});
	}, __("View"));
}
