# Copyright (c) 2023, Sajith K and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class NittaRole(Document):
	def before_insert(self):
		role = frappe.new_doc('Role',self.name)
		role.role_name = self.name1
		role.save(ignore_permissions=True)