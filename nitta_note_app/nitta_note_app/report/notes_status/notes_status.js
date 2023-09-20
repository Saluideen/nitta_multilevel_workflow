// Copyright (c) 2023, Sajith K and contributors
// For license information, please see license.txt
/* eslint-disable */

// let current_year=new Date().getFullYear()
// let current_month=new Date().getMonth()+1
// let current_date=new Date().getDate()

frappe.query_reports["Notes Status"] = {
	"filters": [
		{
			fieldname: "note_type",
			label: __("Note Type"),
			fieldtype: "Select",
			options: ["All", "Financial", "Non Financial"],
		},
		{
			fieldname: "division",
			label: __("Division"),
			fieldtype: "Link",
			options: "Division",
		},
		{
			fieldname: "departmentfunction",
			label: __("Department"),
			fieldtype: "Link",
			options: "Department and Function",
		},
		{
			fieldname: "expense_category",
			label: __("Expense Category"),
			fieldtype: "Link",
			options: "Expense Category",
		},
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
			default: new Date()
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
			default: new Date()
		},
	]
};


// if (frappe.user_roles.find(n => n == 'Administrator')){
// frappe.query_reports["Attendance Report"]["filters"].push({
// 	"fieldname":"admin1",
// 	"label": __("Executive Admin1"),
// 	"fieldtype": "Link",
// 	"options":"Hybrid User"
// });
// }
