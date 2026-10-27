const PAYROLL_CATEGORIES = [
	"دعاة", "خدمات", "منتديات", "نماء", "اداريين",
	"دور القران -اداريين", "دور-الشيوخ المدرسين", "غير مصنف",
	"مسجد الفرقان", "مسجد أبي بكر الصديق", "مسجد السيدة عائشة",
];

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
		if (["Currency", "Float", "Int"].includes(column.fieldtype) && Number(value) === 0) return "";
		const formatted = default_formatter(value, row, column, data);
		return column.fieldname === "employee_name" ? `<strong>${formatted}</strong>` : formatted;
	},
};

function is_arabic() {
	return String(frappe.boot.lang || "en").toLowerCase().startsWith("ar");
}

function category_label(category) {
	return category;
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
	report.page.add_inner_button(is_arabic() ? "طباعة التبويب الحالي" : "Print Current Tab", () => print_current_tab(report));
	report.page.add_inner_button(is_arabic() ? "معاينة وطباعة كل التبويبات" : "Preview / Print All Tabs", () => preview_all_tabs(report)).addClass("btn-primary");
}

async function preview_all_tabs(report) {
	const payroll_run = report.get_filter_value("payroll_run");
	if (!payroll_run) {
		frappe.msgprint(is_arabic() ? "اختر تشغيل الرواتب أولاً." : "Select a Multi Company Payroll Run first.");
		return;
	}
	const [response, user_settings] = await Promise.all([
		fetch_arabic_registers(payroll_run),
		frappe.model.user_settings.get("Multi Company Payroll Run"),
	]);
	apply_saved_layout(response.message, saved_layout_for_run(user_settings, payroll_run));
	const dialog = new frappe.ui.Dialog({
		title: is_arabic() ? "معاينة كل كشوف الرواتب" : "Preview All Payroll Registers",
		size: "extra-large", fields: [{fieldname: "preview", fieldtype: "HTML"}],
		secondary_action_label: is_arabic() ? "حفظ التصميم" : "Save Layout",
		secondary_action: async () => {
			await save_register_layout(payroll_run, response.message);
			frappe.show_alert({message: is_arabic() ? "تم حفظ ترتيب الصفوف وعرض الأعمدة." : "Row order and column widths saved.", indicator: "green"});
		},
		primary_action_label: is_arabic() ? "طباعة الكل" : "Print All",
		primary_action: () => print_all_registers(build_all_registers_html(response.message)),
	});
	dialog.$wrapper.find(".modal-dialog").css("max-width", "96vw");
	dialog.show();
	render_reorderable_preview(dialog.fields_dict.preview.$wrapper, response.message);
}

async function print_current_tab(report) {
	const payroll_run = report.get_filter_value("payroll_run");
	if (!payroll_run) {
		frappe.msgprint(is_arabic() ? "اختر تشغيل الرواتب أولاً." : "Select a Multi Company Payroll Run first.");
		return;
	}
	const [response, user_settings] = await Promise.all([
		fetch_arabic_registers(payroll_run),
		frappe.model.user_settings.get("Multi Company Payroll Run"),
	]);
	apply_saved_layout(response.message, saved_layout_for_run(user_settings, payroll_run));
	const category = report.get_filter_value("payroll_category");
	const registers = category
		? response.message.registers.filter((register) => register.category === category)
		: response.message.registers;
	print_all_registers(build_all_registers_html({...response.message, registers}));
}

function saved_layout_for_run(user_settings, payroll_run) {
	return ((user_settings || {}).payroll_salary_register_layouts || {})[payroll_run] || {};
}

function row_layout_key(row) {
	return String(row.employee || row.employee_name || "");
}

