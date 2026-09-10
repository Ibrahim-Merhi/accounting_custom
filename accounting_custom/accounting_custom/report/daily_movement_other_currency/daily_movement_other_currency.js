const daily_movement_other_currency_print_format = `
		<style>
			@page { size: A4 portrait; margin: 9mm; }
			.daily-movement-print { direction: rtl; width: 100%; font-family: Tahoma, Arial, sans-serif; color: #111; font-size: 13px; }
			.daily-movement-print .report-head { display: flex; align-items: center; justify-content: space-between; gap: 20px; border-bottom: 2px solid #202a33; padding: 0 0 7px; margin-bottom: 9px; }
			.daily-movement-print .title-block { white-space: nowrap; }
			.daily-movement-print h1 { margin: 0; font-size: 25px; font-weight: 700; }
			.daily-movement-print .subtitle { margin-top: 2px; color: #59636c; }
			.daily-movement-print .meta { display: flex; align-items: center; gap: 20px; text-align: right; font-size: 16px; font-weight: 700; white-space: nowrap; }
			.daily-movement-print .currency-section { margin: 0 0 11px; }
			.daily-movement-print .section-title { border: 2px solid #333; border-bottom: 0; padding: 5px 8px; font-size: 15px; font-weight: 700; }
			.daily-movement-print .summary { display: grid; grid-template-columns: 27% 27% 23% 23%; direction: rtl; width: 100%; margin: 0 0 8px; }
			.daily-movement-print .summary-item { border: 1px solid #888; border-left: 0; padding: 6px 7px; }
			.daily-movement-print .summary-item:last-child { border-left: 1px solid #888; }
			.daily-movement-print .summary-label { display: block; color: #333; font-size: 11px; margin-bottom: 2px; }
			.daily-movement-print .summary-value { display: block; direction: ltr; text-align: right; font-size: 14px; font-weight: 700; white-space: nowrap; }
			.daily-movement-print table.transactions { width: 100%; table-layout: fixed; border-collapse: collapse; }
			.daily-movement-print .transactions thead { display: table-header-group; }
			.daily-movement-print .transactions th { border-bottom: 2px solid #555 !important; font-weight: 700; }
			.daily-movement-print .transactions th, .daily-movement-print .transactions td { border: 1px solid #999; padding: 6px 7px; text-align: right; vertical-align: top; overflow-wrap: anywhere; }
			.daily-movement-print .transactions tr { page-break-inside: avoid; }
			.daily-movement-print .amount { direction: ltr; text-align: right !important; white-space: nowrap; font-size: 14px; font-weight: 700; }
			.daily-movement-print .empty-row { text-align: center !important; color: #69747d; padding: 7px !important; }
			.daily-movement-print .signatures { display: flex; justify-content: center; align-items: flex-start; gap: 24px; margin-top: 10px; page-break-inside: avoid; }
			.daily-movement-print .signature { width: 38%; text-align: center; font-size: 15px; font-weight: 700; }
			.daily-movement-print .signature-line { position: relative; height: 8px; margin-top: 68px; border-top: 1px solid #59636c; }
			.daily-movement-print .signature-image { position: absolute; top: 0; left: 50%; display: block; width: 82px; height: 78px; object-fit: contain; mix-blend-mode: multiply; transform: translate(-50%, -100%); }
			.daily-movement-print .print-footer { margin-top: 4px; padding-top: 4px; border-top: 1px solid #999; text-align: center; color: #444; font-size: 10px; }
			.daily-movement-print .print-action { position: fixed; top: 14px; left: 14px; z-index: 10; border: 1px solid #222; border-radius: 4px; padding: 8px 18px; background: #fff; color: #111; font: 700 13px Tahoma, Arial, sans-serif; cursor: pointer; box-shadow: 0 1px 4px rgba(0, 0, 0, 0.16); }
			.daily-movement-print .print-action:hover { background: #f3f3f3; }
			@media print { .daily-movement-print { width: 100%; } .daily-movement-print .print-action { display: none !important; } * { -webkit-print-color-adjust: economy !important; print-color-adjust: economy !important; } }
		</style>
		<div class="daily-movement-print">
			<button type="button" class="print-action" onclick="window.print()">طباعة</button>
			<div class="report-head">
				<div class="title-block"><h1>الحركة اليومية للعملات الأخرى</h1><div class="subtitle">بيان حركة الصندوق للعملات غير الدولار والليرة اللبنانية</div></div>
				<div class="meta"><span><strong>التاريخ:</strong> {{ filters.date }}</span></div>
			</div>
			{% var display_amount = value => format_number(value, null, 2).replace(/\.00$/, ""); %}
			{% var section_keys = [...new Set(original_data.filter(row => row.section_key).map(row => row.section_key))]; %}
			{% for item in section_keys %}
				{% var sections = original_data.filter(row => row.section_key === item && row.is_section); %}
				{% var transactions = original_data.filter(row => row.section_key === item && row.voucher_no); %}
				{% var currency_code = sections[0]?.currency || ""; %}
				{% var currency_symbol = sections[0]?.currency_symbol || currency_code; %}
				{% var currency_name = sections[0]?.currency_name_ar || sections[0]?.currency_name || currency_code; %}
				{% var previous = sections.reduce((sum, row) => sum + Number(row.previous_balance || 0), 0); %}
				{% var incoming = transactions.reduce((sum, row) => sum + Number(row.incoming || 0), 0); %}
				{% var outgoing = transactions.reduce((sum, row) => sum + Number(row.outgoing || 0), 0); %}
				{% var opening_date = sections.find(row => row.opening_date)?.opening_date || ""; %}
				<div class="currency-section">
					<div class="section-title">{{ currency_name }} ({{ currency_code }})</div>
					<div class="summary">
						<div class="summary-item"><span class="summary-label">الرصيد السابق{% if opening_date %} حتى {{ opening_date }}{% endif %}</span><span class="summary-value">{{ currency_symbol }} {{ display_amount(previous) }}</span></div>
						<div class="summary-item"><span class="summary-label">الرصيد الحالي</span><span class="summary-value">{{ currency_symbol }} {{ display_amount(previous + incoming - outgoing) }}</span></div>
						<div class="summary-item"><span class="summary-label">إجمالي الوارد</span><span class="summary-value">{{ currency_symbol }} {{ display_amount(incoming) }}</span></div>
						<div class="summary-item"><span class="summary-label">إجمالي الصادر</span><span class="summary-value">{{ currency_symbol }} {{ display_amount(outgoing) }}</span></div>
					</div>
					<table class="transactions">
						<colgroup><col style="width:54%"><col style="width:23%"><col style="width:23%"></colgroup>
						<thead><tr><th>الوصف</th><th>الوارد</th><th>الصادر</th></tr></thead>
						<tbody>
						{% if transactions.length %}
							{% for row in transactions %}
							<tr><td>{{ row.description || "" }}</td><td class="amount">{% if row.incoming %}{{ currency_symbol }} {{ display_amount(row.incoming) }}{% endif %}</td><td class="amount">{% if row.outgoing %}{{ currency_symbol }} {{ display_amount(row.outgoing) }}{% endif %}</td></tr>
							{% endfor %}
						{% else %}
							<tr><td colspan="3" class="empty-row">لا توجد حركات لهذه العملة في التاريخ المحدد</td></tr>
						{% endif %}
						</tbody>
					</table>
				</div>
			{% endfor %}
			<div class="signatures">
				<div class="signature">
					أمين الصندوق
					<div class="signature-line">
						<img class="signature-image" src="https://i.imgur.com/aP1ydEJ.jpg" alt="توقيع وختم أمين الصندوق">
					</div>
				</div>
				<div class="signature">
					رئيس الجمعية
					<div class="signature-line"></div>
				</div>
			</div>
			<div class="print-footer">تم إصدار هذا التقرير من نظام المحاسبة</div>
		</div>`;

