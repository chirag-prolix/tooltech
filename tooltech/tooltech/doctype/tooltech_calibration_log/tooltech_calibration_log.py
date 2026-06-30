import frappe
from frappe.model.document import Document


class TooltechCalibrationLog(Document):
	def validate(self) -> None:
		self.compute_next_calibration_date()

	def compute_next_calibration_date(self) -> None:
		"""Auto-compute the next calibration date from calibration_date + frequency."""
		if self.calibration_date and self.calibration_frequency_days and not self.next_calibration_date:
			self.next_calibration_date = frappe.utils.add_days(
				self.calibration_date, self.calibration_frequency_days
			)