function apply_saved_layout(payload, layout) {
	(payload.registers || []).forEach((register) => {
		const saved = layout[register.category] || {};
		const order = Array.isArray(saved) ? saved : saved.order;
		if (Array.isArray(order) && order.length) {
			const positions = new Map(order.map((key, index) => [String(key), index]));
			register.data.sort((left, right) => {
				const left_position = positions.has(row_layout_key(left)) ? positions.get(row_layout_key(left)) : Number.MAX_SAFE_INTEGER;
				const right_position = positions.has(row_layout_key(right)) ? positions.get(row_layout_key(right)) : Number.MAX_SAFE_INTEGER;
				return left_position - right_position;
			});
			register.data.forEach((row, index) => { row.row_number = String(index + 1); });
		}
		if (saved.widths) {
			register.columns.forEach((column) => {
				const width = Number(saved.widths[column.fieldname]);
				if (width > 0) {
					column.width = width;
					column.saved_print_width = width;
				}
			});
		}
	});
}

function save_register_layout(payroll_run, payload) {
	const layout = {};
	(payload.registers || []).forEach((register) => {
		const printable = printable_register(register);
		layout[register.category] = {
			order: register.data.map(row_layout_key),
			widths: Object.fromEntries(printable.columns.map((column) => [column.fieldname, Number(column.width || 100)])),
		};
	});
	return frappe.model.user_settings.save("Multi Company Payroll Run", "payroll_salary_register_layouts", {
		[payroll_run]: layout,
	});
}

function fetch_arabic_registers(payroll_run) {
	return frappe.call({
		method: "accounting_custom.accounting_custom.report.payroll_salary_register.payroll_salary_register.get_all_registers",
		args: {payroll_run}, freeze: true,
		freeze_message: is_arabic() ? "جارٍ تجهيز كشوف الرواتب..." : "Preparing Arabic payroll registers...",
	});
}

function build_all_registers_html(payload) {
	const direction = payload.direction || (is_arabic() ? "rtl" : "ltr");
	const sections = payload.registers.map((register, register_index) => {
		const printable = printable_register(register);
		const headers = printable.columns.map((column) => `<th data-fieldname="${frappe.utils.escape_html(column.fieldname)}">${frappe.utils.escape_html(column.label)}<span class="column-resizer" title="اسحب لتغيير عرض العمود"></span></th>`).join("");
		const widths = printable.columns.map((column) => `<col data-fieldname="${frappe.utils.escape_html(column.fieldname)}" style="width:${column.print_width}%">`).join("");
		const body = printable.data.length ? printable.data.map((row, row_index) => `<tr class="payroll-data-row" draggable="true" data-row-index="${row_index}">${printable.columns.map((column) => `<td class="${numeric_column(column) ? "number" : ""} ${column.fieldname === "row_number" ? "drag-handle" : ""}"${column.fieldname === "row_number" ? ' title="اسحب لتغيير الترتيب"' : ""}>${column.fieldname === "row_number" ? '<span class="drag-grip">⋮⋮</span>' : ""}${format_cell(row[column.fieldname], column)}</td>`).join("")}</tr>`).join("") : `<tr><td colspan="${printable.columns.length}" class="empty">لا يوجد موظفون في هذه الفئة</td></tr>`;
		const totals = printable.data.length ? build_total_row(printable) : "";
		return `<section class="payroll-print-section" data-register-index="${register_index}" dir="${direction}"><div class="payroll-print-category">${frappe.utils.escape_html(register.category_label)}</div>${register.title_html}<table><colgroup>${widths}</colgroup><thead><tr>${headers}</tr></thead><tbody>${body}${totals}</tbody></table><div class="payroll-signatures"><strong>المدير التنفيذي</strong><strong>الإدارة المالية</strong><strong>رئيس الجمعية</strong></div></section>`;
	}).join("");
	return `<div class="payroll-all-preview" dir="${direction}"><div class="column-resize-help"><span class="resize-help-icon">↔</span><span>مرّر المؤشر فوق الفاصل بين عناوين الأعمدة واسحبه لتعديل العرض، ثم اضغط حفظ التصميم.</span></div>${sections}</div>`;
}

