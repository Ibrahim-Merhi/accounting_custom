const daily_movement_arabic_print_format = `
		<style>
			@page { size: A4 landscape; margin: 7mm; }
			.daily-movement-print { direction: rtl; width: 100%; font-family: Tahoma, Arial, sans-serif; color: #15191d; font-size: 10px; }
			.daily-movement-print .report-head { display: flex; align-items: center; justify-content: space-between; gap: 20px; border-bottom: 2px solid #202a33; padding: 0 0 7px; margin-bottom: 9px; }
			.daily-movement-print .title-block { white-space: nowrap; }
			.daily-movement-print h1 { margin: 0; font-size: 22px; font-weight: 700; }
			.daily-movement-print .subtitle { margin-top: 2px; color: #59636c; }
			.daily-movement-print .meta { display: flex; align-items: center; gap: 24px; text-align: right; font-size: 10px; white-space: nowrap; }
			.daily-movement-print .currency-section { margin: 0 0 11px; }
			.daily-movement-print .section-title { background: #202a33; color: #fff; padding: 5px 8px; font-size: 12px; font-weight: 700; }
			.daily-movement-print .summary { display: table; width: 100%; table-layout: fixed; border-collapse: collapse; margin: 0 0 8px; }
			.daily-movement-print .summary-item { display: table-cell; border: 1px solid #aeb6bd; padding: 5px 8px; background: #f3f5f6; }
			.daily-movement-print .summary-label { display: block; color: #59636c; font-size: 8px; margin-bottom: 2px; }
			.daily-movement-print .summary-value { display: block; direction: ltr; text-align: right; font-size: 12px; font-weight: 700; white-space: nowrap; }
			.daily-movement-print table.transactions { width: 100%; table-layout: fixed; border-collapse: collapse; }
			.daily-movement-print .transactions thead { display: table-header-group; }
			.daily-movement-print .transactions th { background: #dfe4e7; font-weight: 700; }
			.daily-movement-print .transactions th, .daily-movement-print .transactions td { border: 1px solid #b8bec4; padding: 4px 5px; text-align: right; vertical-align: top; overflow-wrap: anywhere; }
			.daily-movement-print .transactions tr { page-break-inside: avoid; }
			.daily-movement-print .transactions tbody tr:nth-child(even) { background: #f8f9f9; }
			.daily-movement-print .amount { direction: ltr; text-align: right !important; white-space: nowrap; font-weight: 600; }
			.daily-movement-print .empty-row { text-align: center !important; color: #69747d; padding: 7px !important; }
			.daily-movement-print .signatures { display: flex; justify-content: space-between; gap: 50px; margin-top: 20px; page-break-inside: avoid; }
			.daily-movement-print .signature { width: 30%; border-top: 1px solid #59636c; padding-top: 5px; text-align: center; }
			.daily-movement-print .print-footer { margin-top: 10px; padding-top: 5px; border-top: 1px solid #c8cdd1; text-align: center; color: #69747d; font-size: 8px; }
			@media print { .daily-movement-print { width: 100%; } }
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
						<colgroup><col style="width:16%"><col style="width:17%"><col style="width:20%"><col style="width:25%"><col style="width:11%"><col style="width:11%"></colgroup>
						<thead><tr><th>نوع المستند</th><th>رقم المستند</th><th>الجهة</th><th>البيان</th><th>الوارد</th><th>الصادر</th></tr></thead>
						<tbody>
						{% if transactions.length %}
							{% for row in transactions %}
							<tr><td>{{ row.voucher_type === "Donation Entry" ? "سند تبرع" : (row.voucher_type === "Accounting Payment Entry" ? "سند صرف" : row.voucher_type) }}</td><td dir="ltr">{{ row.voucher_no }}</td><td>{{ row.party || "" }}</td><td>{{ row.description || "" }}</td><td class="amount">{% if row.incoming %}{{ frappe.format(row.incoming, {fieldtype: "Currency", options: item.code}) }}{% endif %}</td><td class="amount">{% if row.outgoing %}{{ frappe.format(row.outgoing, {fieldtype: "Currency", options: item.code}) }}{% endif %}</td></tr>
							{% endfor %}
						{% else %}
							<tr><td colspan="6" class="empty-row">لا توجد حركات لهذه العملة في التاريخ المحدد</td></tr>
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
				print_settings: { orientation: "Landscape" },
				landscape: true,
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
