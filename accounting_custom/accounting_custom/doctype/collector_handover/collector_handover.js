frappe.ui.form.on("Collector Handover", {
	setup(frm) {
		set_handover_queries(frm);
	},
	refresh(frm) {
		set_handover_queries(frm);
	},
	company(frm) {
		frm.set_value("collector", null);
		frm.clear_table("lines");
		frm.refresh_field("lines");
	},
	collector(frm) {
		frm.clear_table("lines");
		frm.refresh_field("lines");
	},
});

frappe.ui.form.on("Collector Handover Detail", {
	currency(frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		if (!frm.doc.collector || !row.currency) return;
		frappe.call({
			method: "accounting_custom.accounting_custom.doctype.collector_handover.collector_handover.get_custody_account",
			args: { collector: frm.doc.collector, currency: row.currency },
			callback: (r) => frappe.model.set_value(cdt, cdn, "source_account", r.message),
		});
	},
});

function set_handover_queries(frm) {
	const empty = { name: ["=", ""] };
	frm.set_query("collector", () => ({
		filters: frm.doc.company ? { company: frm.doc.company, active: 1 } : empty,
	}));
	frm.set_query("donation_entry", "lines", () => ({
		filters: frm.doc.collector
			? { company: frm.doc.company, collector: frm.doc.collector, docstatus: 1, treasury_status: ["!=", "Handed Over"] }
			: empty,
	}));
	frm.set_query("source_account", "lines", (_doc, cdt, cdn) => {
		const row = locals[cdt][cdn];
		return { filters: row.currency ? { company: frm.doc.company, account_currency: row.currency, is_group: 0 } : empty };
	});
	frm.set_query("destination_account", "lines", (_doc, cdt, cdn) => {
		const row = locals[cdt][cdn];
		return { filters: row.currency ? { company: frm.doc.company, account_currency: row.currency, is_group: 0, disabled: 0 } : empty };
	});
	frm.set_query("cost_center", "lines", () => ({
		filters: frm.doc.company ? { company: frm.doc.company, is_group: 0 } : empty,
	}));
}