frappe.query_reports["Daily Movement Other Currency"] = {
	html_format: daily_movement_other_currency_print_format,
	onload(report) {
		const print_arabic_report = (movement_only = false) => {
			const report_data = report.data || [];
			const active_sections = new Set(
				report_data
					.filter((row) => row.voucher_no && (Number(row.incoming || 0) || Number(row.outgoing || 0)))
					.map((row) => row.section_key)
			);
			const print_data = movement_only
				? report_data.filter((row) => !row.section_key || active_sections.has(row.section_key))
				: report_data;
			report.make_access_log?.("Print", "PDF");
			frappe.render_grid({
				template: daily_movement_other_currency_print_format,
				title: "الحركة اليومية للعملات الأخرى",
				subtitle: "",
				print_settings: { orientation: "Portrait" },
				landscape: false,
				filters: report.get_filter_values(),
				data: report.get_data_for_print(),
				columns: report.columns,
				original_data: print_data,
				report,
				can_use_smaller_font: 0,
			});
		};
		const print_all_currencies = () => print_arabic_report(false);
		const print_active_currencies = () => print_arabic_report(true);

		// Frappe's print dialog forces the generic grid when it supplies columns.
		// Keep every print path for this report on the dedicated Arabic format.
		report.print_report = print_all_currencies;
		report.page.add_inner_button(
			__("Arabic - All Currencies"), print_all_currencies, __("Print")
		);
		report.page.add_inner_button(
			__("Arabic - Currencies With Movement Only"), print_active_currencies, __("Print")
		);
	},
	filters: [
		{
			fieldname: "company",
			label: __("Company"),
			fieldtype: "MultiSelectList",
			options: "Company",
			get_data: (txt) => frappe.db.get_link_options("Company", txt, {
				name: ["!=", "Namaa"],
			}),
		},
		{
			fieldname: "date",
			label: __("Date"),
			fieldtype: "Date",
			reqd: 1,
			default: frappe.datetime.get_today(),
		},
	],
	formatter(value, row, column, data, default_formatter) {
		const amount_fields = ["incoming", "outgoing", "previous_balance", "current_balance"];
		if (data?.is_company) {
			if (column.fieldname !== "description") {
				return "";
			}
			return `<strong style="display:block;font-size:13px;white-space:nowrap">${value}</strong>`;
		}
		if (amount_fields.includes(column.fieldname) && (value === null || value === undefined || value === "")) {
			return "";
		}
		if (["previous_balance", "current_balance"].includes(column.fieldname) && !data?.is_section) {
			return "";
		}
		if (amount_fields.includes(column.fieldname) && data?.currency) {
			const symbol = data.currency_symbol || data.currency;
			value = `${symbol} ${format_number(value, null, 2)}`;
		} else {
			value = default_formatter(value, row, column, data);
		}
		if (data?.is_section) {
			return `<strong style="font-size:14px">${value}</strong>`;
		}
		if (data?.is_total) {
			return `<strong>${value}</strong>`;
		}
		return value;
	},
};
