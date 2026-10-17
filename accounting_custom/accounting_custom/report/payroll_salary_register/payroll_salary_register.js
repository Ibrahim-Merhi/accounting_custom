const PAYROLL_CATEGORIES = [
	"دعاة", "خدمات", "منتديات", "نماء", "اداريين",
	"دور القران -اداريين", "دور-الشيوخ المدرسين", "غير مصنف",
	"مسجد الفرقان", "مسجد أبي بكر الصديق", "مسجد السيدة عائشة",
];

const CATEGORY_LABELS_EN = {
	"دعاة": "Preachers", "خدمات": "Services", "منتديات": "Forums", "نماء": "Namaa",
	"اداريين": "Administrators", "دور القران -اداريين": "Quran Centers - Administrators",
	"دور-الشيوخ المدرسين": "Quran Centers - Teachers", "غير مصنف": "Uncategorized",
	"مسجد الفرقان": "Al Furqan Mosque", "مسجد أبي بكر الصديق": "Abu Bakr Al-Siddiq Mosque",
	"مسجد السيدة عائشة": "Aisha Mosque",
};

frappe.query_reports["Payroll Salary Register"] = {
	filters: [
		{fieldname: "payroll_run", label: __("Multi Company Payroll Run"), fieldtype: "Link", options: "Multi Company Payroll Run", reqd: 1},
		{fieldname: "payroll_category", label: __("Payroll Category"), fieldtype: "Select", options: ["", ...PAYROLL_CATEGORIES].join("\n"), hidden: 1},
	],
	onload(report) {
		report.page.set_title(is_arabic() ? "كشف الرواتب" : "Payroll Salary Register");
		add_category_tabs(report);
		add_print_actions(report);
		add_report_styles();
	},
	formatter(value, row, column, data, default_formatter) {
		const formatted = default_formatter(value, row, column, data);
		return column.fieldname === "employee_name" ? `<strong>${formatted}</strong>` : formatted;
	},
};

function is_arabic() {
	return String(frappe.boot.lang || "en").toLowerCase().startsWith("ar");
}

function category_label(category) {
	return is_arabic() ? category : (CATEGORY_LABELS_EN[category] || category);
}

function add_category_tabs(report) {
	if (report.__payroll_category_tabs) return;
	report.__payroll_category_tabs = true;
	const direction = is_arabic() ? "rtl" : "ltr";
	const wrapper = $(`<div class="payroll-register-nav" dir="${direction}"><div class="payroll-register-nav-title"><span class="payroll-register-icon">▦</span><div><strong>${is_arabic() ? "فئات كشف الرواتب" : "Payroll Categories"}</strong><small>${is_arabic() ? "اختر فئة لعرضها وطباعتها" : "Choose a category to view and print"}</small></div></div><div class="payroll-category-tabs"></div></div>`).prependTo(report.page.main);
	const tabs = wrapper.find(".payroll-category-tabs");
	const categories = [{value: "", label: is_arabic() ? "الكل" : "All"}, ...PAYROLL_CATEGORIES.map((value) => ({value, label: category_label(value)}))];
	categories.forEach(({value, label}) => {
		const button = $(`<button class="payroll-tab" type="button">${frappe.utils.escape_html(label)}</button>`).appendTo(tabs);
		button.on("click", async () => {
			await report.set_filter_value("payroll_category", value);
			tabs.find(".payroll-tab").removeClass("active");
			button.addClass("active");
			report.refresh();
		});
	});
	tabs.find(".payroll-tab:first").addClass("active");
}

function add_print_actions(report) {
	if (report.__payroll_print_actions) return;
	report.__payroll_print_actions = true;
	report.page.add_inner_button(is_arabic() ? "طباعة التبويب الحالي" : "Print Current Tab", () => report.print_report({orientation: "Landscape"}));
	report.page.add_inner_button(is_arabic() ? "معاينة وطباعة كل التبويبات" : "Preview / Print All Tabs", () => preview_all_tabs(report)).addClass("btn-primary");
}

