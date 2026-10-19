frappe.query_reports["Liquidity Position Report"] = {
	filters: [
		{
			fieldname: "companies",
			label: __("Companies"),
			fieldtype: "MultiSelectList",
			get_data: (txt) => frappe.db.get_link_options("Company", txt),
		},
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
			reqd: 1,
			default: frappe.datetime.month_start(),
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
			reqd: 1,
			default: frappe.datetime.get_today(),
		},
		{
			fieldname: "report_page",
			label: __("Report Page"),
			fieldtype: "Select",
			options: [
				{ value: "liquidity", label: __("Liquidity Report") },
				{ value: "movement", label: __("Liquidity Movement") },
				{ value: "summary", label: __("Group Summary") },
			],
			default: "liquidity",
			reqd: 1,
		},
		{
			fieldname: "groups_only",
			label: __("Groups Only"),
			fieldtype: "Check",
			default: 0,
		},
	],
	tree: true,
	name_field: "cost_center",
	parent_field: "parent_cost_center",
	initial_depth: 1,
	formatter(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		if (!data) return value;
		if (data.is_group) value = `<strong>${value}</strong>`;
		if (["available_liquidity", "ending_liquidity", "balance_liquidity"].includes(column.fieldname)) {
			value = `<span style="color:${flt(data[column.fieldname]) < 0 ? "#c62828" : "#16825d"};font-weight:600">${value}</span>`;
		}
		if (["check", "difference"].includes(column.fieldname) && Math.abs(flt(data[column.fieldname])) >= 2) {
			value = `<span style="color:#c62828;font-weight:700">${value}</span>`;
		}
		return value;
	},
	onload(report) {
		report.page.add_inner_button(__("Configure Accounts"), () => {
			frappe.set_route("List", "Account", { custom_liquidity_report_classification: ["is", "not set"] });
		});
		add_liquidity_print_actions(report);
	},
};

function add_liquidity_print_actions(report) {
	if (report.__liquidity_print_actions) return;
	report.__liquidity_print_actions = true;
	const group = __("Print");
	report.page.add_inner_button("تقرير السيولة", () => open_liquidity_print_preview(report, "liquidity"), group);
	report.page.add_inner_button("حركة السيولة", () => open_liquidity_print_preview(report, "movement"), group);
}

async function open_liquidity_print_preview(report, report_page) {
	const filters = report.get_values();
	if (!filters.from_date || !filters.to_date) {
		frappe.msgprint(__("From Date and To Date are required."));
		return;
	}
	const response = await frappe.call({
		method: "accounting_custom.accounting_custom.report.liquidity_position_report.liquidity_position_report.get_print_data",
		args: {filters, report_page}, freeze: true, freeze_message: __("Preparing print preview..."),
	});
	const payload = response.message;
	const state = {
		columns: new Set(payload.columns.map((column) => column.fieldname)),
		rows: new Set(payload.rows.map((_row, index) => index)),
	};
	const dialog = new frappe.ui.Dialog({
		title: report_page === "liquidity" ? "معاينة تقرير السيولة" : "معاينة حركة السيولة",
		size: "extra-large",
		fields: [{fieldname: "designer", fieldtype: "HTML"}],
		primary_action_label: "طباعة",
		primary_action: () => print_liquidity_preview(payload, state),
	});
	dialog.show();
	dialog.$wrapper.find(".modal-dialog").css("max-width", "98vw");
	const wrapper = dialog.fields_dict.designer.$wrapper;
	build_liquidity_designer(wrapper, payload, state);
}

