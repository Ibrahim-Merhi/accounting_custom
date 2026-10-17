const PAYROLL_CATEGORIES = [
	"دعاة", "خدمات", "منتديات", "نماء", "اداريين",
	"دور القران -اداريين", "دور-الشيوخ المدرسين", "غير مصنف",
	"مسجد الفرقان", "مسجد أبي بكر الصديق", "مسجد السيدة عائشة",
];

frappe.query_reports["Payroll Salary Register"] = {
	filters: [
		{
			fieldname: "payroll_run",
			label: __("Multi Company Payroll Run"),
			fieldtype: "Link",
			options: "Multi Company Payroll Run",
			reqd: 1,
		},
		{
			fieldname: "payroll_category",
			label: __("فئة كشف الرواتب"),
			fieldtype: "Select",
			options: ["", ...PAYROLL_CATEGORIES].join("\n"),
		},
	],
	onload(report) {
		report.page.set_title(__("كشف الرواتب"));
		add_category_tabs(report);
	},
	formatter(value, row, column, data, default_formatter) {
		const formatted = default_formatter(value, row, column, data);
		if (column.fieldname === "employee_name") return `<strong>${formatted}</strong>`;
		return formatted;
	},
};

function add_category_tabs(report) {
	if (report.__payroll_category_tabs) return;
	report.__payroll_category_tabs = true;
	const wrapper = $(`<div class="payroll-category-tabs mb-3" dir="rtl"></div>`).prependTo(report.page.main);
	const categories = ["الكل", ...PAYROLL_CATEGORIES];
	categories.forEach((category) => {
		const button = $(`<button class="btn btn-sm btn-default ml-1 mb-1">${frappe.utils.escape_html(category)}</button>`)
			.appendTo(wrapper);
		button.on("click", () => {
				report.set_filter_value("payroll_category", category === "الكل" ? "" : category);
				report.refresh();
				wrapper.find("button").removeClass("btn-primary").addClass("btn-default");
				button.removeClass("btn-default").addClass("btn-primary");
			});
	});
	wrapper.find("button:first").removeClass("btn-default").addClass("btn-primary");
	$("<style>")
		.text(`
			.payroll-category-tabs { padding: 10px 15px 4px; border-bottom: 1px solid var(--border-color); }
			.payroll-category-tabs .btn-primary { background: #22c55e; border-color: #22c55e; }
			@media print {
				.payroll-category-tabs, .page-form, .page-head { display: none !important; }
				.print-format { direction: rtl; font-family: Arial, "Noto Naskh Arabic", sans-serif; }
				table { font-size: 9px; }
			}
			@page { size: A4 landscape; margin: 8mm; }
		`)
		.appendTo(document.head);
}
