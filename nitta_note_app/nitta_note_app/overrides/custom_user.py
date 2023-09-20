# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt

import frappe
from frappe.core.doctype.user.user import User
from frappe.desk.notifications import clear_notifications
from frappe import STANDARD_USERS

class CustomUser(User):
	
	def on_update(self):
		super().on_update()
		# update Approval user on update
		doc=self.get_doc_before_save()
		if(doc and doc.full_name!=self.full_name):
			frappe.db.set_value('Nitta User',self.name, 'name1', self.full_name)
		if(doc and doc.enabled!=self.enabled):
			frappe.db.set_value('Nitta User',self.name, 'enabled', self.enabled)

	def after_rename(self, old_name, new_name, merge=False):
		# update email, name of Approval User
		super().after_rename(old_name, new_name, merge=False)
		if frappe.db.exists('Nitta User', old_name):	
			from frappe.model.rename_doc import rename_doc
			rename_doc('Nitta User', old_name, new_name,ignore_permissions=True, force=True, show_alert=False)