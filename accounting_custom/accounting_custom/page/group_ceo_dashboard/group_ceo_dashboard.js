frappe.pages["group-ceo-dashboard"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({parent: wrapper, title: __("Group CEO Dashboard"), single_column: true});
	page.set_primary_action(__("Refresh"), () => render(), "refresh");
	const root = $("<div class='group-ceo-dashboard'></div>").appendTo(page.main);

	async function render() {
		root.html(`<div class="gceo-loading">${__("Loading executive information…")}</div>`);
		try {
			const data = (await frappe.call("accounting_custom.executive.get_dashboard_data")).message;
			root.html(layout(data));
			renderCharts(data);
		} catch (error) {
			root.html(`<div class="gceo-error">${frappe.utils.escape_html(error.message || error)}</div>`);
		}
	}

	function metric(label, value, tone = "blue") {
		return `<div class="gceo-metric ${tone}"><span>${__(label)}</span><strong>${format(value)}</strong></div>`;
	}
	function format(value) { return new Intl.NumberFormat().format(Number(value || 0)); }
	function money(value, currency) { return `${format(value)} ${frappe.utils.escape_html(currency || "")}`; }
	function layout(data) {
		const m = data.metrics;
		const financeRows = (data.company_finance || []).map(row => {
			const net = Number(row.income_ytd || 0) - Number(row.expense_ytd || 0);
			return `<tr><td><strong>${frappe.utils.escape_html(row.company)}</strong></td><td>${money(row.income_ytd,row.currency)}</td><td>${money(row.expense_ytd,row.currency)}</td><td class="${net < 0 ? "negative" : "positive"}">${money(net,row.currency)}</td><td>${money(row.cash_bank,row.currency)}</td></tr>`;
		}).join("");
		return `<section class="gceo-hero"><div><span>${__("Organization-wide intelligence")}</span><h2>${__("Executive Overview")}</h2><p>${__("Live consolidated information across every company, department and program.")}</p></div><b>${data.companies.length} ${__("companies")}</b></section>
		<section class="gceo-metrics">${metric("Active Employees",m.active_employees,"green")}${metric("Pending Leaves",m.pending_leaves,"amber")}${metric("Attendance Today",m.attendance_today,"blue")}${metric("Absent Today",m.absent_today,"red")}${metric("Payroll YTD",m.payroll_ytd,"purple")}${metric("Donors",m.donors,"rose")}${metric("Beneficiaries",m.beneficiaries,"teal")}${metric("Orphans",m.orphans,"orange")}${metric("Families",m.families,"cyan")}${metric("Relief Orders",m.relief_orders,"indigo")}${metric("Statements",m.relief_statements,"blue")}${metric("Activities",m.activities,"green")}</section>
		<section class="gceo-finance"><div><span>${__("Donations YTD · USD")}</span><strong>$${format(m.donations_usd)}</strong></div><div><span>${__("Donations YTD · LBP")}</span><strong>${format(m.donations_lbp)} LBP</strong></div><div><span>${__("Donation Transactions")}</span><strong>${format(m.donations)}</strong></div></section>
		<section class="gceo-company-finance"><header><span>${__("Organization-wide finance")}</span><h3>${__("Financial Position by Company")}</h3></header><div class="gceo-table-wrap"><table><thead><tr><th>${__("Company")}</th><th>${__("Income YTD")}</th><th>${__("Expenses YTD")}</th><th>${__("Net Result")}</th><th>${__("Cash & Bank")}</th></tr></thead><tbody>${financeRows || `<tr><td colspan="5">${__("No financial entries found.")}</td></tr>`}</tbody></table></div></section>
		<section class="gceo-charts"><article><h3>${__("Attendance Today")}</h3><div id="gceo-attendance"></div></article><article><h3>${__("Leave Trend")}</h3><div id="gceo-leaves"></div></article><article><h3>${__("Donations · USD")}</h3><div id="gceo-donations"></div></article></section>
		<section class="gceo-reports"><header><div><span>${__("Decision center")}</span><h3>${__("Reports and Records")}</h3></div><input type="search" placeholder="${__("Filter reports…")}" id="gceo-report-search"></header><div class="gceo-report-grid">${data.reports.map(group => `<article><h4>${__(group.group)}</h4>${group.items.map(item => `<a href="${item.route}">${__(item.label)}<span>→</span></a>`).join("")}</article>`).join("")}</div></section>`;
	}
	function renderCharts(data) {
		const make = (selector, labels, values, type, colors) => new frappe.Chart(selector, {data:{labels,datasets:[{values}]},type,height:220,colors,axisOptions:{xIsSeries:true},tooltipOptions:{formatTooltipY:d=>format(d)}});
		make("#gceo-attendance", data.attendance.map(x=>__(x.label)), data.attendance.map(x=>x.value), "donut", ["#19a56b","#df5261","#7057c8","#e1a32b","#3977c3"]);
		make("#gceo-leaves", data.leave_trend.labels, data.leave_trend.values, "line", ["#df9d25"]);
		make("#gceo-donations", data.donation_usd_trend.labels, data.donation_usd_trend.values, "bar", ["#169b62"]);
		$("#gceo-report-search").on("input", function(){const q=this.value.toLowerCase();$(".gceo-report-grid a").each(function(){$(this).toggle($(this).text().toLowerCase().includes(q));});});
	}
	render();
};