function printable_register(register) {
	const columns = register.columns
		.filter((column) => !numeric_column(column) || register.data.some((row) => Number(row[column.fieldname] || 0) !== 0))
		.map((column) => ({...column}));
	const notes = columns.find((column) => column.fieldname === "notes");
	if (notes && !notes.saved_print_width) notes.width = notes_column_width(register.data);
	const total_width = columns.reduce((sum, column) => sum + Number(column.width || 100), 0) || 1;
	columns.forEach((column) => { column.print_width = (Number(column.width || 100) / total_width * 100).toFixed(4); });
	return {...register, columns};
}

function notes_column_width(rows) {
	const longest_note = rows.reduce((length, row) => Math.max(length, String(row.notes || "").trim().length), 0);
	if (!longest_note) return 110;
	if (longest_note <= 20) return 160;
	if (longest_note <= 45) return 220;
	return 280;
}

function render_reorderable_preview(wrapper, payload) {
	wrapper.html(build_all_registers_html(payload));
	let dragged = null;
	wrapper.find(".drag-handle").on("mousedown", function () {
		$(this).closest(".payroll-data-row").addClass("drag-armed");
	});
	wrapper.find(".payroll-data-row").on("dragstart", function (event) {
		if (!$(this).hasClass("drag-armed")) {
			event.preventDefault();
			return;
		}
		const section = $(this).closest(".payroll-print-section");
		dragged = {register: Number(section.data("register-index")), row: Number($(this).data("row-index"))};
		$(this).addClass("dragging");
		event.originalEvent.dataTransfer.effectAllowed = "move";
	});
	wrapper.find(".payroll-data-row").on("dragover", function (event) {
		if (!dragged) return;
		const register = Number($(this).closest(".payroll-print-section").data("register-index"));
		if (register !== dragged.register) return;
		event.preventDefault();
		wrapper.find(".payroll-data-row").removeClass("drag-target");
		$(this).addClass("drag-target");
	});
	wrapper.find(".payroll-data-row").on("drop", function (event) {
		event.preventDefault();
		const register_index = Number($(this).closest(".payroll-print-section").data("register-index"));
		const target_index = Number($(this).data("row-index"));
		if (!dragged || dragged.register !== register_index || dragged.row === target_index) return;
		const rows = payload.registers[register_index].data;
		const [moved] = rows.splice(dragged.row, 1);
		rows.splice(target_index, 0, moved);
		rows.forEach((row, index) => { row.row_number = String(index + 1); });
		dragged = null;
		render_reorderable_preview(wrapper, payload);
	});
	wrapper.find(".payroll-data-row").on("dragend", function () {
		dragged = null;
		wrapper.find(".payroll-data-row").removeClass("drag-armed dragging drag-target");
	});
	wrapper.find(".column-resizer").on("mousedown", function (event) {
		event.preventDefault();
		event.stopPropagation();
		const header = $(this).closest("th");
		const section = header.closest(".payroll-print-section");
		const register_index = Number(section.data("register-index"));
		const register = payload.registers[register_index];
		const fieldname = String(header.data("fieldname"));
		const source_column = register.columns.find((column) => column.fieldname === fieldname);
		const visible_column = printable_register(register).columns.find((column) => column.fieldname === fieldname);
		if (!source_column || !visible_column) return;
		const start_x = event.clientX;
		const start_width = Number(visible_column.width || 100);
		const table_width = Math.max(header.closest("table").width(), 1);
		const table = header.closest("table");
		const total_width = printable_register(register).columns.reduce((sum, column) => sum + Number(column.width || 100), 0);
		const rtl_multiplier = section.attr("dir") === "rtl" ? -1 : 1;
		const resizer = $(this).addClass("active");
		section.addClass("column-resize-active");
		$(document).off("mousemove.payroll-column mouseup.payroll-column");
		$(document).on("mousemove.payroll-column", (move_event) => {
			const model_delta = (move_event.clientX - start_x) * rtl_multiplier * total_width / table_width;
			const width = Math.max(45, Math.round(start_width + model_delta));
			source_column.width = width;
			source_column.saved_print_width = width;
			printable_register(register).columns.forEach((column) => {
				table.find(`col[data-fieldname="${column.fieldname}"]`).css("width", `${column.print_width}%`);
			});
		});
		$(document).one("mouseup.payroll-column", () => {
			$(document).off("mousemove.payroll-column mouseup.payroll-column");
			resizer.removeClass("active");
			section.removeClass("column-resize-active");
			render_reorderable_preview(wrapper, payload);
		});
	});
	$(document).off("mouseup.payroll-register").on("mouseup.payroll-register", () => wrapper.find(".payroll-data-row").removeClass("drag-armed"));
}