async function preview_all_tabs(report) {
	const payroll_run = report.get_filter_value("payroll_run");
	if (!payroll_run) {
		frappe.msgprint(is_arabic() ? "اختر تشغيل الرواتب أولاً." : "Select a Multi Company Payroll Run first.");
		return;
	}
	const response = await frappe.call({
		method: "accounting_custom.accounting_custom.report.payroll_salary_register.payroll_salary_register.get_all_registers",
		args: {payroll_run}, freeze: true,
		freeze_message: is_arabic() ? "جارٍ تجهيز كل كشوف الرواتب..." : "Preparing all payroll registers...",
	});
	const content = build_all_registers_html(response.message);
	const dialog = new frappe.ui.Dialog({
		title: is_arabic() ? "معاينة كل كشوف الرواتب" : "Preview All Payroll Registers",
		size: "extra-large", fields: [{fieldname: "preview", fieldtype: "HTML"}],
		primary_action_label: is_arabic() ? "طباعة الكل" : "Print All",
		primary_action: () => print_all_registers(content),
	});
	dialog.fields_dict.preview.$wrapper.html(content);
	dialog.$wrapper.find(".modal-dialog").css("max-width", "96vw");
	dialog.show();
}

function build_all_registers_html(payload) {
	const direction = payload.direction || (is_arabic() ? "rtl" : "ltr");
	const sections = payload.registers.map((register) => {
		const headers = register.columns.map((column) => `<th>${frappe.utils.escape_html(column.label)}</th>`).join("");
		const body = register.data.length ? register.data.map((row) => `<tr>${register.columns.map((column) => `<td class="${numeric_column(column) ? "number" : ""}">${format_cell(row[column.fieldname], column)}</td>`).join("")}</tr>`).join("") : `<tr><td colspan="${register.columns.length}" class="empty">${is_arabic() ? "لا يوجد موظفون في هذه الفئة" : "No employees in this category"}</td></tr>`;
		const totals = register.data.length ? build_total_row(register) : "";
		return `<section class="payroll-print-section" dir="${direction}"><div class="payroll-print-category">${frappe.utils.escape_html(register.category_label)}</div>${register.title_html}<table><thead><tr>${headers}</tr></thead><tbody>${body}${totals}</tbody></table><div class="payroll-signatures"><strong>${is_arabic() ? "المدير التنفيذي" : "Executive Director"}</strong><strong>${is_arabic() ? "الإدارة المالية" : "Finance Department"}</strong><strong>${is_arabic() ? "رئيس الجمعية" : "Association President"}</strong></div></section>`;
	}).join("");
	return `<div class="payroll-all-preview" dir="${direction}">${sections}</div>`;
}

function numeric_column(column) {
	return ["Currency", "Float", "Int"].includes(column.fieldtype) && column.fieldname !== "row_number";
}

function format_cell(value, column) {
	if (value === null || value === undefined || value === "") return "";
	if (numeric_column(column)) return frappe.utils.escape_html(format_number(Number(value), null, column.precision ?? 0));
	return frappe.utils.escape_html(String(value));
}

function build_total_row(register) {
	let label_written = false;
	const cells = register.columns.map((column) => {
		if (numeric_column(column)) {
			const total = register.data.reduce((sum, row) => sum + Number(row[column.fieldname] || 0), 0);
			return `<td class="number total-value">${frappe.utils.escape_html(format_number(total, null, column.precision ?? 0))}</td>`;
		}
		if (!label_written) {
			label_written = true;
			return `<td class="total-label">${is_arabic() ? "المجموع" : "Total"}</td>`;
		}
		return "<td></td>";
	}).join("");
	return `<tr class="total-row">${cells}</tr>`;
}

