frappe.ui.form.on("Accounting Currency Exchange", {
	setup(frm) {
		set_accounting_currency_exchange_queries(frm);
	},
	refresh(frm) {
		set_accounting_currency_exchange_queries(frm);
		if (frm.doc.journal_entry) {
			frm.add_custom_button(__("View Journal Entry"), () => {
				frappe.set_route("Form", "Journal Entry", frm.doc.journal_entry);
			});
		}
	},
	company(frm) {
		frm.set_value({
			from_mode_of_payment: null,
			to_mode_of_payment: null,
			source_account: null,
			target_account: null,
			from_cost_center: null,
			to_cost_center: null,
			from_currency: null,
			to_currency: null,
			to_amount: 0,
		});
		if (frm.doc.company) {
			frappe.db.get_value("Company", frm.doc.company, "default_currency").then((r) => {
				frm.set_value("company_currency", r.message?.default_currency || null);
			});
		}
	},
	from_mode_of_payment(frm) {
		return set_exchange_side(frm, "from");
	},
	to_mode_of_payment(frm) {
		return set_exchange_side(frm, "to");
	},
});

function set_accounting_currency_exchange_queries(frm) {
	const payment_query = () => ({
		query: "accounting_custom.api.queries.mode_of_payment_by_company",
		filters: { company: frm.doc.company },
	});
	frm.set_query("from_mode_of_payment", payment_query);
	frm.set_query("to_mode_of_payment", payment_query);
	const cost_center_query = () => ({
		filters: frm.doc.company
			? { company: frm.doc.company, is_group: 0 }
			: { name: ["=", ""] },
	});
	frm.set_query("from_cost_center", cost_center_query);
	frm.set_query("to_cost_center", cost_center_query);
}

async function set_exchange_side(frm, side) {
	const mode = frm.doc[`${side}_mode_of_payment`];
	if (!frm.doc.company || !mode) return;
	const result = await frappe.call({
		method: "accounting_custom.accounting_custom.doctype.accounting_currency_exchange.accounting_currency_exchange.get_mode_of_payment_details",
		args: { company: frm.doc.company, mode_of_payment: mode },
	});
	const account_field = side === "from" ? "source_account" : "target_account";
	await frm.set_value(account_field, result.message?.account || null);
	await frm.set_value(`${side}_currency`, result.message?.currency || null);
}
