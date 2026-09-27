frappe.ui.form.on("Payroll Entry", {
	setup(frm) {
		suppress_standard_bank_button_for_managed_payroll(frm);
		frm.set_query("employee", "custom_manual_deductions", () => ({filters: {company: frm.doc.company, status: "Active"}}));
		frm.set_query("salary_component", "custom_manual_deductions", () => ({filters: {type: "Deduction", disabled: 0}}));
		frm.set_query("payment_account", "custom_bank_payment_allocations", () => ({filters: {
			company: frm.doc.company, is_group: 0, disabled: 0,
			account_type: ["in", ["Bank", "Cash"]],
		}}));
		frm.set_query("cost_center", "custom_bank_payment_allocations", () => ({filters: {
			company: frm.doc.company, is_group: 0, disabled: 0,
		}}));
	},
	refresh(frm) {
		const managed = Boolean(frm.doc.custom_multi_company_payroll_run);
		frm.toggle_display("cost_center", !managed);
		frm.toggle_display("payment_account", !managed);
		frm.toggle_display("custom_bank_allocations_section", managed);
		frm.toggle_display("custom_bank_payment_allocations", managed);
		if (!managed) return;

		make_bank_allocation_full_width(frm);
		add_payroll_flow_actions(frm);
		if (frm.doc.docstatus === 1 && !(frm.doc.custom_bank_payment_allocations || []).length && !frm.__loading_bank_allocations) {
			frm.__loading_bank_allocations = true;
			frm.call("ensure_bank_payment_allocation_defaults").then((response) => {
				if (response.message) return frm.reload_doc();
			}).finally(() => { frm.__loading_bank_allocations = false; });
		}
	},
});

frappe.ui.form.on("Payroll Bank Payment Allocation", {
	payment_account(frm) { sync_primary_payment_account(frm); },
	custom_bank_payment_allocations_remove(frm) { sync_primary_payment_account(frm); },
});


function add_payroll_flow_actions(frm) {
	frm.add_custom_button(__("Back to Payroll Run"), () => {
		frappe.set_route("Form", "Multi Company Payroll Run", frm.doc.custom_multi_company_payroll_run);
	}, __("Payroll Flow"));

	if (frm.doc.docstatus !== 1 || !frm.doc.salary_slips_submitted) return;
	frm.dashboard.set_headline_alert(
		__("Review the Bank / Cash Payment Allocations, then create the Bank Entry."),
		"blue"
	);

	frappe.call({
		method: "hrms.payroll.doctype.payroll_entry.payroll_entry.payroll_entry_has_bank_entries",
		args: {
			name: frm.doc.name,
			payroll_payable_account: frm.doc.payroll_payable_account,
		},
	}).then((response) => {
		const has_submitted_entry = Boolean(response.message?.submitted);
		const label = has_submitted_entry ? __("View Bank Entry") : __("Create Bank Entry");
		frm.add_custom_button(label, () => {
			if (has_submitted_entry) {
				open_payroll_bank_entries(frm);
				return;
			}
			create_payroll_bank_entry(frm);
		}).addClass("btn-primary");
	});
}


function suppress_standard_bank_button_for_managed_payroll(frm) {
	const standard_handler = frm.events.add_bank_entry_button;
	if (!standard_handler || standard_handler._accounting_custom_wrapped) return;

	const wrapped_handler = (form) => {
		if (form.doc.custom_multi_company_payroll_run) return;
		return standard_handler(form);
	};
	wrapped_handler._accounting_custom_wrapped = true;
	frm.events.add_bank_entry_button = wrapped_handler;
}

function create_payroll_bank_entry(frm) {
	if (frm.__loading_bank_allocations) {
		frappe.show_alert({message: __("Payment allocations are still loading. Please try again in a moment."), indicator: "blue"});
		return;
	}
	if (!(frm.doc.custom_bank_payment_allocations || []).length) {
		frappe.msgprint(__("Add at least one Bank / Cash Payment Allocation before creating the Bank Entry."));
		return;
	}

	const create_entry = () => frappe.call({
		method: "run_doc_method",
		args: {
			method: "make_bank_entry",
			dt: "Payroll Entry",
			dn: frm.doc.name,
		},
		freeze: true,
		freeze_message: __("Creating Bank Entry..."),
	}).then(() => open_payroll_bank_entries(frm));

	if (frm.is_dirty()) {
		frm.save().then(create_entry);
	} else {
		create_entry();
	}
}

function open_payroll_bank_entries(frm) {
	frappe.set_route("List", "Journal Entry", {
		"Journal Entry Account.reference_type": "Payroll Entry",
		"Journal Entry Account.reference_name": frm.doc.name,
	});
}

function make_bank_allocation_full_width(frm) {
	const field = frm.get_field("custom_bank_payment_allocations");
	field?.$wrapper.closest(".form-column").removeClass("col-sm-6").addClass("col-sm-12");
}

function sync_primary_payment_account(frm) {
	const first_account = (frm.doc.custom_bank_payment_allocations || []).find((row) => row.payment_account)?.payment_account || "";
	frm.set_value("payment_account", first_account);
}