function build_liquidity_designer(wrapper, payload, state) {
	const controls = `
		<div class="liquidity-print-controls" dir="rtl">
			<section><div class="control-title">الأعمدة <button data-action="all-columns">الكل</button></div>
				<div class="column-options">${payload.columns.map((column) => `<label><input type="checkbox" data-column="${frappe.utils.escape_html(column.fieldname)}" checked ${column.fieldname === "cost_center" ? "disabled" : ""}> ${frappe.utils.escape_html(column.label)}</label>`).join("")}</div></section>
			<section><div class="control-title">الصفوف <button data-action="all-rows">الكل</button></div>
				<div class="row-options">${payload.rows.map((row, index) => `<label style="padding-right:${Math.min(Number(row.indent || 0), 5) * 12}px"><input type="checkbox" data-row="${index}" checked> ${frappe.utils.escape_html(row.cost_center)}</label>`).join("")}</div></section>
			<p class="text-muted">التعديلات للطباعة فقط، ولن تغيّر السجلات في النظام.</p>
		</div><div class="liquidity-print-canvas"></div>`;
	wrapper.html(`<div class="liquidity-print-designer">${controls}</div>`);
	const render = () => wrapper.find(".liquidity-print-canvas").html(build_liquidity_print_html(payload, state, true));
	wrapper.on("change", "input[data-column]", function () {
		this.checked ? state.columns.add(this.dataset.column) : state.columns.delete(this.dataset.column); render();
	});
	wrapper.on("change", "input[data-row]", function () {
		const index = Number(this.dataset.row);
		this.checked ? state.rows.add(index) : state.rows.delete(index); render();
	});
	wrapper.on("click", "button[data-action='all-columns']", () => {
		payload.columns.forEach((column) => state.columns.add(column.fieldname));
		wrapper.find("input[data-column]").prop("checked", true); render();
	});
	wrapper.on("click", "button[data-action='all-rows']", () => {
		payload.rows.forEach((_row, index) => state.rows.add(index));
		wrapper.find("input[data-row]").prop("checked", true); render();
	});
	add_liquidity_print_styles();
	render();
}

function selected_print_rows(payload, state) {
	const rows = payload.rows.map((row, index) => ({...row, __index: index}));
	const terminal = rows.map((row, index) => index === rows.length - 1 || Number(rows[index + 1].indent || 0) <= Number(row.indent || 0));
	let sequence = 0;
	return rows.filter((row) => state.rows.has(row.__index)).map((row) => {
		const result = {...row};
		if (terminal[row.__index]) {
			result.__number = ++sequence;
			return result;
		}
		const descendants = rows.filter((candidate) =>
			candidate.__index > row.__index && Number(candidate.indent || 0) > Number(row.indent || 0)
			&& terminal[candidate.__index] && state.rows.has(candidate.__index)
		);
		payload.columns.filter(is_print_numeric).forEach((column) => {
			result[column.fieldname] = descendants.reduce((sum, item) => sum + Number(item[column.fieldname] || 0), 0);
		});
		result.__number = "";
		return result;
	});
}

function build_liquidity_print_html(payload, state, preview = false) {
	const columns = payload.columns.filter((column) => state.columns.has(column.fieldname));
	const rows = selected_print_rows(payload, state);
	const terminalRows = rows.filter((row) => row.__number !== "");
	const headers = `<th>#</th>${columns.map((column) => `<th>${frappe.utils.escape_html(column.label)}</th>`).join("")}`;
	const body = rows.map((row) => `<tr class="${row.is_group ? "group-row" : ""}"><td>${row.__number}</td>${columns.map((column) => `<td class="${is_print_numeric(column) ? "number" : ""}">${print_cell(row[column.fieldname], column)}</td>`).join("")}</tr>`).join("");
	const totals = `<tr class="grand-total"><td></td>${columns.map((column, index) => {
		if (is_print_numeric(column)) return `<td class="number">${print_number(terminalRows.reduce((sum, row) => sum + Number(row[column.fieldname] || 0), 0))}</td>`;
		return `<td>${index === 0 ? "المجموع" : ""}</td>`;
	}).join("")}</tr>`;
	const cards = payload.report_page === "liquidity" ? build_liquidity_print_cards(rows) : "";
	return `<article class="liquidity-sheet ${preview ? "preview" : ""}" dir="rtl"><header><div class="brand-bar"><div class="brand-mark">إ</div><div><h2>جمعية الإتحاد الإسلامي</h2><span>الإدارة المالية</span></div></div><div class="report-heading"><h1>${frappe.utils.escape_html(payload.title)}</h1><p><strong>الفترة:</strong> من ${frappe.datetime.str_to_user(payload.from_date)} إلى ${frappe.datetime.str_to_user(payload.to_date)}</p></div></header>${cards}<table><thead><tr>${headers}</tr></thead><tbody>${body}${totals}</tbody></table><footer>تم إنشاء هذا التقرير من النظام المحاسبي</footer></article>`;
}

