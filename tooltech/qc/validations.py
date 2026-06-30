import frappe


def _validate_linked_qc_gate(
	inspection: str | None,
	status: str | None,
	gate_label: str,
) -> None:
	"""Require both the gate status and linked Quality Inspection to be accepted."""
	if status != "Passed":
		frappe.throw(
			frappe._(
				"{0} QC is required for this Job Card but has not passed. "
				"Please complete the {0} QC Inspection before submitting."
			).format(gate_label),
			title=frappe._("QC Gate: {0}").format(gate_label),
		)

	if not inspection:
		frappe.throw(
			frappe._(
				"{0} QC is marked as passed, but no Quality Inspection is linked. "
				"Please link an accepted Quality Inspection before submitting."
			).format(gate_label),
			title=frappe._("QC Gate: {0}").format(gate_label),
		)

	qi = frappe.db.get_value(
		"Quality Inspection",
		inspection,
		["status", "docstatus"],
		as_dict=True,
	)
	if not qi or qi.status != "Accepted" or qi.docstatus != 1:
		frappe.throw(
			frappe._(
				"The linked {0} QC Inspection {1} must be submitted and Accepted "
				"before this Job Card can be submitted."
			).format(gate_label, inspection),
			title=frappe._("QC Gate: {0}").format(gate_label),
		)


def validate_qc_gate_on_job_card(doc: object, method: str) -> None:
	"""Block Job Card submission if pre- or post-QC is required but not passed.

	Hooked via doc_events → Job Card → before_submit.
	"""
	if getattr(doc, "custom_pre_qc_required", 0):
		_validate_linked_qc_gate(
			getattr(doc, "custom_pre_qc_inspection", None),
			getattr(doc, "custom_pre_qc_status", None),
			frappe._("Pre-Process"),
		)

	if getattr(doc, "custom_post_qc_required", 0):
		_validate_linked_qc_gate(
			getattr(doc, "custom_post_qc_inspection", None),
			getattr(doc, "custom_post_qc_status", None),
			frappe._("Post-Process"),
		)


def validate_qc_gate_on_purchase_receipt(doc: object, method: str) -> None:
	"""Block Purchase Receipt submission if QC is required but not passed.

	Hooked via doc_events → Purchase Receipt → before_submit.
	"""
	if not getattr(doc, "custom_qc_required", 0):
		return

	if not doc.custom_qc_inspection:
		frappe.throw(
			frappe._(
				"QC Inspection is mandatory before accepting this purchase. "
				"Please link a Quality Inspection."
			),
			title=frappe._("QC Gate: Purchase"),
		)

	qi_status = frappe.db.get_value("Quality Inspection", doc.custom_qc_inspection, "status")
	if qi_status != "Accepted":
		frappe.throw(
			frappe._(
				"The linked Quality Inspection {0} has status '{1}'. "
				"It must be 'Accepted' before this Purchase Receipt can be submitted."
			).format(doc.custom_qc_inspection, qi_status),
			title=frappe._("QC Gate: Purchase"),
		)

	doc.custom_qc_passed = 1


def calculate_rejection_totals(doc: object, method: str) -> None:
	"""Auto-calculate total rejected qty and accepted qty from rejection detail child table.

	Hooked via doc_events → Quality Inspection → validate.
	"""
	if not hasattr(doc, "custom_rejection_details"):
		return

	total_rejected = sum(
		(row.rejected_qty or 0) for row in (doc.custom_rejection_details or [])
	)
	doc.custom_total_rejected_qty = total_rejected

	batch_qty = doc.custom_batch_qty or 0
	doc.custom_accepted_qty = max(batch_qty - total_rejected, 0)

	# Validate that rejected qty does not exceed batch qty
	if batch_qty and total_rejected > batch_qty:
		frappe.throw(
			frappe._(
				"Total rejected qty ({0}) exceeds batch qty ({1}). "
				"Please correct the rejection details."
			).format(total_rejected, batch_qty),
			title=frappe._("Rejection Qty Mismatch"),
		)
