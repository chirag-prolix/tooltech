frappe.query_reports["SPC Control Chart"] = {
	filters: [
		{
			fieldname: "item_code",
			label: __("Item Code"),
			fieldtype: "Link",
			options: "Item",
			reqd: 1,
			on_change: function() {
				const item = frappe.query_report.get_filter_value("item_code");
				if (item) {
					frappe.call({
						method: "frappe.client.get_list",
						args: {
							doctype: "Quality Inspection",
							filters: { item_code: item, docstatus: 1 },
							fields: ["name"],
							limit: 100
						},
						callback: function(r) {
							if (r.message && r.message.length > 0) {
								const qi_names = r.message.map(d => d.name);
								frappe.call({
									method: "frappe.client.get_list",
									args: {
										doctype: "Quality Inspection Reading",
										filters: { parent: ["in", qi_names] },
										fields: ["specification"],
										distinct: 1
									},
									callback: function(res) {
										if (res.message) {
											const specs = [...new Set(res.message.map(d => d.specification))];
											const parameter_filter = frappe.query_report.get_filter("parameter");
											parameter_filter.df.options = specs.join("\n");
											parameter_filter.refresh();
											if (specs.length > 0) {
												frappe.query_report.set_filter_value("parameter", specs[0]);
											}
										}
									}
								});
							}
						}
					});
				}
			}
		},
		{
			fieldname: "parameter",
			label: __("Quality Parameter"),
			fieldtype: "Select",
			reqd: 1,
			options: []
		},
		{
			fieldname: "workstation",
			label: __("Workstation / Machine"),
			fieldtype: "Link",
			options: "Workstation"
		},
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
			default: frappe.datetime.add_months(frappe.datetime.get_today(), -3)
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
			default: frappe.datetime.get_today()
		}
	],

	onload: function(report) {
		// Custom rendering for double charts (X-bar and R chart)
		const original_onload = report.onload;
		
		// Style override to make it premium
		report.page.main.css({
			"background-color": "#f8f9fa",
			"padding": "15px"
		});
	},

	// custom rendering or layout can be customized here
	formatter: function(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		
		// Highlight out of control points in red/orange
		if (column.fieldname === "x_bar" && data) {
			if (data.x_bar > data.ucl_x || data.x_bar < data.lcl_x) {
				value = `<span style="color: #d62728; font-weight: bold;">${value} ⚠️</span>`;
			}
		}
		if (column.fieldname === "r_val" && data) {
			if (data.r_val > data.ucl_r || data.r_val < data.lcl_r) {
				value = `<span style="color: #ff7f0e; font-weight: bold;">${value} ⚠️</span>`;
			}
		}
		return value;
	}
};