function numeric_column(column) {
	return ["Currency", "Float", "Int"].includes(column.fieldtype) && column.fieldname !== "row_number";
}

function format_cell(value, column) {
	if (value === null || value === undefined || value === "") return "";
	if (numeric_column(column) && Number(value) === 0) return "";
	if (numeric_column(column)) return frappe.utils.escape_html(format_number(Number(value), null, column.precision ?? 0));
	return frappe.utils.escape_html(String(value));
}

function build_total_row(register) {
	const cells = register.columns.map((column) => {
		if (numeric_column(column)) {
			const total = register.data.reduce((sum, row) => sum + Number(row[column.fieldname] || 0), 0);
			return `<td class="number total-value">${frappe.utils.escape_html(format_number(total, null, column.precision ?? 0))}</td>`;
		}
		if (column.fieldname === "employee_name") {
			return `<td class="total-label">المجموع</td>`;
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
	print_window.document.write(`<!doctype html><html><head><meta charset="utf-8"><title>كشف الرواتب</title><style>${print_styles()}</style></head><body>${content}</body></html>`);
	print_window.document.close();
	print_window.focus();
	setTimeout(() => print_window.print(), 300);
}

function print_styles() {
	return `@page { size: A4 landscape; margin: 8mm; } * { box-sizing: border-box; } body { margin: 0; color: #111; font-family: Arial, "Noto Naskh Arabic", sans-serif; } .payroll-print-section { page-break-after: always; padding: 4mm; min-height: 185mm; } .payroll-print-section:last-child { page-break-after: auto; } .payroll-print-category { display: inline-block; border: 1px solid #222; padding: 5px 16px; margin-bottom: 10px; font-size: 15px; font-weight: 700; border-radius: 12px; } .payroll-print-section > div[style] { margin: 3mm 0 6mm; } table { width: 100%; border-collapse: collapse; table-layout: fixed; font-size: 13px; } th, td { border: 1px solid #222; padding: 8px 5px; text-align: center; vertical-align: middle; overflow-wrap: anywhere; } th { background: #f1f3f5; font-size: 13px; font-weight: 700; } td.number { direction: ltr; font-variant-numeric: tabular-nums; } .drag-grip, .column-resizer, .column-resize-help { display: none; } .total-row td { border-top: 2px solid #111; font-weight: 700; background: #f8f9fa; } .empty { padding: 24px; color: #777; } .payroll-signatures { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; text-align: center; font-size: 14px; margin-top: 9mm; padding-top: 5mm; border-top: 1px solid #555; }`;
}

function add_report_styles() {
	if (document.getElementById("payroll-register-styles")) return;
	$("<style id='payroll-register-styles'>").text(`.payroll-register-nav { margin: 12px 0 18px; padding: 16px; background: var(--card-bg); border: 1px solid var(--border-color); border-radius: 12px; box-shadow: var(--shadow-sm); } .payroll-register-nav-title { display: flex; gap: 10px; align-items: center; margin-bottom: 12px; } .payroll-register-nav-title small { display: block; color: var(--text-muted); margin-top: 2px; } .payroll-register-icon { display: grid; place-items: center; width: 36px; height: 36px; border-radius: 9px; color: #fff; background: #22c55e; font-size: 20px; } .payroll-category-tabs { display: flex; gap: 7px; overflow-x: auto; padding: 2px 0 5px; scrollbar-width: thin; } .payroll-tab { flex: 0 0 auto; border: 1px solid var(--border-color); color: var(--text-color); background: var(--control-bg); border-radius: 999px; padding: 7px 13px; font-size: 12px; transition: .15s ease; } .payroll-tab:hover { border-color: #22c55e; color: #16803d; } .payroll-tab.active { color: #fff; background: #22c55e; border-color: #22c55e; box-shadow: 0 3px 9px rgba(34,197,94,.22); } .payroll-all-preview { max-height: 72vh; overflow: auto; padding: 12px; background: #eef1f4; } .payroll-all-preview .column-resize-help { position: sticky; top: 0; z-index: 8; display: flex; align-items: center; justify-content: center; gap: 8px; width: fit-content; max-width: 90%; margin: 0 auto 12px; padding: 8px 14px; color: #166534; background: #f0fdf4; border: 1px solid #bbf7d0; border-radius: 999px; box-shadow: 0 2px 8px rgba(22,101,52,.1); font-size: 12px; font-weight: 600; } .payroll-all-preview .resize-help-icon { display: inline-grid; place-items: center; width: 24px; height: 24px; color: #fff; background: #22c55e; border-radius: 50%; font-size: 16px; } .payroll-all-preview .payroll-print-section { background: #fff; margin: 0 auto 18px; padding: 20px; box-shadow: 0 2px 12px rgba(0,0,0,.08); } .payroll-all-preview table { width: 100%; border-collapse: collapse; table-layout: fixed; font-size: 11px; } .payroll-all-preview th, .payroll-all-preview td { border: 1px solid #777; padding: 6px 4px; text-align: center; overflow-wrap: anywhere; } .payroll-all-preview th { position: relative; background: #f1f3f5; } .payroll-all-preview .column-resizer { position: absolute; inset-inline-end: -6px; top: 0; bottom: 0; width: 12px; z-index: 3; cursor: col-resize; touch-action: none; } .payroll-all-preview .column-resizer::before { content: ""; position: absolute; inset-inline-start: 5px; top: 5px; bottom: 5px; width: 2px; border-radius: 2px; background: transparent; transition: background .15s, box-shadow .15s; } .payroll-all-preview .column-resizer::after { content: "•••"; position: absolute; inset-inline-start: 0; top: 50%; width: 12px; color: transparent; font-size: 8px; letter-spacing: -1px; line-height: 12px; text-align: center; transform: translateY(-50%) rotate(90deg); transition: color .15s, background .15s; } .payroll-all-preview .column-resizer:hover::before, .payroll-all-preview .column-resizer.active::before { background: #22c55e; box-shadow: 0 0 0 2px rgba(34,197,94,.15); } .payroll-all-preview .column-resizer:hover::after, .payroll-all-preview .column-resizer.active::after { color: #fff; background: #16a34a; border-radius: 6px; } .payroll-all-preview .column-resize-active { user-select: none; cursor: col-resize; } .payroll-all-preview .number { direction: ltr; font-variant-numeric: tabular-nums; } .payroll-all-preview .drag-handle { position: relative; cursor: grab; user-select: none; white-space: nowrap; padding-inline-start: 14px; } .payroll-all-preview .drag-handle:active { cursor: grabbing; } .payroll-all-preview .drag-grip { position: absolute; inset-inline-start: 2px; top: 50%; transform: translateY(-50%); color: #8b95a1; font-weight: 700; font-size: 9px; } .payroll-all-preview .payroll-data-row.dragging { opacity: .35; } .payroll-all-preview .payroll-data-row.drag-target td { border-top: 3px solid #22c55e; } .payroll-all-preview .total-row { font-weight: 700; background: #f8f9fa; } .payroll-all-preview .total-label { white-space: nowrap; } .payroll-all-preview .payroll-signatures { display: grid; grid-template-columns: repeat(3, 1fr); text-align: center; margin-top: 20px; padding-top: 14px; border-top: 1px solid #555; } @media print { .payroll-register-nav, .page-form, .page-head { display: none !important; } }`).appendTo(document.head);
}