function build_liquidity_print_cards(rows) {
	const detailRows = rows.filter((row) => row.__number !== "");
	const total = (field) => detailRows.reduce((sum, row) => sum + Number(row[field] || 0), 0);
	const cards = [["السيولة المتوفرة", total("available_liquidity")], ["التغير في السيولة", total("available_liquidity") - total("opening_liquidity")], ["استثمار في الذهب", total("gold_end")], ["مشتريات أصول", total("asset_purchase")], ["ودائع مجمّدة", total("frozen_end")], ["مراكز بسيولة سالبة", rows.filter((row) => row.__number !== "" && Number(row.available_liquidity || 0) < -.5).length]];
	return `<div class="liquidity-cards">${cards.map(([label, value]) => `<div><span>${label}</span><strong>${print_number(value)}</strong></div>`).join("")}</div>`;
}

function is_print_numeric(column) {
	return ["Currency", "Float", "Int"].includes(column.fieldtype);
}

function print_cell(value, column) {
	if (value === null || value === undefined || value === "") return "";
	return is_print_numeric(column) ? print_number(value) : frappe.utils.escape_html(String(value));
}

function print_number(value) {
	const number = Number(value || 0);
	if (Math.abs(number) < .005) return "-";
	return frappe.utils.escape_html(format_number(number, null, 2));
}

function print_liquidity_preview(payload, state) {
	const content = build_liquidity_print_html(payload, state);
	const win = window.open("", "_blank");
	if (!win) return frappe.msgprint(__("Allow pop-ups to print the report."));
	win.document.write(`<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8"><title>${frappe.utils.escape_html(payload.title)}</title><style>${liquidity_print_css()}</style></head><body>${content}</body></html>`);
	win.document.close(); win.focus(); setTimeout(() => win.print(), 300);
}

function liquidity_print_css() {
	return `@page{size:A3 landscape;margin:7mm}*{box-sizing:border-box}body{margin:0;color:#172033;font-family:Tahoma,Arial,"Noto Naskh Arabic",sans-serif}.liquidity-sheet{width:100%}header{margin-bottom:9px}.brand-bar{display:flex;align-items:center;gap:9px;border-bottom:2px solid #173b66;padding:0 2px 6px;color:#173b66}.brand-mark{width:34px;height:34px;border:2px solid #173b66;border-radius:50%;display:grid;place-items:center;font-size:20px;font-weight:800}.brand-bar h2{font-size:14px;margin:0}.brand-bar span{font-size:9px}.report-heading{text-align:center;padding:6px 0 1px}.report-heading h1{font-size:19px;margin:0 0 3px;color:#102f52}.report-heading p{font-size:11px;margin:0}.liquidity-cards{display:grid;grid-template-columns:repeat(6,1fr);gap:5px;margin:8px 0}.liquidity-cards div{border:1px solid #b9c7d6;border-top:3px solid #2b6f9f;border-radius:3px;padding:5px;text-align:center;background:#f7fafc}.liquidity-cards span{display:block;font-size:9px;color:#506176}.liquidity-cards strong{font-size:13px;color:#173b66;direction:ltr;display:block;margin-top:2px}table{width:100%;border-collapse:collapse;table-layout:auto;font-size:8.5px}th,td{border:1px solid #748397;padding:4px 3px;text-align:center;vertical-align:middle}th{background:#173b66;color:#fff;font-weight:700;line-height:1.45}.number{direction:ltr;font-variant-numeric:tabular-nums;white-space:nowrap}.group-row{font-weight:800;background:#dbe7f1;color:#102f52}.grand-total{font-weight:800;background:#b9cee0;border-top:2px solid #102f52;color:#102f52}tbody tr:not(.group-row):nth-child(even){background:#f8fafc}footer{text-align:left;color:#66788a;font-size:8px;margin-top:5px;border-top:1px solid #d6dee7;padding-top:3px}`;
}

