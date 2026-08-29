frappe.ui.form.on("Payroll Review", {
	refresh(frm) {
		if (frm.is_new()) return;
		const roles = frappe.user_roles || [];
		let actions = [];
		if (frm.doc.review_status === "Pending CEO" && (roles.includes("CEO") || roles.includes("System Manager"))) actions = ["Approve", "Return"];
		if (frm.doc.review_status === "Pending President" && (roles.includes("Association President") || roles.includes("System Manager"))) actions = ["Approve", "Return"];
		if (frm.doc.review_status === "Returned to Finance" && (roles.includes("Finance Officer") || roles.includes("System Manager"))) actions = ["Resubmit"];
		actions.forEach((label) => frm.add_custom_button(__(label), () => {
			frappe.call({
				method: "accounting_custom.accounting_custom.doctype.payroll_review.payroll_review.review",
				args: { name: frm.doc.name, action: label === "Resubmit" ? "Approve" : label },
				freeze: true,
				callback: () => frm.reload_doc(),
			});
		}, __("Review")));
	},
});
