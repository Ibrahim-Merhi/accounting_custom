frappe.ui.form.on("Accounting User Guide", {
	refresh(frm) {
		frappe.require("/assets/accounting_custom/css/accounting_user_guide.css", () => {
			render_accounting_guide(frm);
		});
	},
});

function render_accounting_guide(frm) {
	frm.disable_save();
	const image_root = "/assets/accounting_custom/images/accounting_guide";
	const html = `
		<div class="accounting-guide">
			<section class="ag-hero">
				<div class="ag-hero-copy">
					<div class="ag-eyebrow">ACCOUNTING OPERATIONS HANDBOOK</div>
					<h1>Work confidently from receipt to financial review</h1>
					<p>A practical guide for collectors, accountants, finance officers, treasurers, managers, and executive reviewers.</p>
					<div class="ag-actions">
						<button class="btn btn-primary" data-route="workspace">Open Accounting Workspace</button>
						<button class="btn btn-default" data-scroll="quick-start">Start with the daily checklist</button>
					</div>
				</div>
				<div class="ag-hero-stat"><strong>11</strong><span>management reports</span><strong>8</strong><span>guided work areas</span></div>
			</section>

			<nav class="ag-tabs" aria-label="Guide audience">
				<button class="active" data-audience="all">Complete guide</button>
				<button data-audience="accountant">Accountant</button>
				<button data-audience="manager">Manager & approver</button>
				<label class="ag-search"><span>⌕</span><input type="search" placeholder="Search this guide…" aria-label="Search this guide"></label>
			</nav>

			<section class="ag-section" id="quick-start" data-audience="all accountant manager" data-search="daily checklist start accounting workspace">
				<div class="ag-section-heading"><span>01</span><div><h2>Daily starting point</h2><p>Use this sequence before entering or approving transactions.</p></div></div>
				<div class="ag-checklist">
					<div><b>1</b><span><strong>Confirm context</strong>Check Company, Branch, Posting Date, currency, and cost center.</span></div>
					<div><b>2</b><span><strong>Choose the correct process</strong>Donation Entry for receipts, Accounting Payment Entry for direct payments, or Payment Memo when approval is required.</span></div>
					<div><b>3</b><span><strong>Attach evidence</strong>Add donor, invoice, project, notes, and supporting documents before requesting approval.</span></div>
					<div><b>4</b><span><strong>Review before submit</strong>Check accounts, currency totals, approval status, and cost-center allocation.</span></div>
				</div>
			</section>

			<section class="ag-section" data-audience="all accountant manager" data-search="workspace navigation sections reports masters">
				<div class="ag-section-heading"><span>02</span><div><h2>Find the accounting tools</h2><p>Open Accounting from the sidebar, then scroll to Accounting Operations and Reports.</p></div></div>
				<figure class="ag-shot"><img src="${image_root}/accounting-workspace-overview.png" alt="Annotated Accounting workspace navigation"><figcaption>The standard ERPNext Accounting workspace contains all custom workflows and reports in dedicated cards.</figcaption></figure>
			</section>

			<section class="ag-section" data-audience="all accountant" data-search="donation donor collector custody receipt handover">
				<div class="ag-section-heading"><span>03</span><div><h2>Donation and collector lifecycle</h2><p>Record the receipt immediately and keep collected funds in custody until treasury handover.</p></div></div>
				<div class="ag-flow">
					<div><em>1</em><strong>Collector Profile</strong><small>Confirm default donor and currency custody accounts.</small><button data-doctype="Collector Profile">Open</button></div>
					<i>→</i><div><em>2</em><strong>Donation Entry</strong><small>Create or select donor, project, currency, and receipt details.</small><button data-doctype="Donation Entry">Open</button></div>
					<i>→</i><div><em>3</em><strong>Finance Approval</strong><small>Finance reviews before the receipt can be submitted.</small></div>
					<i>→</i><div><em>4</em><strong>Collector Handover</strong><small>Treasury receives the funds and transfers custody to cash or bank.</small><button data-doctype="Collector Handover">Open</button></div>
				</div>
				<div class="ag-note"><strong>Quick donor:</strong> Name and phone are enough. The collector’s configured donor account is assigned automatically. Never create a duplicate donor when the same name and phone already exist.</div>
			</section>

			<section class="ag-section" data-audience="all accountant" data-search="payment beneficiary employee supplier institution company party finance approval">
				<div class="ag-section-heading"><span>04</span><div><h2>Accounting Payment Entry</h2><p>Use for balanced direct payments after selecting the correct mode of payment and allocation.</p></div></div>
				<figure class="ag-shot"><img src="${image_root}/accounting-payment-entry.png" alt="Annotated Accounting Payment Entry"><figcaption>Beneficiaries are available across companies. Employees and Institutions use their Company; Suppliers use the Company in their Accounts table.</figcaption></figure>
				<div class="ag-rule-grid">
					<div><strong>Beneficiary</strong><span>Global—no company filter.</span></div><div><strong>Employee</strong><span>Filtered by employee company.</span></div>
					<div><strong>Supplier</strong><span>Filtered through Supplier → Accounts.</span></div><div><strong>Institution</strong><span>Filtered by Institution Company.</span></div>
				</div>
			</section>

			<section class="ag-section" data-audience="all accountant manager" data-search="payment memo salary advance custody closure approval manager president treasurer ceo">
				<div class="ag-section-heading"><span>05</span><div><h2>Payment Memo and custody</h2><p>Select the memo type carefully—the approval route and accounting treatment depend on it.</p></div></div>
				<div class="ag-cards">
					<article><span class="ag-tag">PAYMENT</span><h3>Normal payment</h3><p>Applicant → Responsible Manager → Finance → President → Treasurer.</p></article>
					<article><span class="ag-tag">CUSTODY</span><h3>Custody request</h3><p>Use when the applicant will later document how the advance was spent.</p></article>
					<article><span class="ag-tag">CLOSURE</span><h3>Custody closure</h3><p>Reference the original custody. The closure cannot exceed its outstanding amount.</p></article>
					<article><span class="ag-tag">SALARY</span><h3>Salary advance</h3><p>Employee → HR Coordinator → Manager → Finance → President → Treasurer.</p></article>
				</div>
				<button class="btn btn-default" data-doctype="Payment Memo">Open Payment Memo</button>
			</section>

			<section class="ag-section" data-audience="all accountant" data-search="payroll salary cost center allocation deductions monthly adjustment">
				<div class="ag-section-heading"><span>06</span><div><h2>Payroll preparation</h2><p>Finance controls allocations; HR records monthly deductions; executives review the register.</p></div></div>
				<div class="ag-table-wrap"><table><thead><tr><th>Task</th><th>Owner</th><th>Document</th><th>Control</th></tr></thead><tbody>
					<tr><td>Allocate salary</td><td>Finance</td><td><button data-doctype="Payroll Cost Center Allocation">Payroll Cost Center Allocation</button></td><td>Cost centers must total 100%.</td></tr>
					<tr><td>Monthly deductions</td><td>HR / Finance</td><td><button data-doctype="Employee Monthly Adjustment">Employee Monthly Adjustment</button></td><td>Creates submitted Additional Salary deductions.</td></tr>
					<tr><td>Salary register review</td><td>CEO / President</td><td><button data-doctype="Payroll Review">Payroll Review</button></td><td>Record comments, return, or approve.</td></tr>
				</tbody></table></div>
			</section>

			<section class="ag-section" data-audience="all manager" data-search="manager approve return reject comments controls review">
				<div class="ag-section-heading"><span>07</span><div><h2>Manager and approver controls</h2><p>Approval means the business purpose and accounting allocation have both been checked.</p></div></div>
				<div class="ag-manager-grid">
					<div><h3>Responsible Manager</h3><ul><li>Review only memos assigned to you.</li><li>Check purpose, project, invoice, and cost centers.</li><li>Return with a clear correction note when needed.</li></ul></div>
					<div><h3>Finance Officer</h3><ul><li>Verify company, accounts, currency, and exchange rate.</li><li>Select payment or custody account.</li><li>Approve only when supporting evidence is complete.</li></ul></div>
					<div><h3>President / Treasurer</h3><ul><li>Review earlier comments and final funding source.</li><li>Treasurer confirms execution and daily cash impact.</li><li>Reject only when the request must not continue.</li></ul></div>
				</div>
			</section>

			<section class="ag-section" data-audience="all accountant manager" data-search="reports daily weekly monthly donor collector approvals custody balance sheet cost center">
				<div class="ag-section-heading"><span>08</span><div><h2>Reports and when to use them</h2><p>Start with an operational report, then use weekly or monthly financial views for management review.</p></div></div>
				<div class="ag-report-grid">
					<button data-report="Daily Treasury Report"><strong>Daily Treasury</strong><span>Received and paid by currency.</span></button>
					<button data-report="Collector Collections"><strong>Collector Collections</strong><span>Collections by date and project.</span></button>
					<button data-report="Donor Donation History"><strong>Donor History</strong><span>Donations by donor and period.</span></button>
					<button data-report="Pending Accounting Approvals"><strong>Pending Approvals</strong><span>Documents waiting for action.</span></button>
					<button data-report="Open Custodies"><strong>Open Custodies</strong><span>Outstanding employee custody.</span></button>
					<button data-report="Weekly Cost Center Comparison"><strong>Weekly Cost Centers</strong><span>Previous versus current balance.</span></button>
					<button data-report="Weekly Cash Bank Comparison"><strong>Weekly Cash & Bank</strong><span>Liquidity movement comparison.</span></button>
					<button data-report="Monthly Cost Center Movement"><strong>Monthly Movement</strong><span>Opening, revenue, expense, ending.</span></button>
					<button data-report="Balance Sheet by Cost Center"><strong>BS by Cost Center</strong><span>Assets, liabilities, and equity.</span></button>
				</div>
			</section>

			<section class="ag-section" data-audience="all accountant manager" data-search="troubleshooting error query beneficiary company permission approval configuration">
				<div class="ag-section-heading"><span>09</span><div><h2>Troubleshooting</h2><p>Resolve configuration issues before changing transaction data.</p></div></div>
				<details><summary>No beneficiary or party appears</summary><p>Beneficiary is global. For Employee and Institution verify Company. For Supplier add a row for the company in Supplier → Accounts.</p></details>
				<details><summary>Collector cannot create a quick donor</summary><p>Create an active Collector Profile for the user and company, with a valid default donor account.</p></details>
				<details><summary>Donation or payment cannot be submitted</summary><p>Check approval status, required cost centers, company accounts, exchange rates, and supporting rows.</p></details>
				<details><summary>Custody closure amount is rejected</summary><p>The selected original custody must be submitted, use the same company and currency, and have enough outstanding balance.</p></details>
			</section>

			<footer class="ag-footer"><strong>Good accounting starts with complete evidence.</strong><span>When uncertain, return the document with a precise note—do not bypass the approval route.</span></footer>
			<div class="ag-empty" hidden>No guide topics match your search.</div>
		</div>`;

	frm.fields_dict.guide_content.$wrapper.html(html);
	const $guide = frm.fields_dict.guide_content.$wrapper.find(".accounting-guide");
	$guide.on("click", "[data-doctype]", (event) => frappe.set_route("List", event.currentTarget.dataset.doctype));
	$guide.on("click", "[data-report]", (event) => frappe.set_route("query-report", event.currentTarget.dataset.report));
	$guide.on("click", "[data-route='workspace']", () => frappe.set_route("Workspaces", "Accounting"));
	$guide.on("click", "[data-scroll]", (event) => document.getElementById(event.currentTarget.dataset.scroll)?.scrollIntoView({ behavior: "smooth" }));
	$guide.on("click", ".ag-tabs [data-audience]", function () {
		$guide.find(".ag-tabs [data-audience]").removeClass("active");
		$(this).addClass("active");
		filter_guide($guide);
	});
	$guide.find(".ag-search input").on("input", () => filter_guide($guide));
}

function filter_guide($guide) {
	const audience = $guide.find(".ag-tabs [data-audience].active").data("audience");
	const query = ($guide.find(".ag-search input").val() || "").trim().toLowerCase();
	let visible = 0;
	$guide.find(".ag-section").each(function () {
		const audiences = ($(this).data("audience") || "all").split(" ");
		const haystack = `${$(this).data("search") || ""} ${$(this).text()}`.toLowerCase();
		const show = (audience === "all" || audiences.includes(audience)) && (!query || haystack.includes(query));
		$(this).toggle(show);
		visible += show ? 1 : 0;
	});
	$guide.find(".ag-empty").prop("hidden", visible > 0);
}
