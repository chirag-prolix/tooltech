import frappe

def run():
    print_format_name = "Parts Rejection Report"
    report_query = """
SELECT
    CAST(ROW_NUMBER() OVER (ORDER BY COALESCE(qi.custom_rejection_date, qi.report_date) DESC, qi.creation DESC) AS CHAR) AS "SL#:Data:60",
    qi.custom_prs_no AS "PRS No:Data:120",
    qi.custom_order_code AS "Order Code:Data:120",
    qi.item_name AS "Description:Data:180",
    item.custom_drawing_number AS "Drawing Number:Data:160",
    COALESCE(qi.custom_rejection_date, qi.report_date) AS "Rejection Date:Date:120",
    qi.custom_process_rejected_in AS "Rejected In:Link/Operation:140",
    qi.custom_process_identified_in AS "Identified In:Link/Operation:140",
    qi.custom_issue_description AS "Issue:Small Text:220",
    IFNULL(qi.custom_rejected_qty, 0) AS "Qty:Float:90",
    qi.custom_disposition AS "Remarks:Data:140",
    qi.custom_responsible_person AS "Responsible:Link/Employee:150"
FROM
    `tabQuality Inspection` qi
LEFT JOIN
    `tabItem` item ON item.name = qi.item_code
WHERE
    qi.docstatus = 1
    AND (
        qi.status = 'Rejected'
        OR IFNULL(qi.custom_rejected_qty, 0) > 0
        OR IFNULL(qi.custom_disposition, '') != ''
    )
    AND COALESCE(qi.custom_rejection_date, qi.report_date) >= %(from_date)s
    AND COALESCE(qi.custom_rejection_date, qi.report_date) <= %(to_date)s
    AND (
        %(disposition)s = 'All'
        OR qi.custom_disposition = %(disposition)s
    )
ORDER BY
    COALESCE(qi.custom_rejection_date, qi.report_date) DESC,
    qi.creation DESC
"""
    report_filters = [
        {
            "default": "Today",
            "fieldname": "from_date",
            "fieldtype": "Date",
            "label": "From Date",
            "mandatory": 1,
        },
        {
            "default": "Today",
            "fieldname": "to_date",
            "fieldtype": "Date",
            "label": "To Date",
            "mandatory": 1,
        },
        {
            "default": "All",
            "fieldname": "disposition",
            "fieldtype": "Select",
            "label": "Disposition",
            "mandatory": 0,
            "options": "All\nReject\nRework\nDeviation",
        },
    ]

    if frappe.db.exists("Report", print_format_name):
        report = frappe.get_doc("Report", print_format_name)
        report.query = report_query
        report.set("filters", [])
        for report_filter in report_filters:
            report.append("filters", report_filter)
        report.save(ignore_permissions=True)
        print(f"Updated Report: {print_format_name}")
    
    html = """<div class="parts-rejection-report">
    <div class="report-header">
        <div class="header-left">
            <div class="company-name">TOOLTECH INDUSTRIES</div>
            <div class="report-title">PARTS REJECTION REPORT</div>
        </div>
        <div class="header-right">
            <div class="total-qty-label">TOTAL REJECTED QTY</div>
            <div class="total-qty-value">
                {% var total_qty = 0; %}
                {% if (data && data.length) { %}
                    {% for (var i=0; i < data.length; i++) { %}
                        {% var row = data[i]; %}
                        {% if (!row.is_total_row) { %}
                            {% total_qty += parseFloat(row.qty) || 0; %}
                        {% } %}
                    {% } %}
                {% } %}
                {{ total_qty.toFixed(3) }}
            </div>
        </div>
    </div>

    {% if (filters) { %}
    <div class="report-filters">
        <span class="filter-item"><strong>From Date:</strong> {{ frappe.datetime.str_to_user(filters.from_date) }}</span>
        <span class="filter-item"><strong>To Date:</strong> {{ frappe.datetime.str_to_user(filters.to_date) }}</span>
        <span class="filter-item"><strong>Disposition:</strong> {{ filters.disposition || "All" }}</span>
    </div>
    {% } %}
    
    <table class="report-table">
        <thead>
            <tr>
                <th style="width: 4%;">SL. NO.</th>
                <th style="width: 8%;">PRS NO.</th>
                <th style="width: 8%;">ORDER CODE</th>
                <th style="width: 14%;">DESCRIPTION</th>
                <th style="width: 10%;">DRAWING NO.</th>
                <th style="width: 8%;">REJECTION DATE</th>
                <th style="width: 8%;">REJECTED IN</th>
                <th style="width: 8%;">IDENTIFIED IN</th>
                <th style="width: 12%;">ISSUE DESCRIPTION</th>
                <th style="width: 4%;">QTY</th>
                <th style="width: 8%;">REMARKS</th>
                <th style="width: 8%;">RESPONSIBLE</th>
            </tr>
        </thead>
        <tbody>
            {% if (data && data.length) { %}
                {% for (var i=0; i < data.length; i++) { %}
                    {% var row = data[i]; %}
                    {% if (!row.is_total_row) { %}
                    <tr>
                        <td class="text-center">{{ row["sl#"] || (i + 1) }}</td>
                        <td class="text-center">{{ row.prs_no || "" }}</td>
                        <td class="text-center">{{ row.order_code || "" }}</td>
                        <td class="text-left">{{ row.description || "" }}</td>
                        <td class="text-center">{{ row.drawing_number || "" }}</td>
                        <td class="text-center">
                            {% if (row.rejection_date) { %}
                                {{ frappe.datetime.str_to_user(row.rejection_date) }}
                            {% } %}
                        </td>
                        <td class="text-center">{{ row.rejected_in || "" }}</td>
                        <td class="text-center">{{ row.identified_in || "" }}</td>
                        <td class="text-left">{{ row.issue || "" }}</td>
                        <td class="text-right">{{ parseFloat(row.qty || 0).toFixed(3) }}</td>
                        <td class="text-center">{{ row.remarks || "" }}</td>
                        <td class="text-center">{{ row.responsible || "" }}</td>
                    </tr>
                    {% } %}
                {% } %}
            {% } else { %}
                <tr>
                    <td colspan="12" class="text-center text-muted">No records found</td>
                </tr>
            {% } %}
        </tbody>
    </table>
</div>"""
 
    css = """.parts-rejection-report {
    font-family: "Helvetica Neue", Helvetica, Arial, sans-serif;
    font-size: 11px;
    color: #1e293b;
    padding: 20px;
    background-color: #ffffff;
}

.report-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-end;
    margin-bottom: 15px;
    border-bottom: 2px solid #e2e8f0;
    padding-bottom: 15px;
}

.header-left {
    display: flex;
    flex-direction: column;
}

.company-name {
    font-size: 16px;
    font-weight: 700;
    color: #dc2626;
    letter-spacing: 0.5px;
}

.report-title {
    font-size: 22px;
    font-weight: 700;
    color: #1e3a8a;
    margin-top: 4px;
    letter-spacing: 0.5px;
}

.header-right {
    display: flex;
    flex-direction: column;
    align-items: flex-end;
}

.total-qty-label {
    font-size: 9px;
    font-weight: 600;
    color: #64748b;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    margin-bottom: 4px;
}

.total-qty-value {
    background-color: #fef2f2;
    color: #991b1b;
    font-size: 18px;
    font-weight: 700;
    padding: 6px 16px;
    border-radius: 6px;
    border: 1px solid #fee2e2;
    min-width: 80px;
    text-align: center;
}

.report-filters {
    margin-bottom: 20px;
    font-size: 11px;
    color: #475569;
    background-color: #f8fafc;
    padding: 10px 15px;
    border-radius: 6px;
    border: 1px solid #e2e8f0;
    display: flex;
    gap: 20px;
}

.filter-item strong {
    color: #1e293b;
}

.report-table {
    width: 100%;
    border-collapse: collapse;
    margin-top: 10px;
}

.report-table th {
    background-color: #f1f5f9;
    color: #334155;
    font-weight: 600;
    text-transform: uppercase;
    font-size: 9px;
    border: 1px solid #cbd5e1;
    padding: 8px 6px;
    text-align: center;
    vertical-align: middle;
}

.report-table td {
    border: 1px solid #cbd5e1;
    padding: 6px 4px;
    vertical-align: middle;
    font-size: 10px;
}

.text-center {
    text-align: center;
}

.text-left {
    text-align: left;
}

.text-right {
    text-align: right;
    font-variant-numeric: tabular-nums;
}

.text-muted {
    color: #64748b;
}"""

    if frappe.db.exists("Print Format", print_format_name):
        doc = frappe.get_doc("Print Format", print_format_name)
        doc.html = html
        doc.css = css
        doc.print_format_for = "Report"
        doc.report = print_format_name
        doc.print_format_type = "JS"
        doc.custom_format = 1
        doc.standard = "No"
        doc.module = "Tooltech"
        doc.save(ignore_permissions=True)
        print(f"Updated Print Format: {print_format_name}")
    else:
        doc = frappe.get_doc({
            "doctype": "Print Format",
            "name": print_format_name,
            "print_format_for": "Report",
            "report": print_format_name,
            "print_format_type": "JS",
            "html": html,
            "css": css,
            "custom_format": 1,
            "standard": "No",
            "module": "Tooltech"
        })
        doc.insert(ignore_permissions=True)
        print(f"Created Print Format: {print_format_name}")
    
    # Update only the roles that can access the Parts Rejection Report.
    report_roles = ["Quality Inspector", "Production Head", "Production Incharge"]
    for d in frappe.get_all(
        "Custom DocPerm",
        filters={"parent": "Quality Inspection", "role": ["in", report_roles]},
    ):
        doc = frappe.get_doc("Custom DocPerm", d.name)
        if not doc.print:
            doc.print = 1
            doc.save(ignore_permissions=True)
            print(f"Updated print permission for Custom DocPerm: {doc.role}")
            
    frappe.db.commit()

if __name__ == "__main__":
    run()
