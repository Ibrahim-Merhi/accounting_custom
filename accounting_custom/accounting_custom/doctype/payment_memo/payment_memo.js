frappe.ui.form.on("Payment Memo", {
	setup(frm) {
		set_payment_memo_queries(frm);
	},
	refresh(frm) {
		set_payment_memo_queries(frm);
		add_payment_memo_actions(frm);
		add_ceo_comment_action(frm);
	},
	company(frm) {
		frm.set_value("payment_account", null);
		frm.clear_table("allocations");
		frm.refresh_field("allocations");
	},
	currency(frm) {
		(frm.doc.allocations || []).forEach((row) => {
			frappe.model.set_value(row.doctype, row.name, "currency", frm.doc.currency);
		});
	},
});

frappe.ui.form.on("Payment Memo Detail", {
	allocations_add(frm, cdt, cdn) {
		frappe.model.set_value(cdt, cdn, "currency", frm.doc.currency);
	},
});

function set_payment_memo_queries(frm) {
	const empty = { name: ["=", ""] };
	const company = frm.doc.company;
	frm.set_query("payment_account", () => ({ filters: company ? { company, is_group: 0, disabled: 0 } : empty }));
	frm.set_query("account", "allocations", () => ({ filters: company ? { company, is_group: 0, disabled: 0 } : empty }));
	frm.set_query("cost_center", "allocations", () => ({ filters: company ? { company, is_group: 0 } : empty }));
	frm.set_query("project", () => ({ filters: company ? { company } : empty }));
	frm.set_query("project", "allocations", () => ({ filters: company ? { company } : empty }));
}

function add_ceo_comment_action(frm) {
	if (frm.is_new() || !(frappe.user_roles || []).some((role) => ["CEO", "System Manager"].includes(role))) return;
	frm.add_custom_button(__("Add CEO Comment"), () => {
		frappe.prompt(
			[{ fieldname: "comment", fieldtype: "Small Text", label: __("CEO Comment"), reqd: 1, default: frm.doc.ceo_comment }],
			(values) => frappe.call({
				method: "accounting_custom.accounting_custom.doctype.payment_memo.payment_memo.add_ceo_comment",
				args: { name: frm.doc.name, comment: values.comment },
				callback: () => frm.reload_doc(),
			}),
			__("CEO Comment"),
		);
	}, __("Workflow"));
}

function add_payment_memo_actions(frm) {
	if (frm.is_new() || frm.doc.docstatus !== 0) return;
	const roles = frappe.user_roles || [];
	const stateRole = {
		"Pending HR Coordinator": "HR Coordinator",
		"Pending Manager": "Responsible Manager",
		"Pending Finance": "Finance Officer",
		"Pending President": "Association President",
		"Pending Treasurer": "Treasurer",
	};
	const move = (action) => frappe.call({
		method: "accounting_custom.accounting_custom.doctype.payment_memo.payment_memo.transition",
		args: { name: frm.doc.name, action },
		freeze: true,
		callback: () => frm.reload_doc(),
	});
	if (["Draft", "Returned"].includes(frm.doc.approval_status)) {
		frm.add_custom_button(__("Submit Request"), () => move("Submit Request"), __("Workflow"));
	}
	const required = stateRole[frm.doc.approval_status];
	if (required && (roles.includes(required) || roles.includes("System Manager"))) {
		["Approve", "Return", "Reject"].forEach((action) => {
			frm.add_custom_button(__(action), () => move(action), __("Workflow"));
		});
	}
}