function add_liquidity_print_styles() {
	if (document.getElementById("liquidity-print-designer-style")) return;
	$(`<style id="liquidity-print-designer-style">.liquidity-print-designer{display:grid;grid-template-columns:300px minmax(0,1fr);gap:12px;height:76vh}.liquidity-print-controls{overflow:auto;border:1px solid var(--border-color);border-radius:10px;padding:14px;background:var(--card-bg)}.liquidity-print-controls section+section{margin-top:16px}.control-title{font-weight:700;display:flex;justify-content:space-between;margin-bottom:8px;color:#173b66}.control-title button{border:0;background:#e8f1f8;color:#173b66;border-radius:12px;padding:2px 10px;font-size:11px}.column-options,.row-options{display:flex;flex-direction:column;gap:6px}.column-options label,.row-options label{font-size:12px;margin:0}.liquidity-print-canvas{overflow:auto;background:#d9e0e7;padding:18px}.liquidity-sheet.preview{background:#fff;min-width:1500px;padding:20px;color:#172033;font-family:Tahoma,Arial,sans-serif;box-shadow:0 3px 16px rgba(0,0,0,.14)}.liquidity-sheet.preview .brand-bar{display:flex;align-items:center;gap:9px;border-bottom:2px solid #173b66;padding-bottom:7px;color:#173b66}.liquidity-sheet.preview .brand-mark{width:36px;height:36px;border:2px solid #173b66;border-radius:50%;display:grid;place-items:center;font-size:20px;font-weight:800}.liquidity-sheet.preview .brand-bar h2{font-size:15px;margin:0}.liquidity-sheet.preview .brand-bar span{font-size:10px}.liquidity-sheet.preview .report-heading{text-align:center;padding:8px 0}.liquidity-sheet.preview h1{font-size:21px;margin:0;color:#102f52}.liquidity-sheet.preview .report-heading p{margin:4px}.liquidity-sheet.preview .liquidity-cards{display:grid;grid-template-columns:repeat(6,1fr);gap:6px;margin:8px 0}.liquidity-sheet.preview .liquidity-cards div{border:1px solid #b9c7d6;border-top:3px solid #2b6f9f;border-radius:4px;padding:6px;text-align:center;background:#f7fafc}.liquidity-sheet.preview .liquidity-cards span{display:block;font-size:10px;color:#506176}.liquidity-sheet.preview .liquidity-cards strong{display:block;color:#173b66;font-size:14px}.liquidity-sheet.preview table{width:100%;border-collapse:collapse;font-size:9px}.liquidity-sheet.preview th,.liquidity-sheet.preview td{border:1px solid #748397;padding:4px;text-align:center}.liquidity-sheet.preview th{background:#173b66;color:#fff;font-weight:700}.liquidity-sheet.preview .group-row{background:#dbe7f1;color:#102f52;font-weight:800}.liquidity-sheet.preview .grand-total{background:#b9cee0;color:#102f52;font-weight:800}.liquidity-sheet.preview .number{direction:ltr;white-space:nowrap}.liquidity-sheet.preview footer{text-align:left;color:#66788a;font-size:9px;margin-top:6px}@media(max-width:900px){.liquidity-print-designer{grid-template-columns:1fr;height:auto}.liquidity-print-controls{max-height:35vh}.liquidity-print-canvas{max-height:55vh}}</style>`).appendTo(document.head);
}
