const daily_movement_arabic_print_format = `
		<style>
			@page { size: A4 portrait; margin: 9mm; }
			.daily-movement-print { direction: rtl; width: 100%; font-family: Tahoma, Arial, sans-serif; color: #111; font-size: 13px; }
			.daily-movement-print .report-head { display: flex; align-items: center; justify-content: space-between; gap: 20px; border-bottom: 2px solid #202a33; padding: 0 0 7px; margin-bottom: 9px; }
			.daily-movement-print .title-block { white-space: nowrap; }
			.daily-movement-print h1 { margin: 0; font-size: 25px; font-weight: 700; }
			.daily-movement-print .subtitle { margin-top: 2px; color: #59636c; }
			.daily-movement-print .meta { display: flex; align-items: center; gap: 20px; text-align: right; font-size: 12px; white-space: nowrap; }
			.daily-movement-print .currency-section { margin: 0 0 11px; }
			.daily-movement-print .section-title { border: 2px solid #333; border-bottom: 0; padding: 5px 8px; font-size: 15px; font-weight: 700; }
			.daily-movement-print .summary { display: table; width: 100%; table-layout: fixed; border-collapse: collapse; margin: 0 0 8px; }
			.daily-movement-print .summary-item { display: table-cell; border: 1px solid #888; padding: 6px 7px; }
			.daily-movement-print .summary-label { display: block; color: #333; font-size: 11px; margin-bottom: 2px; }
			.daily-movement-print .summary-value { display: block; direction: ltr; text-align: right; font-size: 14px; font-weight: 700; white-space: nowrap; }
			.daily-movement-print table.transactions { width: 100%; table-layout: fixed; border-collapse: collapse; }
			.daily-movement-print .transactions thead { display: table-header-group; }
			.daily-movement-print .transactions th { border-bottom: 2px solid #555 !important; font-weight: 700; }
			.daily-movement-print .transactions th, .daily-movement-print .transactions td { border: 1px solid #999; padding: 6px 7px; text-align: right; vertical-align: top; overflow-wrap: anywhere; }
			.daily-movement-print .transactions tr { page-break-inside: avoid; }
			.daily-movement-print .amount { direction: ltr; text-align: right !important; white-space: nowrap; font-size: 14px; font-weight: 700; }
			.daily-movement-print .empty-row { text-align: center !important; color: #69747d; padding: 7px !important; }
			.daily-movement-print .signatures { display: flex; justify-content: space-between; gap: 50px; margin-top: 20px; page-break-inside: avoid; }
			.daily-movement-print .signature { width: 30%; border-top: 1px solid #59636c; padding-top: 5px; text-align: center; }
			.daily-movement-print .print-footer { margin-top: 10px; padding-top: 5px; border-top: 1px solid #999; text-align: center; color: #444; font-size: 10px; }
			@media print { .daily-movement-print { width: 100%; } * { -webkit-print-color-adjust: economy !important; print-color-adjust: economy !important; } }
		</style>
		<div class="daily-movement-print">
			<div class="report-head">
				<div class="title-block"><h1>الحركة اليومية</h1><div class="subtitle">بيان حركة الصندوق اليومية</div></div>
				<div class="meta"><span><strong>الشركة:</strong> {{ filters.company }}</span><span><strong>التاريخ:</strong> {{ filters.date }}</span></div>
			</div>
			{% var currencies = [{code: "LBP", label: "الليرة اللبنانية"}, {code: "USD", label: "الدولار الأمريكي"}]; %}
			{% for item in currencies %}
				{% var section = original_data.find(row => row.currency === item.code && row.is_section); %}
				{% var total = original_data.find(row => row.currency === item.code && row.is_total); %}
				{% var transactions = original_data.filter(row => row.currency === item.code && row.voucher_no); %}
				<div class="currency-section">
					<div class="section-title">{{ item.label }} ({{ item.code }})</div>
					<div class="summary">
						<div class="summary-item"><span class="summary-label">الرصيد السابق</span><span class="summary-value">{{ frappe.format((section && section.previous_balance) || 0, {fieldtype: "Currency", options: item.code}) }}</span></div>
						<div class="summary-item"><span class="summary-label">إجمالي الوارد</span><span class="summary-value">{{ frappe.format((total && total.incoming) || 0, {fieldtype: "Currency", options: item.code}) }}</span></div>
						<div class="summary-item"><span class="summary-label">إجمالي الصادر</span><span class="summary-value">{{ frappe.format((total && total.outgoing) || 0, {fieldtype: "Currency", options: item.code}) }}</span></div>
						<div class="summary-item"><span class="summary-label">الرصيد الحالي</span><span class="summary-value">{{ frappe.format((section && section.current_balance) || 0, {fieldtype: "Currency", options: item.code}) }}</span></div>
					</div>
					<table class="transactions">
						<colgroup><col style="width:56%"><col style="width:22%"><col style="width:22%"></colgroup>
						<thead><tr><th>الوصف</th><th>الوارد</th><th>الصادر</th></tr></thead>
						<tbody>
						{% if transactions.length %}
							{% for row in transactions %}
							<tr><td>{{ row.description || "" }}</td><td class="amount">{% if row.incoming %}{{ frappe.format(row.incoming, {fieldtype: "Currency", options: item.code}) }}{% endif %}</td><td class="amount">{% if row.outgoing %}{{ frappe.format(row.outgoing, {fieldtype: "Currency", options: item.code}) }}{% endif %}</td></tr>
							{% endfor %}
						{% else %}
							<tr><td colspan="3" class="empty-row">لا توجد حركات لهذه العملة في التاريخ المحدد</td></tr>
						{% endif %}
						</tbody>
					</table>
				</div>
			{% endfor %}
			<div class="signatures"><div class="signature">أمين الصندوق</div><div class="signature">المحاسب</div><div class="signature">الاعتماد</div></div>
			<div class="print-footer">تم إصدار هذا التقرير من نظام المحاسبة</div>
		</div>`;

frappe.query_reports["Daily Movement"] = {
	html_format: daily_movement_arabic_print_format,
	onload(report) {
		const print_arabic_report = () => {
			report.make_access_log?.("Print", "PDF");
			frappe.render_grid({
				template: daily_movement_arabic_print_format,
				title: "الحركة اليومية",
				subtitle: "",
				print_settings: { orientation: "Portrait" },
				landscape: false,
				filters: report.get_filter_values(),
				data: report.get_data_for_print(),
				columns: report.columns,
				original_data: report.data,
				report,
				can_use_smaller_font: 0,
			});
		};

		// Frappe's print dialog forces the generic grid when it supplies columns.
		// Keep every print path for this report on the dedicated Arabic format.
		report.print_report = print_arabic_report;
		report.page.add_inner_button(__("Arabic Print"), print_arabic_report, __("Print"));
	},
	filters: [
		{
			fieldname: "company",
			label: __("Company"),
			fieldtype: "Link",
			options: "Company",
			reqd: 1,
			default: frappe.defaults.get_user_default("Company"),
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
		if (amount_fields.includes(column.fieldname) && (value === null || value === undefined || value === "")) {
			return "";
		}
		if (["previous_balance", "current_balance"].includes(column.fieldname) && !data?.is_section) {
			return "";
		}
		value = default_formatter(value, row, column, data);
		if (data?.is_section) {
			return `<strong style="font-size:14px">${value}</strong>`;
		}
		if (data?.is_total) {
			return `<strong>${value}</strong>`;
		}
		return value;
	},
};
