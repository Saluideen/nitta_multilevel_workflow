# Copyright (c) 2023, Sajith K and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class NittaWorkflow(Document):
	pass

@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_department_role(doctype, txt, searchfield, start, page_len, filters):

	roles= frappe.db.sql("""
	SELECT r.role FROM `tabNitta User Role` r WHERE r.departmentfunction = %(departmentfunction)s OR r.departmentfunction = 'All' GROUP BY r.role
	;
		""".format(**{
				'key': searchfield
			}), {
			'txt': "%{}%".format(txt),
			'_txt': txt.replace("%", ""),
			'start': start,
			'page_len': page_len,
			'departmentfunction':filters['departmentfunction'],
			'division':filters['division']
			
		})

	return roles