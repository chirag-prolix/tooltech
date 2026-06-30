import frappe
from frappe import _


def execute(filters=None):
	columns = get_columns()
	data = get_data(filters)
	chart = get_chart_data(data)
	report_summary = get_report_summary(data)
	return columns, data, None, chart, report_summary


def get_columns():
	return [
		{
			"fieldname": "inspection",
			"label": _("Inspection"),
			"fieldtype": "Link",
			"options": "Quality Inspection",
			"width": 140,
		},
		{
			"fieldname": "inspection_date",
			"label": _("Date"),
			"fieldtype": "Date",
			"width": 110,
		},
		{
			"fieldname": "item_code",
			"label": _("Item Code"),
			"fieldtype": "Link",
			"options": "Item",
			"width": 120,
		},
		{
			"fieldname": "workstation",
			"label": _("Workstation"),
			"fieldtype": "Link",
			"options": "Workstation",
			"width": 120,
		},
		{
			"fieldname": "parameter",
			"label": _("Parameter"),
			"fieldtype": "Data",
			"width": 140,
		},
		{
			"fieldname": "sample_size",
			"label": _("Sample Size (n)"),
			"fieldtype": "Int",
			"width": 110,
		},
		{
			"fieldname": "x_bar",
			"label": _("Mean (X-bar)"),
			"fieldtype": "Float",
			"precision": 3,
			"width": 110,
		},
		{
			"fieldname": "r_val",
			"label": _("Range (R)"),
			"fieldtype": "Float",
			"precision": 3,
			"width": 110,
		},
		{
			"fieldname": "ucl_x",
			"label": _("UCL (X-bar)"),
			"fieldtype": "Float",
			"precision": 3,
			"width": 110,
		},
		{
			"fieldname": "lcl_x",
			"label": _("LCL (X-bar)"),
			"fieldtype": "Float",
			"precision": 3,
			"width": 110,
		},
		{
			"fieldname": "ucl_r",
			"label": _("UCL (R)"),
			"fieldtype": "Float",
			"precision": 3,
			"width": 110,
		},
		{
			"fieldname": "lcl_r",
			"label": _("LCL (R)"),
			"fieldtype": "Float",
			"precision": 3,
			"width": 110,
		},
	]


