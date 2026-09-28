frappe.ui.form.on("Employee Advance", {
	setup(frm) {
		frm.set_query("custom_employee_profile", () => ({
			filters: { custom_is_payroll_identity: 0, status: "Active" },
		}));
		frm.set_query("company", () => ({
			filters: frm.salary_advance_companies?.length
				? { name: ["in", frm.salary_advance_companies] }
				: {},
		}));
	},
	async refresh(frm) {
		configure_simple_salary_advance_form(frm);
		if (frm.is_new() && !frm.doc.custom_salary_installment_plan) {
			await frm.set_value("custom_salary_installment_plan", 1);
		}
		if (frm.is_new() && !frm.doc.purpose) {
			await frm.set_value("purpose", __("Salary Advance"));
		}
		if (
			frm.doc.custom_employee_profile &&
			(!frm.doc.employee || !frm.doc.advance_account)
		) {
			await load_salary_advance_defaults(frm, frm.doc.company);
		}
		if (frm.doc.custom_monthly_installment && frm.doc.custom_repayment_months) {
			frm.dashboard.set_headline_alert(
				__("{0} will be deducted monthly for {1} month(s).", [
					format_currency(frm.doc.custom_monthly_installment, frm.doc.currency),
					frm.doc.custom_repayment_months,
				]),
				"blue"
			);
		}
	},
	async custom_employee_profile(frm) {
		if (!frm.doc.custom_employee_profile) return;
		await load_salary_advance_defaults(frm);
	},
	async company(frm) {
		if (frm.salary_advance_applying_defaults || !frm.doc.custom_employee_profile) return;
		if (frm.salary_advance_companies?.includes(frm.doc.company)) {
			await load_salary_advance_defaults(frm, frm.doc.company);
		}
	},
	advance_amount(frm) {
		set_default_monthly_deduction(frm);
	},
	custom_repayment_months(frm) {
		set_default_monthly_deduction(frm);
	},
	validate(frm) {
		if (!frm.doc.custom_salary_installment_plan) return;
		const total = flt(frm.doc.custom_monthly_installment) * cint(frm.doc.custom_repayment_months);
		if (Math.abs(total - flt(frm.doc.advance_amount)) > 0.01) {
			frappe.throw(__("Monthly Deduction Amount x Number of Months must equal the Amount Given."));
		}
	},
});

function configure_simple_salary_advance_form(frm) {
	const simple_fields = [
		"employee", "employee_name", "posting_date", "department", "currency_section",
		"currency", "exchange_rate", "purpose", "paid_amount", "pending_amount",
		"claimed_amount", "section_break_7", "advance_account", "mode_of_payment",
		"repay_unclaimed_amount_from_salary", "more_info_section",
		"custom_salary_installment_plan", "custom_salary_deduction_component",
	];
	simple_fields.forEach((fieldname) => frm.toggle_display(fieldname, false));
	frm.toggle_display("company", Boolean(frm.salary_advance_companies?.length > 1));
	frm.toggle_enable("company", frm.is_new());
	frm.set_df_property("advance_amount", "label", __("Amount Given"));
	frm.set_df_property("custom_monthly_installment", "label", __("Monthly Deduction Amount"));
	frm.set_df_property("custom_repayment_start_date", "label", __("Deduction Start Date"));
	frm.set_df_property("custom_monthly_installment", "read_only", 0);
}

async function load_salary_advance_defaults(frm, company = null) {
	const response = await frappe.call({
		method: "accounting_custom.accounting.salary_advance.get_salary_advance_defaults",
		args: {
			employee_profile: frm.doc.custom_employee_profile,
			company,
		},
	});
	const options = response.message || [];
	if (!options.length) {
		frappe.throw(__("This employee has no active company payroll details."));
	}
	frm.salary_advance_companies = options.map((row) => row.company);
	configure_simple_salary_advance_form(frm);
	if (options.length > 1 && !company) {
		await frm.set_value("employee", null);
		await frm.set_value("company", null);
		frappe.show_alert({
			message: __("Select the company responsible for this salary advance."),
			indicator: "blue",
		});
		return;
	}
	const selected = options[0];
	if (!selected.advance_account) {
		frappe.throw(__("Set a Default Employee Advance Account for company {0}.", [selected.company]));
	}
	if (!selected.deduction_component) {
		frappe.throw(__("Configure a salary-advance deduction component for company {0}.", [selected.company]));
	}
	frm.salary_advance_applying_defaults = true;
	try {
		await frm.set_value("employee", selected.employee);
		await frm.set_value("company", selected.company);
		await frm.set_value("advance_account", selected.advance_account);
		await frm.set_value("currency", selected.currency);
		await frm.set_value("custom_salary_deduction_component", selected.deduction_component);
	} finally {
		frm.salary_advance_applying_defaults = false;
	}
	configure_simple_salary_advance_form(frm);
}

function set_default_monthly_deduction(frm) {
	if (
		!flt(frm.doc.custom_monthly_installment) &&
		flt(frm.doc.advance_amount) > 0 &&
		cint(frm.doc.custom_repayment_months) > 0
	) {
		frm.set_value(
			"custom_monthly_installment",
			flt(frm.doc.advance_amount) / cint(frm.doc.custom_repayment_months)
		);
	}
}
