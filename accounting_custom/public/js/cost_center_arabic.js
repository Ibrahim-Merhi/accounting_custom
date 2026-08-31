frappe.ready(() => {
	if (frappe.boot.lang !== "ar") return;

	const maps = {
		Account: frappe.boot.account_arabic_names || {},
		Company: frappe.boot.company_arabic_names || {},
		"Cost Center": frappe.boot.cost_center_arabic_names || {},
	};
	const arabicName = (doctype, value) => maps[doctype]?.[value] || value;
	const standardLinkFormatter = frappe.form.formatters.Link;

	for (const doctype of Object.keys(maps)) {
		frappe.form.link_formatters[doctype] = (value) => arabicName(doctype, value);
	}

	frappe.form.formatters.Link = function (value, docfield, options, doc) {
		const doctype = docfield?._options || docfield?.options;
		if (maps[doctype] && options && (options.for_print || options.only_value)) {
			return arabicName(doctype, value);
		}
		return standardLinkFormatter(value, docfield, options, doc);
	};
});
