# Copyright (c) 2023, Sajith K and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils.password import get_decrypted_password

class NittaUser(Document):
	def after_insert(self):
		pass
		

	def on_update(self):
		if not self.user:
			user = frappe.new_doc('User')
			user.email = self.email
			user.first_name = self.name1
			user.phone = self.phone
			user.send_welcome_email=False
			user.enabled=self.enabled
			user.new_password = self.get_password('password')
			user.append('roles',{'role':'Nitta User'})
			for role in self.roles:
				user.append('roles',{'role':role.role})
			inserted_user=user.insert(ignore_permissions=True)

			if(inserted_user):
				inserted_user.user_type='System User'
				inserted_user.module_profile='Nitta Module Profile'
				updated_user=inserted_user.save(ignore_permissions=True)
		
			self.user=inserted_user.name
			notification_settings = frappe.get_doc("Notification Settings",self.user)
			notification_settings.enable_email_notifications =False
			notification_settings.save(ignore_permissions=True)


			self.db_update()
		else:
			user = frappe.get_doc('User',self.user)
			user.first_name = self.name1
			user.phone = self.phone
			user.enabled=self.enabled
			user.new_password = self.get_password('password')
			user.roles=None
			user.append('roles',{'role':'Nitta User'})
			for role in self.roles:
				user.append('roles',{'role':role.role})
			updated_user=user.save(ignore_permissions=True)
			notification_settings = frappe.get_doc("Notification Settings",self.user)
			notification_settings.enable_email_notifications =False
			notification_settings.save(ignore_permissions=True)

	def after_rename(self, old_name, new_name, merge=False):	
		# update email, name of Approval User
		if frappe.db.exists("User", old_name):
			from frappe.model.rename_doc import rename_doc
			rename_doc("User", old_name, new_name,ignore_permissions=True, force=True, show_alert=False)