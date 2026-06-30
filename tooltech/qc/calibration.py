import frappe


def update_asset_calibration_status(doc: object, method: str) -> None:
	"""On Calibration Log submit, update the linked Asset's calibration fields.

	Hooked via doc_events → Tooltech Calibration Log → on_submit.
	"""
	if not doc.asset:
		return

	update_fields = {
		"custom_last_calibration_date": doc.calibration_date,
		"custom_next_calibration_date": doc.next_calibration_date,
	}

	# Update instrument status based on calibration result
	if doc.result == "Pass" or doc.result == "Adjusted":
		update_fields["custom_calibration_status"] = "Calibrated"
	elif doc.result == "Fail":
		update_fields["custom_calibration_status"] = "Due"

	# Copy the instrument status if it indicates scrapping
	if doc.instrument_status == "Scrapped":
		update_fields["custom_calibration_status"] = "Scrapped"

	# Attach the latest certificate
	if doc.certificate:
		update_fields["custom_latest_certificate"] = doc.certificate

	frappe.db.set_value("Asset", doc.asset, update_fields, update_modified=True)

	frappe.msgprint(
		frappe._(
			"Asset {0} calibration status updated to '{1}'."
		).format(doc.asset_name or doc.asset, update_fields.get("custom_calibration_status", "")),
		indicator="green",
		alert=True,
	)


def check_overdue_calibrations() -> None:
	"""Scheduled task to mark instruments as 'Overdue' when past their next calibration date.

	Can be added to scheduler_events → daily in hooks.py.
	"""
	today = frappe.utils.today()

	overdue_assets = frappe.get_all(
		"Asset",
		filters={
			"custom_is_inspection_instrument": 1,
			"custom_next_calibration_date": ["<", today],
			"custom_calibration_status": ["in", ["Calibrated", "Due"]],
		},
		pluck="name",
	)

	for asset_name in overdue_assets:
		frappe.db.set_value(
			"Asset", asset_name, "custom_calibration_status", "Overdue", update_modified=False
		)

	if overdue_assets:
		frappe.db.commit()
		frappe.logger().info(
			f"Marked {len(overdue_assets)} assets as calibration overdue: {overdue_assets}"
		)
