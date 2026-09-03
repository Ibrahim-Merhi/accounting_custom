frappe.query_reports["Daily Movement"] = {
	html_format: `
		<style>
			.daily-movement-print { direction: rtl; font-family: Arial, Tahoma, sans-serif; color: #161616; }
			.daily-movement-print .report-head { text-align: center; border-bottom: 2px solid #111; padding-bottom: 12px; margin-bottom: 18px; }
			.daily-movement-print h1 { margin: 0 0 8px; font-size: 24px; }
			.daily-movement-print .meta { display: flex; justify-content: center; gap: 32px; font-size: 13px; }
			.daily-movement-print table { width: 100%; border-collapse: collapse; margin-bottom: 22px; }
			.daily-movement-print th { background: #1f2933; color: #fff; font-weight: 700; }
			.daily-movement-print th, .daily-movement-print td { border: 1px solid #b8bec5; padding: 7px 8px; text-align: right; }
			.daily-movement-print .amount { direction: ltr; text-align: left; white-space: nowrap; }
			.daily-movement-print .section td { background: #e9edf0; font-weight: 700; border-top: 2px solid #1f2933; }
			.daily-movement-print .total td { background: #f4f5f6; font-weight: 700; border-top: 2px solid #59636e; }
			.daily-movement-print .balance { display: inline-block; margin-left: 24px; }
			@media print { .daily-movement-print { font-size: 11px; } }
		</style>
		<div class="daily-movement-print">
			<div class="report-head">
				<h1>الحركة اليومية</h1>
				<div class="meta"><span><strong>الشركة:</strong> {{ filters.company }}</span><span><strong>التاريخ:</strong> {{ filters.date }}</span></div>
			</div>
			<table>
				<thead><tr><th>العملة</th><th>نوع المستند</th><th>رقم المستند</th><th>الجهة</th><th>البيان</th><th>الوارد</th><th>الصادر</th></tr></thead>
				<tbody>
				{% for row in original_data %}
					{% if row.is_section %}
					<tr class="section"><td colspan="7">{{ row.currency }} - {{ row.description }} <span class="balance">الرصيد السابق: {{ frappe.format(row.previous_balance, {fieldtype: 'Currency', options: row.currency}) }}</span><span class="balance">الرصيد الحالي: {{ frappe.format(row.current_balance, {fieldtype: 'Currency', options: row.currency}) }}</span></td></tr>
					{% elif row.is_total %}
					<tr class="total"><td colspan="5">إجمالي الحركة اليومية</td><td class="amount">{% if row.incoming %}{{ frappe.format(row.incoming, {fieldtype: 'Currency', options: row.currency}) }}{% endif %}</td><td class="amount">{% if row.outgoing %}{{ frappe.format(row.outgoing, {fieldtype: 'Currency', options: row.currency}) }}{% endif %}</td></tr>
					{% else %}
					<tr><td>{{ row.currency }}</td><td>{{ __(row.voucher_type) }}</td><td>{{ row.voucher_no }}</td><td>{{ row.party || '' }}</td><td>{{ row.description || '' }}</td><td class="amount">{% if row.incoming %}{{ frappe.format(row.incoming, {fieldtype: 'Currency', options: row.currency}) }}{% endif %}</td><td class="amount">{% if row.outgoing %}{{ frappe.format(row.outgoing, {fieldtype: 'Currency', options: row.currency}) }}{% endif %}</td></tr>
					{% endif %}
				{% endfor %}
				</tbody>
			</table>
		</div>`,
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
