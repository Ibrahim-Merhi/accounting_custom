import frappe


PRIVILEGED = {
	"System Manager", "Accounts Manager", "Finance Officer", "Treasurer",
	"Association President", "CEO",
}


def _roles(user=None):
	return set(frappe.get_roles(user or frappe.session.user))


def _collectors(user=None):
	return frappe.get_all(
		"Collector Profile", filters={"user": user or frappe.session.user, "active": 1}, pluck="name"
	)


def donation_query(user=None):
	if _roles(user) & PRIVILEGED:
		return None
	collectors = _collectors(user)
	return "1=0" if not collectors else f"`tabDonation Entry`.`collector` in ({', '.join(frappe.db.escape(value) for value in collectors)})"


def donation_permission(doc, user=None, permission_type=None):
	if _roles(user) & PRIVILEGED:
		return True
	return bool(doc.collector and doc.collector in _collectors(user))


def handover_query(user=None):
	if _roles(user) & PRIVILEGED:
		return None
	collectors = _collectors(user)
	return "1=0" if not collectors else f"`tabCollector Handover`.`collector` in ({', '.join(frappe.db.escape(value) for value in collectors)})"


def handover_permission(doc, user=None, permission_type=None):
	if _roles(user) & PRIVILEGED:
		return True
	return bool(doc.collector and doc.collector in _collectors(user))


def payment_memo_query(user=None):
	user = user or frappe.session.user
	roles = _roles(user)
	if roles & PRIVILEGED:
		return None
	conditions = [f"`tabPayment Memo`.`requested_by`={frappe.db.escape(user)}"]
	if "Responsible Manager" in roles:
		conditions.append(f"`tabPayment Memo`.`responsible_manager`={frappe.db.escape(user)}")
	if "HR Coordinator" in roles:
		conditions.append("`tabPayment Memo`.`payment_type`='Salary Advance'")
	return "(" + " or ".join(conditions) + ")"


def payment_memo_permission(doc, user=None, permission_type=None):
	user = user or frappe.session.user
	roles = _roles(user)
	if roles & PRIVILEGED:
		return True
	if "Responsible Manager" in roles and doc.responsible_manager == user:
		return True
	if "HR Coordinator" in roles and doc.payment_type == "Salary Advance":
		return True
	return doc.requested_by == user