function print_all_registers(content) {
	const print_window = window.open("", "_blank");
	if (!print_window) {
		frappe.msgprint(is_arabic() ? "اسمح بالنوافذ المنبثقة لطباعة التقرير." : "Allow pop-ups to print the report.");
		return;
	}
	print_window.document.write(`<!doctype html><html><head><meta charset="utf-8"><title>${is_arabic() ? "كشف الرواتب" : "Payroll Salary Register"}</title><style>${print_styles()}</style></head><body>${content}</body></html>`);
	print_window.document.close();
	print_window.focus();
	setTimeout(() => print_window.print(), 300);
}

function print_styles() {
	return `@page { size: A4 landscape; margin: 8mm; } * { box-sizing: border-box; } body { margin: 0; color: #111; font-family: Arial, "Noto Naskh Arabic", sans-serif; } .payroll-print-section { page-break-after: always; padding: 4mm; min-height: 185mm; } .payroll-print-section:last-child { page-break-after: auto; } .payroll-print-category { display: inline-block; border: 1px solid #222; padding: 4px 14px; margin-bottom: 8px; font-weight: 700; border-radius: 12px; } .payroll-print-section > div[style] { margin: 3mm 0 6mm; } table { width: 100%; border-collapse: collapse; table-layout: auto; font-size: 10px; } th, td { border: 1px solid #222; padding: 6px 4px; text-align: center; vertical-align: middle; overflow-wrap: anywhere; } th { background: #f1f3f5; font-weight: 700; } td.number { direction: ltr; font-variant-numeric: tabular-nums; } .total-row td { border-top: 2px solid #111; font-weight: 700; background: #f8f9fa; } .empty { padding: 24px; color: #777; } .payroll-signatures { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; text-align: center; margin-top: 9mm; padding-top: 5mm; border-top: 1px solid #555; }`;
}

function add_report_styles() {
	if (document.getElementById("payroll-register-styles")) return;
	$("<style id='payroll-register-styles'>").text(`.payroll-register-nav { margin: 12px 0 18px; padding: 16px; background: var(--card-bg); border: 1px solid var(--border-color); border-radius: 12px; box-shadow: var(--shadow-sm); } .payroll-register-nav-title { display: flex; gap: 10px; align-items: center; margin-bottom: 12px; } .payroll-register-nav-title small { display: block; color: var(--text-muted); margin-top: 2px; } .payroll-register-icon { display: grid; place-items: center; width: 36px; height: 36px; border-radius: 9px; color: #fff; background: #22c55e; font-size: 20px; } .payroll-category-tabs { display: flex; gap: 7px; overflow-x: auto; padding: 2px 0 5px; scrollbar-width: thin; } .payroll-tab { flex: 0 0 auto; border: 1px solid var(--border-color); color: var(--text-color); background: var(--control-bg); border-radius: 999px; padding: 7px 13px; font-size: 12px; transition: .15s ease; } .payroll-tab:hover { border-color: #22c55e; color: #16803d; } .payroll-tab.active { color: #fff; background: #22c55e; border-color: #22c55e; box-shadow: 0 3px 9px rgba(34,197,94,.22); } .payroll-all-preview { max-height: 72vh; overflow: auto; padding: 12px; background: #eef1f4; } .payroll-all-preview .payroll-print-section { background: #fff; margin: 0 auto 18px; padding: 20px; box-shadow: 0 2px 12px rgba(0,0,0,.08); } .payroll-all-preview table { width: 100%; border-collapse: collapse; font-size: 11px; } .payroll-all-preview th, .payroll-all-preview td { border: 1px solid #777; padding: 6px 4px; text-align: center; } .payroll-all-preview th { background: #f1f3f5; } .payroll-all-preview .number { direction: ltr; font-variant-numeric: tabular-nums; } .payroll-all-preview .total-row { font-weight: 700; background: #f8f9fa; } .payroll-all-preview .payroll-signatures { display: grid; grid-template-columns: repeat(3, 1fr); text-align: center; margin-top: 20px; padding-top: 14px; border-top: 1px solid #555; } @media print { .payroll-register-nav, .page-form, .page-head { display: none !important; } }`).appendTo(document.head);
}
