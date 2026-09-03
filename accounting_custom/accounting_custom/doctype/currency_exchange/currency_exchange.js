frappe.ui.form.on("Currency Exchange", {
	setup(frm) {
		set_currency_exchange_queries(frm);
	},
	refresh(frm) {
		set_currency_exchange_queries(frm);
		if (frm.doc.journal_entry) {
			frm.add_custom_button(__("Journal Entry"), () => {
				frappe.set_route("Form", "Journal Entry", frm.doc.journal_entry);
			}, __("View"));
		}
	},
	company(frm) {
		frm.set_value({
			custom_branch: null,
			from_mode_of_payment: null,
			to_mode_of_payment: null,
			source_account: null,
			target_account: null,
			from_currency: null,
			to_currency: null,
			exchange_rate: 0,
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
	posting_date: update_exchange_amount,
	from_amount: update_exchange_amount,
});

function set_currency_exchange_queries(frm) {
	const payment_query = () => ({
		query: "accounting_custom.api.queries.mode_of_payment_by_company",
		filters: { company: frm.doc.company },
	});
	frm.set_query("from_mode_of_payment", payment_query);
	frm.set_query("to_mode_of_payment", payment_query);
	frm.set_query("custom_branch", () => ({
		filters: frm.doc.company ? { custom_company: frm.doc.company } : { name: ["=", ""] },
	}));
}

async function set_exchange_side(frm, side) {
	const mode = frm.doc[`${side}_mode_of_payment`];
	if (!frm.doc.company || !mode) return;
	const result = await frappe.call({
		method: "accounting_custom.accounting_custom.doctype.currency_exchange.currency_exchange.get_mode_of_payment_details",
		args: { company: frm.doc.company, mode_of_payment: mode },
	});
	const account_field = side === "from" ? "source_account" : "target_account";
	await frm.set_value(account_field, result.message?.account || null);
	await frm.set_value(`${side}_currency`, result.message?.currency || null);
	return update_exchange_amount(frm);
}

async function update_exchange_amount(frm) {
	if (!frm.doc.company || !frm.doc.posting_date || !frm.doc.from_currency ||
		!frm.doc.to_currency || !frm.doc.from_amount) return;
	const [from_result, to_result] = await Promise.all([
		frappe.call({
			method: "accounting_custom.api.exchange_rate.get_company_exchange_rate",
			args: { company: frm.doc.company, from_currency: frm.doc.from_currency,
				to_currency: frm.doc.company_currency, transaction_date: frm.doc.posting_date },
		}),
		frappe.call({
			method: "accounting_custom.api.exchange_rate.get_company_exchange_rate",
			args: { company: frm.doc.company, from_currency: frm.doc.to_currency,
				to_currency: frm.doc.company_currency, transaction_date: frm.doc.posting_date },
		}),
	]);
	const from_rate = Number(from_result.message?.exchange_rate || 0);
	const to_rate = Number(to_result.message?.exchange_rate || 0);
	if (from_rate <= 0 || to_rate <= 0) return;
	const rate = from_rate / to_rate;
	await frm.set_value("exchange_rate", rate);
	await frm.set_value("to_amount", Number(frm.doc.from_amount) * rate);
}
