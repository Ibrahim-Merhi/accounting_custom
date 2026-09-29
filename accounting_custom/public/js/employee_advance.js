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
		frm.set_query("custom_advance_cost_center", () => ({
			filters: {company: frm.doc.company, is_group: 0, disabled: 0},
		}));
	},
	async refresh(frm) {
		if (frm.doc.__onload) frm.doc.__onload.make_payment_via_journal_entry = 1;
		configure_simple_salary_advance_form(frm);
		configure_salary_advance_actions(frm);
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
			const headline = __("{0} will be deducted monthly for {1} month(s).", [
				format_currency(frm.doc.custom_monthly_installment, frm.doc.currency),
				frm.doc.custom_repayment_months,
			]);
			if (frm.salary_advance_headline !== headline) {
				frm.salary_advance_headline = headline;
				frm.dashboard.set_headline_alert(headline, "blue");
			}
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

function configure_salary_advance_actions(frm) {
	frm.remove_custom_button(__("Payment"), __("Create"));
	if (frm.doc.docstatus !== 1) return;
	if (flt(frm.doc.paid_amount) < flt(frm.doc.advance_amount)) {
		frm.add_custom_button(__("Pay Advance"), () => frm.events.make_payment_entry(frm))
			.addClass("btn-primary");
		return;
	}
	frappe.db.get_list("Journal Entry Account", {
		filters: {
			reference_type: "Employee Advance",
			reference_name: frm.doc.name,
			docstatus: ["<", 2],
		},
		fields: ["parent"],
		order_by: "creation desc",
		limit: 1,
	}).then((rows) => {
		if (!rows[0]?.parent) return;
		frm.add_custom_button(__("Open Payment Entry"), () => {
			frappe.set_route("Form", "Journal Entry", rows[0].parent);
		}).addClass("btn-primary");
	});
}

function configure_simple_salary_advance_form(frm) {
	const simple_fields = [
		"employee", "employee_name", "posting_date", "department", "currency_section",
		"currency", "exchange_rate", "purpose", "paid_amount", "pending_amount",
		"claimed_amount",
		"repay_unclaimed_amount_from_salary", "more_info_section",
		"custom_salary_installment_plan", "custom_salary_deduction_component",
	];
	simple_fields.forEach((fieldname) => frm.toggle_display(fieldname, false));
	frm.toggle_display("company", true);
	frm.toggle_enable(
		"company",
		frm.is_new() && Boolean(frm.salary_advance_companies?.length > 1)
	);
	[
		"section_break_7",
		"advance_account",
		"custom_advance_cost_center",
		"mode_of_payment",
	].forEach((fieldname) => frm.toggle_display(fieldname, true));
	frm.set_df_property("section_break_8", "label", __("Advance Details"));
	frm.set_df_property("custom_salary_installment_section", "label", __("Repayment Plan"));
	frm.set_df_property("section_break_7", "label", __("Payment & Accounting"));
	frm.set_df_property("advance_amount", "label", __("Amount Given"));
	frm.set_df_property("advance_account", "description", __("Account used to track the amount owed by the employee."));
	frm.set_df_property("custom_advance_cost_center", "description", __("Cost center used for the advance payment and payroll recovery."));
	frm.set_df_property("mode_of_payment", "description", __("Select how the advance will be paid to the employee."));
	frm.set_df_property("custom_monthly_installment", "label", __("Monthly Deduction Amount"));
	frm.set_df_property("custom_repayment_start_date", "label", __("Deduction Start Date"));
	frm.set_df_property("custom_monthly_installment", "read_only", 0);
	frm.set_df_property("advance_account", "reqd", 1);
	frm.set_df_property("custom_advance_cost_center", "reqd", 1);
	frm.set_df_property("mode_of_payment", "reqd", 1);
}

function load_salary_advance_defaults(frm, company = null) {
	const key = `${frm.doc.custom_employee_profile || ""}:${company || ""}`;
	if (frm.salary_advance_defaults_request?.key === key) {
		return frm.salary_advance_defaults_request.promise;
	}
	const request = {
		key,
		promise: apply_salary_advance_defaults(frm, company),
	};
	frm.salary_advance_defaults_request = request;
	return request.promise.finally(() => {
		if (frm.salary_advance_defaults_request === request) {
			frm.salary_advance_defaults_request = null;
		}
	});
}

async function apply_salary_advance_defaults(frm, company = null) {
	const options = await get_salary_advance_options(
		frm.doc.custom_employee_profile,
		company
	);
	if (!options.length) {
		frappe.throw(__("This employee has no active company payroll details."));
	}
	frm.salary_advance_companies = options.map((row) => row.company);
	configure_simple_salary_advance_form(frm);
	if (options.length > 1 && !company) {
		await frm.set_value("employee", null);
		await frm.set_value("company", null);
		if (frm.salary_advance_company_prompted_for !== frm.doc.custom_employee_profile) {
			frm.salary_advance_company_prompted_for = frm.doc.custom_employee_profile;
			frappe.show_alert({
				message: __("Select the company responsible for this salary advance."),
				indicator: "blue",
			});
		}
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
		if (!frm.doc.custom_advance_cost_center && selected.cost_center) {
			await frm.set_value("custom_advance_cost_center", selected.cost_center);
		}
		await frm.set_value("currency", selected.currency);
		await frm.set_value("custom_salary_deduction_component", selected.deduction_component);
	} finally {
		frm.salary_advance_applying_defaults = false;
	}
	configure_simple_salary_advance_form(frm);
}

async function get_salary_advance_options(employee_profile, selected_company = null) {
	const [employee, payroll_identities] = await Promise.all([
		frappe.db.get_doc("Employee", employee_profile),
		frappe.db.get_list("Employee", {
			filters: {
				custom_master_employee: employee_profile,
				custom_is_payroll_identity: 1,
				status: "Active",
			},
			fields: ["name", "company"],
			limit: 0,
		}),
	]);
	const identity_by_company = Object.fromEntries(
		payroll_identities.filter((row) => row.company).map((row) => [row.company, row.name])
	);
	let companies = [...new Set(payroll_identities.map((row) => row.company).filter(Boolean))];
	if (!companies.length) {
		companies = [...new Set(
			(employee.custom_branches || [])
				.filter((row) => !row.left_position && row.company)
				.map((row) => row.company)
		)];
	}
	if (!companies.length && employee.company) companies = [employee.company];
	if (selected_company) {
		companies = companies.filter((company) => company === selected_company);
	}

	const deduction_components = await frappe.db.get_list("Salary Component", {
		filters: { type: "Deduction", disabled: 0 },
		fields: ["name"],
		limit: 0,
	});
	const component_documents = await Promise.all(
		deduction_components.map((row) => frappe.db.get_doc("Salary Component", row.name))
	);

	return Promise.all(companies.map(async (company) => {
		const company_values = await frappe.db.get_value("Company", company, [
			"default_employee_advance_account",
			"default_currency",
			"cost_center",
		]);
		const message = company_values.message || {};
		const deduction_component = component_documents.find((component) =>
			(component.accounts || []).some((row) =>
				row.company === company &&
				row.account === message.default_employee_advance_account
			)
		)?.name;
		return {
			employee: identity_by_company[company] || employee_profile,
			company,
			advance_account: message.default_employee_advance_account,
			currency: message.default_currency,
			cost_center: message.cost_center,
			deduction_component,
		};
	}));
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
