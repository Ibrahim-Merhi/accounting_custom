frappe.query_reports["Daily Movement"] = {
	html_format: `
		<style>
			.daily-movement-print { direction: rtl; font-family: Tahoma, Arial, sans-serif; color: #15191d; font-size: 11px; }
			.daily-movement-print .report-head { display: flex; align-items: flex-end; justify-content: space-between; border-bottom: 3px solid #202a33; padding: 0 0 10px; margin-bottom: 14px; }
			.daily-movement-print h1 { margin: 0; font-size: 25px; font-weight: 700; }
			.daily-movement-print .meta { line-height: 1.9; text-align: left; font-size: 11px; }
			.daily-movement-print .currency-section { margin: 0 0 22px; page-break-inside: avoid; }
			.daily-movement-print .section-title { background: #202a33; color: #fff; padding: 7px 10px; font-size: 14px; font-weight: 700; }
			.daily-movement-print .summary { display: table; width: 100%; table-layout: fixed; border-collapse: collapse; margin: 0 0 8px; }
			.daily-movement-print .summary-item { display: table-cell; border: 1px solid #aeb6bd; padding: 7px 9px; background: #f3f5f6; }
			.daily-movement-print .summary-label { display: block; color: #59636c; font-size: 9px; margin-bottom: 3px; }
			.daily-movement-print .summary-value { display: block; direction: ltr; text-align: right; font-size: 14px; font-weight: 700; white-space: nowrap; }
			.daily-movement-print table.transactions { width: 100%; table-layout: fixed; border-collapse: collapse; }
			.daily-movement-print .transactions th { background: #dfe4e7; font-weight: 700; }
			.daily-movement-print .transactions th, .daily-movement-print .transactions td { border: 1px solid #b8bec4; padding: 6px 7px; text-align: right; vertical-align: top; overflow-wrap: anywhere; }
			.daily-movement-print .transactions tbody tr:nth-child(even) { background: #f8f9f9; }
			.daily-movement-print .amount { direction: ltr; text-align: right !important; white-space: nowrap; font-weight: 600; }
			.daily-movement-print .empty-row { text-align: center !important; color: #69747d; padding: 14px !important; }
			.daily-movement-print .signatures { display: flex; justify-content: space-between; gap: 50px; margin-top: 28px; }
			.daily-movement-print .signature { width: 30%; border-top: 1px solid #59636c; padding-top: 5px; text-align: center; }
			.daily-movement-print .print-footer { margin-top: 18px; padding-top: 6px; border-top: 1px solid #c8cdd1; text-align: center; color: #69747d; font-size: 9px; }
			@media print { .daily-movement-print { font-size: 10px; } .daily-movement-print .currency-section { page-break-inside: avoid; } }
		</style>
		<div class="daily-movement-print">
			<div class="report-head">
				<div><h1>الحركة اليومية</h1><div>بيان حركة الصندوق اليومية</div></div>
				<div class="meta"><div><strong>الشركة:</strong> {{ filters.company }}</div><div><strong>التاريخ:</strong> {{ filters.date }}</div></div>
			</div>
			{% var currencies = [{code: "LBP", label: "الليرة اللبنانية"}, {code: "USD", label: "الدولار الأمريكي"}]; %}
			{% for item in currencies %}
				{% var section = original_data.find(row => row.currency === item.code && row.is_section); %}
				{% var total = original_data.find(row => row.currency === item.code && row.is_total); %}
				{% var transactions = original_data.filter(row => row.currency === item.code && row.voucher_no); %}
				<div class="currency-section">
					<div class="section-title">{{ item.label }} ({{ item.code }})</div>
					<div class="summary">
						<div class="summary-item"><span class="summary-label">الرصيد السابق</span><span class="summary-value">{{ frappe.format(section.previous_balance, {fieldtype: "Currency", options: item.code}) }}</span></div>
						<div class="summary-item"><span class="summary-label">إجمالي الوارد</span><span class="summary-value">{{ frappe.format((total && total.incoming) || 0, {fieldtype: "Currency", options: item.code}) }}</span></div>
						<div class="summary-item"><span class="summary-label">إجمالي الصادر</span><span class="summary-value">{{ frappe.format((total && total.outgoing) || 0, {fieldtype: "Currency", options: item.code}) }}</span></div>
						<div class="summary-item"><span class="summary-label">الرصيد الحالي</span><span class="summary-value">{{ frappe.format(section.current_balance, {fieldtype: "Currency", options: item.code}) }}</span></div>
					</div>
					<table class="transactions">
						<colgroup><col style="width:16%"><col style="width:17%"><col style="width:20%"><col style="width:25%"><col style="width:11%"><col style="width:11%"></colgroup>
						<thead><tr><th>نوع المستند</th><th>رقم المستند</th><th>الجهة</th><th>البيان</th><th>الوارد</th><th>الصادر</th></tr></thead>
						<tbody>
						{% if transactions.length %}
							{% for row in transactions %}
							<tr><td>{{ __(row.voucher_type) }}</td><td dir="ltr">{{ row.voucher_no }}</td><td>{{ row.party || "" }}</td><td>{{ row.description || "" }}</td><td class="amount">{% if row.incoming %}{{ frappe.format(row.incoming, {fieldtype: "Currency", options: item.code}) }}{% endif %}</td><td class="amount">{% if row.outgoing %}{{ frappe.format(row.outgoing, {fieldtype: "Currency", options: item.code}) }}{% endif %}</td></tr>
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
		</div>`,
	onload(report) {
		report.page.add_inner_button(__("Arabic Print"), () => {
			report.print_report({ orientation: "Landscape" });
		}, __("Print"));
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