def get_data(filters):
	if not filters:
		return []

	# Build filters conditions
	conditions = []
	values = {}

	if filters.get("item_code"):
		conditions.append("qi.item_code = %(item_code)s")
		values["item_code"] = filters.get("item_code")

	if filters.get("workstation"):
		conditions.append("qi.custom_machine = %(workstation)s")
		values["workstation"] = filters.get("workstation")

	if filters.get("from_date"):
		conditions.append("qi.inspection_date >= %(from_date)s")
		values["from_date"] = filters.get("from_date")

	if filters.get("to_date"):
		conditions.append("qi.inspection_date <= %(to_date)s")
		values["to_date"] = filters.get("to_date")

	where_clause = " AND ".join(conditions) if conditions else "1=1"

	# Get quality inspections matching filters
	inspections = frappe.db.sql(
		f"""
		SELECT
			qi.name,
			qi.inspection_date,
			qi.item_code,
			qi.custom_machine as workstation
		FROM
			`tabQuality Inspection` qi
		WHERE
			qi.docstatus = 1 AND {where_clause}
		ORDER BY
			qi.inspection_date ASC, qi.creation ASC
		""",
		values,
		as_dict=1,
	)

	if not inspections:
		return []

	inspection_names = [r.name for r in inspections]

	# Get inspection readings for the selected parameter
	reading_conditions = ["parent IN %(inspection_names)s"]
	reading_values = {"inspection_names": inspection_names}

	if filters.get("parameter"):
		reading_conditions.append("specification = %(parameter)s")
		reading_values["parameter"] = filters.get("parameter")

	reading_where = " AND ".join(reading_conditions)

	# Fetch all readings
	readings = frappe.db.sql(
		f"""
		SELECT
			parent,
			specification,
			reading_1, reading_2, reading_3, reading_4, reading_5,
			reading_6, reading_7, reading_8, reading_9, reading_10
		FROM
			`tabQuality Inspection Reading`
		WHERE
			{reading_where}
		""",
		reading_values,
		as_dict=1,
	)

	# Map readings to inspections
	readings_map = {}
	for r in readings:
		# Extract non-empty numeric readings
		vals = []
		for i in range(1, 11):
			val = r.get(f"reading_{i}")
			if val is not None and val != "":
				try:
					vals.append(float(val))
				except (ValueError, TypeError):
					pass
		if vals:
			readings_map[r.parent] = {
				"parameter": r.specification,
				"vals": vals,
			}

	# Compute subgroup statistics
	data = []
	for qi in inspections:
		reading = readings_map.get(qi.name)
		if not reading:
			continue

		vals = reading["vals"]
		n = len(vals)
		if n < 2:
			continue  # Range requires at least 2 readings

		x_bar = sum(vals) / n
		r_val = max(vals) - min(vals)

		data.append(
			{
				"inspection": qi.name,
				"inspection_date": qi.inspection_date,
				"item_code": qi.item_code,
				"workstation": qi.workstation,
				"parameter": reading["parameter"],
				"sample_size": n,
				"x_bar": x_bar,
				"r_val": r_val,
				# Limits will be updated below
				"ucl_x": 0.0,
				"lcl_x": 0.0,
				"ucl_r": 0.0,
				"lcl_r": 0.0,
			}
		)

	if not data:
		return []

	# Standard control limit constants for n=2 to 10
	spc_constants = {
		2: {"A2": 1.880, "D3": 0.0, "D4": 3.267},
		3: {"A2": 1.023, "D3": 0.0, "D4": 2.574},
		4: {"A2": 0.729, "D3": 0.0, "D4": 2.282},
		5: {"A2": 0.577, "D3": 0.0, "D4": 2.114},
		6: {"A2": 0.482, "D3": 0.0, "D4": 2.004},
		7: {"A2": 0.419, "D3": 0.076, "D4": 1.924},
		8: {"A2": 0.373, "D3": 0.136, "D4": 1.864},
		9: {"A2": 0.337, "D3": 0.184, "D4": 1.816},
		10: {"A2": 0.308, "D3": 0.223, "D4": 1.777},
	}

	# Calculate Overall Statistics
	total_x_bar = sum(row["x_bar"] for row in data)
	total_r = sum(row["r_val"] for row in data)
	k = len(data)

	double_x_bar = total_x_bar / k
	r_bar = total_r / k

	# Default to subgroup size of the first item, or 5 if invalid
	avg_n = int(round(sum(row["sample_size"] for row in data) / k))
	constants = spc_constants.get(avg_n, spc_constants[5])

	A2 = constants["A2"]
	D3 = constants["D3"]
	D4 = constants["D4"]

	# Compute limits
	ucl_x = double_x_bar + (A2 * r_bar)
	lcl_x = max(double_x_bar - (A2 * r_bar), 0.0)
	ucl_r = D4 * r_bar
	lcl_r = D3 * r_bar

	# Update rows
	for row in data:
		row["ucl_x"] = ucl_x
		row["lcl_x"] = lcl_x
		row["ucl_r"] = ucl_r
		row["lcl_r"] = lcl_r
		row["double_x_bar"] = double_x_bar
		row["r_bar"] = r_bar

	return data


def get_chart_data(data):
	if not data:
		return None

	labels = [row["inspection"] for row in data]
	x_bar_values = [row["x_bar"] for row in data]
	ucl_x_values = [row["ucl_x"] for row in data]
	lcl_x_values = [row["lcl_x"] for row in data]
	cl_x_values = [row["double_x_bar"] for row in data]

	return {
		"data": {
			"labels": labels,
			"datasets": [
				{"name": _("Mean (X-bar)"), "values": x_bar_values},
				{"name": _("UCL"), "values": ucl_x_values},
				{"name": _("CL"), "values": cl_x_values},
				{"name": _("LCL"), "values": lcl_x_values},
			],
		},
		"type": "line",
		"colors": ["#1f77b4", "#d62728", "#2ca02c", "#ff7f0e"],
	}


def get_report_summary(data):
	if not data:
		return []

	first_row = data[0]
	double_x_bar = first_row.get("double_x_bar", 0.0)
	r_bar = first_row.get("r_bar", 0.0)

	# Count out-of-control points
	x_out = 0
	r_out = 0
	for row in data:
		if row["x_bar"] > row["ucl_x"] or row["x_bar"] < row["lcl_x"]:
			x_out += 1
		if row["r_val"] > row["ucl_r"] or row["r_val"] < row["lcl_r"]:
			r_out += 1

	return [
		{
			"value": round(double_x_bar, 3),
			"indicator": "Blue",
			"label": _("Process Mean (X-double-bar)"),
		},
		{
			"value": round(r_bar, 3),
			"indicator": "Green",
			"label": _("Average Range (R-bar)"),
		},
		{
			"value": x_out,
			"indicator": "Red" if x_out > 0 else "Green",
			"label": _("X-bar Out of Control Points"),
		},
		{
			"value": r_out,
			"indicator": "Red" if r_out > 0 else "Green",
			"label": _("R Out of Control Points"),
		},
	]
