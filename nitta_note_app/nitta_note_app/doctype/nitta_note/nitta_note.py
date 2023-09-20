# Copyright (c) 2023, Sajith K and contributors
# For license information, please see license.txt

import frappe
import PyPDF2
import json
from datetime import date,datetime,timezone
from frappe.model.document import Document
from frappe.desk.form.assign_to import add as add_assignment
from frappe.share import add as add_share
from frappe.utils import get_url_to_form
from frappe.utils.pdf import get_pdf
from frappe.utils.file_manager import get_file,download_file,get_file_path,write_file,save_file
from PyPDF2 import PdfMerger
from frappe.utils import get_site_path

class NittaNote(Document):
	
	is_send_mail=False
		
	def before_insert(self):
		# set initiated by
		self.initiated_by=frappe.session.user
		#clear attachments when duplicating file
		for attachment in self.other_attachments:
			attachment.attachment=None
			attachment.file_name=None
		for vendor in self.vendors:
			vendor.document=None
			vendor.file_name=None
		self.technical_comparison_file_name=None
		self.technical_comparison_file=None
		self.commercial_comparison_file_name=None
		self.commercial_comparison_file=None
		
	def before_save(self):
		doc= self.get_doc_before_save()
		if(doc):
			if self.status=="Draft":
				#set workflow on change
				if(float(doc.expected_amount)!=float(self.expected_amount)
				or doc.expense_category !=self.expense_category
				or doc.budget_provision !=self.budget_provision
				or doc.item_category !=self.item_category
				or doc.is_pre_approval_note !=self.is_pre_approval_note
				or doc.departmentfunction !=self.departmentfunction ):
					self.work_flow_name=None
					self.approval_flow=[]
					self.set_workflow()
				#change note no on change
				if(doc.division != self.division
				or doc.departmentfunction != self.departmentfunction
				or doc.financial_year != self.financial_year
				or doc.expense_category != self.expense_category):
					self.set_note_no()
			elif doc.status=="Draft" and self.status!=doc.status:
					self.set_note_no()


	def after_insert(self):
		self.date=frappe.utils.today()
		self.set_workflow()
		# set note number
		self.set_note_no()
		self.save()

	def on_trash(self):
		# prevent delete
		if self.status!='Draft' and frappe.session.user!='Administrator':
			frappe.throw("Cannot delete initiated Note")

	def on_update(self):		
		if not self.status=="Draft":

			# add changes to time line
			self.add_changes_to_timeline()

			# update approval flow
			self.update_workflow()

			# Doc Share For Next Approver
			add_share(self.doctype, self.name, user=self.next_approval_by, read=1, write=1, submit=0, share=1, everyone=0, notify=0)

			# Doc Assign to
			is_exist_assign = frappe.db.exists('ToDo',{'reference_type':self.doctype,'reference_name':self.name,'allocated_to':self.next_approval_by})
			if not is_exist_assign and self.next_approval_by:
				add_assignment({"doctype": self.doctype, "name": self.name, "assign_to": [self.next_approval_by]})
				# Send mail
				self.is_send_mail=frappe.get_doc('Nitta Constant').enable_email_notifications
				if(self.is_send_mail):
					user_name = frappe.get_cached_value("User", frappe.session.user, "full_name")
					doc_link = get_url_to_form('Nitta Note',self.name)
					args={
					"message":user_name+" Requested to approve "+self.note_no +", Title:"+self.title+", Department:"+self.departmentfunction,
					"doc_link":{"doc_link":doc_link,'name':self.note_no},
					"header":['Request for Approval of '+self.note_no, 'green'],
					}
					frappe.sendmail(template='assign_to',subject="Request for Approval of "+self.note_no,recipients=[self.next_approval_by],args=args)
		self.reload()

	def update_assigned_date(self,index):
		approval_flow=frappe.get_all("Nitta Approval Flow",filters={'parent':self.name,'parenttype':self.doctype,'idx':index})
		if len(approval_flow)>0:
			approval=frappe.get_doc("Nitta Approval Flow",approval_flow[0].name)
			approval.assigned_date=frappe.utils.now()
			approval.save()
		else:
			frappe.throw("Assign Approval flow")

	def update_updated_date(self,index):
		approval_flow=frappe.get_all("Nitta Approval Flow",filters={'parent':self.name,'parenttype':self.doctype,'idx':index})
		if len(approval_flow)>0:
			approval=frappe.get_doc("Nitta Approval Flow",approval_flow[0].name)
			approval.updated_date=frappe.utils.now()
			approval.save()
		else:
			frappe.throw("Assign Approval flow")
	
	def set_workflow(self):
		entity_type=get_entity_type(self.departmentfunction)
		workflows=frappe.get_all('Nitta Workflow',filters={
				'expense_category': self.expense_category,
				'budget_provision': self.budget_provision,
				'item_category': self.item_category,
				'lower_limit': ['<=', self.expected_amount],
				'upper_limit': ['>=', self.expected_amount],
				'is_pre_approval': self.is_pre_approval_note,
				'note_type': 'Financial',
				'entity_type':['IN',[entity_type,'All']]
				},
				fields=['name'])

		if len(workflows)>0:
			self.work_flow_name=workflows[0].name
			# Get workflow transitions
			workflow_transitions=get_workflow_transition(self.work_flow_name,self.division,self.departmentfunction)
			for transition in workflow_transitions['data']:
				self.append("approval_flow", {'role': transition['role'],
					'nitta_user': transition['name'],
					'department': transition['department'],
					'status':'Pending',
					'alert_in_days':transition['alert_in_days'],
					'is_editable':False
					})
			# Get copyto transitions
			copy_to= get_copy_to(self.work_flow_name,self.division,self.departmentfunction)
			for copy in copy_to['data']:
				self.append('copy_to',{
					'role': copy['role'],
					'nitta_user': copy['name'],
					'department': copy['department']
					})

	def update_workflow(self):
		self.current_approval_level=0
		self.max_approval_level=0
		self.status="Initiated"
		self.rejected=False
		self.modify=False
		current_user_index =0
		for index,approval in enumerate(self.approval_flow,start=1):
			self.max_approval_level+=1
			if approval.status=='Approved':
				self.current_approval_level+=1
			if approval.status=='Rejected':
				self.rejected=True
			if approval.status=='Modify':
				self.modify=True
			if approval.nitta_user ==frappe.session.user and approval.status!='Pending':
				current_user_index=index
			
		if self.current_approval_level==0:
			self.next_approval_by=self.approval_flow[self.current_approval_level].nitta_user
			if self.rejected:
				# self.status='Level '+str(self.current_approval_level+1)+' Rejected'
				approval_flow = self.approval_flow[self.current_approval_level]
				self.status='Level '+str(self.current_approval_level+1)+'('+approval_flow.department+'-' +approval_flow.role +')'+' Rejected'
			if self.modify:
				approval_flow = self.approval_flow[self.current_approval_level]
				self.status='Level '+str(self.current_approval_level+1)+'('+approval_flow.department+'-' +approval_flow.role +')'+' Modify Request'
		
		elif self.current_approval_level<self.max_approval_level:
			self.next_approval_by=self.approval_flow[self.current_approval_level].nitta_user
			if not self.rejected and not self.modify:
				self.update_assigned_date(self.current_approval_level+1)
				if current_user_index>0:
					self.update_updated_date(current_user_index)	
				# self.status='Level '+str(self.current_approval_level)+' Approved'
				approval_flow = self.approval_flow[self.current_approval_level-1]
				self.status='Level '+str(self.current_approval_level)+'('+approval_flow.department+'-' +approval_flow.role +')'+' Approved'
			elif self.modify:
				# self.status='Level '+str(self.current_approval_level+1)+' Modify Request'
				approval_flow = self.approval_flow[self.current_approval_level]
				self.status='Level '+str(self.current_approval_level+1)+'('+approval_flow.department+'-' +approval_flow.role +')'+' Modify Request'
				if current_user_index>0:
					self.update_updated_date(current_user_index)	
			else:
				# self.status='Level '+str(self.current_approval_level+1)+' Rejected'
				approval_flow = self.approval_flow[self.current_approval_level]
				self.status='Level '+str(self.current_approval_level+1)+'('+approval_flow.department+'-' +approval_flow.role +')'+' Rejected'
				if current_user_index>0:
					self.update_updated_date(current_user_index)	

		elif self.current_approval_level==self.max_approval_level:
			self.next_approval_by=None
			self.status='Final Approved'
			self.send_final_mail()
			if current_user_index>0:
				self.update_updated_date(current_user_index)	
			# Copy Sharing
			is_copy_to = frappe.get_all('Nitta CC',filters={'parent':self.name,'parenttype':self.doctype},fields=['nitta_user'])
			for copy in is_copy_to:
				# Doc Share For CC user
				add_share(self.doctype, self.name, user=copy.nitta_user, read=1, write=1, submit=0, share=1, everyone=0, notify=0)
		
		# set assign date for first user in approval flow
		if self.status=='Initiated':
			self.update_assigned_date(1)
		
		self.db_update()

	def send_final_mail(self):
		self.is_send_mail=frappe.get_doc('Nitta Constant').enable_email_notifications
		if(self.is_send_mail):
			args={"message":"Note "+self.note_no+" is Approved"}
			frappe.sendmail(template='noteapproved',subject="Note Approved",recipients=self.initiated_by,args=args,header=['Note Approved', 'green'],)

	def add_changes_to_timeline(self):
		old_doc = self.get_doc_before_save()
		# Checking the changed fields to add the timeline
		if old_doc:
			if old_doc.nature_of_expenditure != self.nature_of_expenditure:
				self.add_comment('Edit', 'changed value of <span>Nature of Expenditure</span> from <b>{0}</b> to <b>{1}<b>'.format(old_doc.nature_of_expenditure,self.nature_of_expenditure))
			if old_doc.proposal_type != self.proposal_type:
				self.add_comment('Edit', 'changed value of <span>Proposal Type</span> from <b>{0}</b> to <b>{1}<b>'.format(old_doc.proposal_type,self.proposal_type))
			if old_doc.sn_in_budget_sheet != self.sn_in_budget_sheet:
				self.add_comment('Edit', 'changed value of <span>SN in budget Sheet</span> from <b>{0}</b> to <b>{1}<b>'.format(old_doc.sn_in_budget_sheet,self.sn_in_budget_sheet))
			if old_doc.gl_account_no != self.gl_account_no:
				self.add_comment('Edit', 'changed value of <span>GL Account No.</span> from <b>{0}</b> to <b>{1}<b>'.format(old_doc.gl_account_no,self.gl_account_no))
			if old_doc.title != self.title:
				self.add_comment('Edit', 'changed value of <span>Title</span> from <b>{0}</b> to <b>{1}<b>'.format(old_doc.title,self.title))
			if str(old_doc.project_start_date) != str(self.project_start_date):
				self.add_comment('Edit', 'changed value of <span>Project Start Date</span> from <b>{0}</b> to <b>{1}<b>'.format(old_doc.project_start_date,self.project_start_date))
			if str(old_doc.project_completion_date) != str(self.project_completion_date):
				self.add_comment('Edit', 'changed value of <span>Project Completion Date</span> from <b>{0}</b> to <b>{1}<b>'.format(old_doc.project_completion_date,self.project_completion_date))
			if old_doc.revised_amount != self.revised_amount:
				self.add_comment('Edit', 'changed value of <span>Revised Amount</span> from <b>{0}</b> to <b>{1}<b>'.format(old_doc.revised_amount,self.revised_amount))
			if old_doc.background != self.background:
				self.add_comment('Edit', 'changed value of <span>Background</span>')
			if old_doc.details_of_the_proposal != self.details_of_the_proposal:
				self.add_comment('Edit', 'changed value of <span>Details of the proposal</span>')
			if old_doc.recommendation != self.recommendation:
				self.add_comment('Edit', 'changed value of <span>Benefits and Recommendation</span>')

			# Checking the reference note table changes
			if old_doc.ref != self.ref:
				# set the changes of reference note table fields
				for i in range(len(old_doc.ref) if len(old_doc.ref)<=len(self.ref) else len(self.ref)):
					edit_comment='changed value of Reference Note in <b>Row {0}</b>'.format(i+1)
					is_edited=False
					if self.ref[i].name1 != old_doc.ref[i].name1:
						edit_comment+=' Name from <b>{0}</b> to <b>{1}</b>'.format(old_doc.ref[i].name1,self.ref[i].name1)
						is_edited=True
					if self.ref[i].refnote != old_doc.ref[i].refnote:
						edit_comment+=' Ref.Note from <b>{0}</b> to <b>{1}</b>'.format(old_doc.ref[i].refnote,self.ref[i].refnote)
						is_edited=True
					if(is_edited):
						self.add_comment('Edit', edit_comment)

				# checking of the reference note insertion or deletion
				if len(self.ref) > len(old_doc.ref):
					for i in range(len(old_doc.ref),len(self.ref)):
						self.add_comment('Edit', 'Added new <b>Row {0}</b> to <span>Reference Note</span> with Name:<b>{1}</b>, Ref.Note:<b>{2}</b>'.format(i+1,self.ref[i].name1,self.ref[i].refnote))
				else:
					for i in range(len(self.ref),len(old_doc.ref)):
						self.add_comment('Edit', 'Deleted <b>Row {0}</b> from <span>Reference Note</span> with Name:<b>{1}</b>, Ref.Note:<b>{2}</b>'.format(i+1,old_doc.ref[i].name1,old_doc.ref[i].refnote))

			# Checking the Cost Estimate table changes
			if old_doc.cost_estimate != self.cost_estimate:
				# set the changes of Cost Estimate table fields
				for i in range(len(old_doc.cost_estimate) if len(old_doc.cost_estimate)<=len(self.cost_estimate) else len(self.cost_estimate)):
					edit_comment='changed value of Cost Estimate in <b>Row {0}</b>'.format(i+1)
					is_edited=False
					if self.cost_estimate[i].title != old_doc.cost_estimate[i].title:
						edit_comment+=' Title from <b>{0}</b> to <b>{1}</b>'.format(old_doc.cost_estimate[i].title,self.cost_estimate[i].title)
						is_edited=True
					if self.cost_estimate[i].quantity != old_doc.cost_estimate[i].quantity:
						edit_comment+=' Quantity from <b>{0}</b> to <b>{1}</b>'.format(old_doc.cost_estimate[i].quantity,self.cost_estimate[i].quantity)
						is_edited=True
					if self.cost_estimate[i].price != old_doc.cost_estimate[i].price:
						edit_comment+=' Price from <b>{0}</b> to <b>{1}</b>'.format(old_doc.cost_estimate[i].price,self.cost_estimate[i].price)
						is_edited=True
					if self.cost_estimate[i].amount != old_doc.cost_estimate[i].amount:
						edit_comment+=' Amount from <b>{0}</b> to <b>{1}</b>'.format(old_doc.cost_estimate[i].amount,self.cost_estimate[i].amount)
						is_edited=True
					if(is_edited):
						self.add_comment('Edit', edit_comment)

				# checking of the Cost Estimate  insertion or deletion
				if len(self.cost_estimate) > len(old_doc.cost_estimate):
					for i in range(len(old_doc.cost_estimate),len(self.cost_estimate)):
						self.add_comment('Edit', 'Added new <b>Row {0}</b> to <span>Cost Estimate</span> with Title:<b>{1}</b>, Quantity:<b>{2}</b>, Price:<b>{3}</b>, Amount:<b>{4}</b>'.format(i+1,self.cost_estimate[i].title,self.cost_estimate[i].quantity,self.cost_estimate[i].price,self.cost_estimate[i].amount))
				else:
					for i in range(len(self.cost_estimate),len(old_doc.cost_estimate)):
						self.add_comment('Edit', 'Deleted <b>Row {0}</b> from <span>Cost Estimate</span> with Title:<b>{1}</b>, Quantity:<b>{2}</b>, Price:<b>{3}</b>, Amount:<b>{4}</b>'.format(i+1,old_doc.cost_estimate[i].title,old_doc.cost_estimate[i].quantity,old_doc.cost_estimate[i].price,old_doc.cost_estimate[i].amount))
				

			# Checking the Technical Comparision table changes
			if old_doc.technical_comparision != self.technical_comparision:
				# set the changes of Technical Comparision table fields
				for i in range(len(old_doc.technical_comparision) if len(old_doc.technical_comparision)<=len(self.technical_comparision) else len(self.technical_comparision)):
					edit_comment='changed value of Technical Comparison in <b>Row {0}</b>'.format(i+1)
					is_edited=False
					if self.technical_comparision[i].parameter != old_doc.technical_comparision[i].parameter:
						edit_comment+=' Parameter from <b>{0}</b> to <b>{1}</b>'.format(old_doc.technical_comparision[i].parameter,self.technical_comparision[i].parameter)
						is_edited=True
					if self.technical_comparision[i].vendor != old_doc.technical_comparision[i].vendor:
						edit_comment+=' Vendor from <b>{0}</b> to <b>{1}</b>'.format(old_doc.technical_comparision[i].vendor,self.technical_comparision[i].vendor)
						is_edited=True
					if self.technical_comparision[i].data != old_doc.technical_comparision[i].data:
						edit_comment+=' Data from <b>{0}</b> to <b>{1}</b>'.format(old_doc.technical_comparision[i].data,self.technical_comparision[i].data)
						is_edited=True
					if(is_edited):
						self.add_comment('Edit', edit_comment)
	
				# checking of the Technical Comparision  insertion or deletion
				if len(self.technical_comparision) > len(old_doc.technical_comparision):
					for i in range(len(old_doc.technical_comparision),len(self.technical_comparision)):
						self.add_comment('Edit', 'Added new <b>Row {0}</b> to <span>Technical Comparision</span> with Parameter:<b>{1}</b>, Vendor:<b>{2}</b>, Data:<b>{3}</b>'.format(i+1,self.technical_comparision[i].parameter,self.technical_comparision[i].vendor,self.technical_comparision[i].data))
				else:
					for i in range(len(self.technical_comparision),len(old_doc.technical_comparision)):
						self.add_comment('Edit', 'Deleted <b>Row {0}</b> to <span>Technical Comparision</span> with Parameter:<b>{1}</b>, Vendor:<b>{2}</b>, Data:<b>{3}</b>'.format(i+1,old_doc.technical_comparision[i].parameter,old_doc.technical_comparision[i].vendor,old_doc.technical_comparision[i].data))
				

			# Checking the Vendors table changes
			if old_doc.vendors != self.vendors:
				# set the changes of Vendors table fields
				for i in range(len(old_doc.vendors) if len(old_doc.vendors)<=len(self.vendors) else len(self.vendors)):
					edit_comment='changed value of Commercial Comparison in <b>Row {0}</b>'.format(i+1)
					is_edited=False
					if self.vendors[i].vendor_name != old_doc.vendors[i].vendor_name:
						edit_comment+=' Vendor Name from <b>{0}</b> to <b>{1}</b>'.format(old_doc.vendors[i].vendor_name,self.vendors[i].vendor_name)
						is_edited=True
					if self.vendors[i].amount != old_doc.vendors[i].amount:
						edit_comment+=' Amount from <b>{0}</b> to <b>{1}</b>'.format(old_doc.vendors[i].amount,self.vendors[i].amount)
						is_edited=True
					if self.vendors[i].is_selected_vendor != old_doc.vendors[i].is_selected_vendor:
						edit_comment+=' Tick Approved Vendor from <b>{0}</b> to <b>{1}</b>'.format(old_doc.vendors[i].is_selected_vendor,self.vendors[i].is_selected_vendor)
						is_edited=True
					if self.vendors[i].document != old_doc.vendors[i].document:
						edit_comment+=' File from <b>{0}</b> to <b>{1}</b>'.format(old_doc.vendors[i].document,self.vendors[i].document)
						is_edited=True
					if(is_edited):
						self.add_comment('Edit', edit_comment)
							
				# checking of the Vendors insertion or deletion
				if len(self.vendors) > len(old_doc.vendors):
					for i in range(len(old_doc.vendors),len(self.vendors)):
						self.add_comment('Edit', 'Added new <b>Row {0}</b> to <span>Commercial Comparision</span> with Vendor Name:<b>{1}</b>, Amount:<b>{2}</b>, Tick Approved Vendor:<b>{3}</b>, File:<b>{4}</b>'.format(i+1,self.vendors[i].vendor_name,self.vendors[i].amount,self.vendors[i].is_selected_vendor,self.vendors[i].document))
				else:
					for i in range(len(self.vendors),len(old_doc.vendors)):
						self.add_comment('Edit', 'Deleted <b>Row {0}</b> to <span>Commercial Comparision</span> with Vendor Name:<b>{1}</b>, Amount:<b>{2}</b>, Tick Approved Vendor:<b>{3}</b>, File:<b>{4}</b>'.format(i+1,old_doc.vendors[i].vendor_name,old_doc.vendors[i].amount,old_doc.vendors[i].is_selected_vendor,old_doc.vendors[i].document))


			# Checking the Other Attachments table changes
			if old_doc.other_attachments != self.other_attachments:
				# set the changes of Other Attachments table fields
				for i in range(len(old_doc.other_attachments) if len(old_doc.other_attachments)<=len(self.other_attachments) else len(self.other_attachments)):
					edit_comment='changed value of Other Attachments in <b>Row {0}</b>'.format(i+1)
					is_edited=False
					if self.other_attachments[i].name1 != old_doc.other_attachments[i].name1:
						edit_comment+=' Name from <b>{0}</b> to <b>{1}</b>'.format(old_doc.other_attachments[i].name1,self.other_attachments[i].name1)
						is_edited=True
					if self.other_attachments[i].attachment != old_doc.other_attachments[i].attachment:
						edit_comment+=' Attachment from <b>{0}</b> to <b>{1}</b>'.format(old_doc.other_attachments[i].attachment,self.other_attachments[i].attachment)
						is_edited=True
					if(is_edited):
						self.add_comment('Edit', edit_comment)	

				# checking of the Other Attachments insertion or deletion
				if len(self.other_attachments) > len(old_doc.other_attachments):
					for i in range(len(old_doc.other_attachments),len(self.other_attachments)):
						self.add_comment('Edit', 'Added new <b>Row {0}</b> to <span>Other Attachments</span> with Name:<b>{1}</b>, Attachments:<b>{2}</b>'.format(i+1,self.other_attachments[i].name1,self.other_attachments[i].attachment))
				else:
					for i in range(len(self.other_attachments),len(old_doc.other_attachments)):
						self.add_comment('Edit', 'Deleted <b>Row {0}</b> to <span>Other Attachments</span> with Name:<b>{1}</b>, Attachments:<b>{2}</b>'.format(i+1,old_doc.other_attachments[i].name1,old_doc.other_attachments[i].attachment))
	  

	def set_note_no(self):
		# Get Division Code
		division=frappe.get_doc("Division",self.division)
		# Get Department Code
		department=frappe.get_doc("Department and Function",self.departmentfunction)
		# Get Expense category Code
		expense_category=frappe.get_doc("Expense Category",self.expense_category)
		# Get count
		count=frappe.db.count(self.doctype,{'division':self.division,'departmentfunction':self.departmentfunction,'expense_category':self.expense_category,'financial_year':self.financial_year,'status':['!=','Draft']})
		if not self.status == 'Draft':
			self.note_no='F'+'/'+division.short_name+'/'+department.short_name+'/'+expense_category.short_name+'/'+self.financial_year+'/'+str(count+1)
		else:
			self.note_no='F'+'/'+division.short_name+'/'+department.short_name+'/'+expense_category.short_name+'/'+self.financial_year+'/'+self.name

# get divisions assigned to logged in user
@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_divisions(doctype, txt, searchfield, start, page_len, filters):

	if isinstance(filters, str):
		try:
			filters = json.loads(filters)
		except:
			pass

	# check if all divisions are allowed
	all_division=frappe.db.exists("Nitta User Role",{"parent":filters["user"],"division":"Corporate"})

    # get all divisions
	# if filters["user"] in ('Administrator','System Manager') or all_division:
	if filters["user"] in ('Administrator','System Manager'):
		return frappe.db.sql("""
			SELECT d.name
			FROM `tabDivision` d
			WHERE d.name LIKE %(txt)s
			ORDER BY
				IF(LOCATE(%(_txt)s, d.name), LOCATE(%(_txt)s, d.name), 99999),
				d.name
			
		""".format(**{
				'key': searchfield
			}), {
			'txt': "%{}%".format(txt),
			'_txt': txt.replace("%", ""),
			'start': start,
			'page_len': page_len,
			'user':filters["user"]
		})
	else:
		# get assigned divisions
		return frappe.db.sql("""
			SELECT d.name
			FROM `tabDivision` d
			inner join `tabNitta User Role` ur on ur.division=d.name and ur.parent=%(user)s
			WHERE d.name LIKE %(txt)s
			GROUP BY
			    d.name
			ORDER BY
				IF(LOCATE(%(_txt)s, d.name), LOCATE(%(_txt)s, d.name), 99999),
				d.name
			
		""".format(**{
				'key': searchfield
			}), {
			'txt': "%{}%".format(txt),
			'_txt': txt.replace("%", ""),
			'start': start,
			'page_len': page_len,
			'user':filters["user"]
		})


# get department/function assigned to logged in user
@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_department(doctype, txt, searchfield, start, page_len, filters):
	if isinstance(filters, str):
		try:
			filters = json.loads(filters)
		except:
			pass
	# check if all department are allowed
	all_department=frappe.db.exists("Nitta User Role",{"parent":filters["user"],"division":filters["division"],"departmentfunction":"All"})

    # get all department
	if filters["user"] in ('Administrator','System Manager') or all_department:
		return frappe.db.sql("""
			SELECT d.name
			FROM `tabDepartment and Function` d
			WHERE d.name LIKE %(txt)s
			AND d.name !='All'
			ORDER BY
				IF(LOCATE(%(_txt)s, d.name), LOCATE(%(_txt)s, d.name), 99999),
				d.name
			LIMIT %(start)s, %(page_len)s
		""".format(**{
				'key': searchfield
			}), {
			'txt': "%{}%".format(txt),
			'_txt': txt.replace("%", ""),
			'start': start,
			'page_len': page_len,
			'user':filters["user"]
		})
	else:
		# get assigned divisions
		return frappe.db.sql("""
			SELECT d.name
			FROM `tabDepartment and Function` d
			inner join `tabNitta User Role` ur on ur.departmentfunction=d.name and ur.parent=%(user)s and ur.division=%(division)s
			WHERE d.name LIKE %(txt)s
			GROUP BY
			    d.name
			ORDER BY
				IF(LOCATE(%(_txt)s, d.name), LOCATE(%(_txt)s, d.name), 99999),
				d.name
			LIMIT %(start)s, %(page_len)s
		""".format(**{
				'key': searchfield
			}), {
			'txt': "%{}%".format(txt),
			'_txt': txt.replace("%", ""),
			'start': start,
			'page_len': page_len,
			'user':filters["user"],
			'division':filters["division"]
		})



@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_department_role(doctype, txt, searchfield, start, page_len, filters):
	roles= frappe.db.sql("""
	SELECT r.role FROM `tabNitta User Role` r WHERE (r.division = %(division)s OR r.division = 'Corporate') 
	AND (r.departmentfunction = %(departmentfunction)s OR r.departmentfunction = 'All') 
	AND r.role LIKE %(txt)s
	GROUP BY r.role
	
	ORDER BY
		IF(LOCATE(%(_txt)s, r.role), LOCATE(%(_txt)s, r.role), 99999),
			r.role
		LIMIT %(start)s, %(page_len)s
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


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_nitta_user(doctype, txt, searchfield, start, page_len, filters):
	user= frappe.db.sql("""
	SELECT u.name FROM `tabNitta User` u INNER JOIN `tabNitta User Role` r on r.parent = u.name WHERE  r.role = %(role)s
	AND (r.division = %(division)s OR r.division = 'Corporate') AND (r.departmentfunction = %(departmentfunction)s OR r.departmentfunction = 'All')
	AND u.name LIKE %(txt)s
	GROUP BY u.name
	ORDER BY
		IF(LOCATE(%(_txt)s, u.name), LOCATE(%(_txt)s, u.name), 99999),
			u.name
		LIMIT %(start)s, %(page_len)s
	
	;
		""".format(**{
				'key': searchfield
			}), {
			'txt': "%{}%".format(txt),
			'_txt': txt.replace("%", ""),
			'start': start,
			'page_len': page_len,
			'role':filters["role"],
			'departmentfunction':filters['departmentfunction'],
			'division':filters['division']
		})

	return user

@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def pre_approval_ref_no_filter(doctype, txt, searchfield, start, page_len, filters):
	pre_approval_ref_no= frappe.db.sql("""SELECT name FROM `tabNitta Note` 
								WHERE name NOT IN(SELECT pre_approval_ref_no  FROM `tabNitta Note` WHERE pre_approval_ref_no IS NOT Null) AND status= 'Final Approved' AND is_pre_approval_note =true;
		""".format(**{
				'key': searchfield
			}), {
			'txt': "%{}%".format(txt),
			'_txt': txt.replace("%", ""),
			'start': start,
			'page_len': page_len,
			
		})

	return pre_approval_ref_no

	
@frappe.whitelist()
def get_workflow_transition(work_flow_name,division,note_department):
	transitions = frappe.get_all('Nitta Workflow Transition',filters={'parent':work_flow_name,'parenttype':'Nitta Workflow'},fields=['role','department','alert_in_days'],order_by='idx')	
	data=[]
	for transition in transitions:
		department = []
		if(transition.department=='From Note'):
			department.append(note_department)
		else:
			department.append(transition.department)
		
		user_role = frappe.db.sql("""
			SELECT r.role,u.name,r.departmentfunction as department,r.division  FROM `tabNitta User` u INNER JOIN `tabNitta User Role` r ON r.parent=u.name 
			WHERE (r.division IN (%(division)s) OR r.division='Corporate') AND (r.departmentfunction IN (%(department)s) OR r.departmentfunction='All') AND r.role IN (%(role)s) 
			""",values={'division':division,'department':department,'role':transition.role},as_dict=1)
		# If count of user is more than one filter appropriate users based on division and depratment
		if len(user_role)==1:
			data.append({'role':user_role[0].role,'name':user_role[0].name,'department':user_role[0].department,'alert_in_days':transition.alert_in_days})
		else:
			f_user = list(filter(lambda x:((x.department==transition.department or x.department==note_department) and x.division==division),user_role))
			if(len(f_user)>0):
				data.append({'role':f_user[0].role,'name':f_user[0].name,'department':f_user[0].department,'alert_in_days':transition.alert_in_days})
			else:
				f_user = list(filter(lambda x:(x.department=="All" and x.division==division),user_role))
				if(len(f_user)>0):
					data.append({'role':f_user[0].role,'name':f_user[0].name,'department':f_user[0].department,'alert_in_days':transition.alert_in_days})
				else:
					f_user = list(filter(lambda x:(x.department=="All" and x.division=="Corporate"),user_role))
					if(len(f_user)>0):
						data.append({'role':f_user[0].role,'name':f_user[0].name,'department':f_user[0].department,'alert_in_days':transition.alert_in_days})
		
	return {'Status':True,'data':data}

@frappe.whitelist()
def get_copy_to(work_flow_name,division,note_department):
	transitions = frappe.get_all('Nitta Copy To',filters={'parent':work_flow_name,'parenttype':'Nitta Workflow'},fields=['role','department'],order_by='idx')	
	data=[]
	for transition in transitions:
		department = []
		if(transition.department=='From Note'):
			department.append(note_department)
		else:
			department.append(transition.department)
		user_role = frappe.db.sql("""
			SELECT r.role,u.name,r.departmentfunction as department,division  FROM `tabNitta User` u INNER JOIN `tabNitta User Role` r ON r.parent=u.name
			WHERE (r.division IN (%(division)s) OR r.division='Corporate') AND (r.departmentfunction IN (%(department)s) OR r.departmentfunction='All') AND r.role IN (%(role)s) 
			""",values={'division':division,'department':department,'role':transition.role},as_dict=1)
			# If count of user is more than one filter appropriate users based on division and depratment
		if len(user_role)==1:
			data.append({'role':user_role[0].role,'name':user_role[0].name,'department':user_role[0].department,'alert_in_days':transition.alert_in_days})
		else:
			f_user = list(filter(lambda x:((x.department==transition.department or x.department==note_department) and x.division==division),user_role))
			if(len(f_user)>0):
				data.append({'role':f_user[0].role,'name':f_user[0].name,'department':f_user[0].department,'alert_in_days':transition.alert_in_days})
			else:
				f_user = list(filter(lambda x:(x.department=="All" and x.division==division),user_role))
				if(len(f_user)>0):
					data.append({'role':f_user[0].role,'name':f_user[0].name,'department':f_user[0].department,'alert_in_days':transition.alert_in_days})
				else:
					f_user = list(filter(lambda x:(x.department=="All" and x.division=="Corporate"),user_role))
					if(len(f_user)>0):
						data.append({'role':f_user[0].role,'name':f_user[0].name,'department':f_user[0].department,'alert_in_days':transition.alert_in_days})
		
	return {'Status':True,'data':data}


@frappe.whitelist()
def get_gl_details(name,note_name):
	details=frappe.db.sql("""
	SELECT description,budget_amount- COALESCE((SELECT SUM(CASE WHEN revised_amount >0 THEN revised_amount ELSE expected_amount END) FROM `tabNitta Note` WHERE status !='Draft' AND status NOT LIKE CONCAT(\'%%\','Rejected',\'%%\')  AND gl_account_no=%(name)s AND name != %(note_name)s),0) as budget_amount
	FROM `tabRevenue Expense` WHERE name=%(name)s
	""",values={'name':name,'note_name':note_name},as_dict=1)
	return {'Status':True,'data':details}
	
@frappe.whitelist()
def capex_expense_details(name,note_name):
	details=frappe.db.sql("""
	SELECT project,amount- COALESCE((SELECT SUM(CASE WHEN revised_amount >0 THEN revised_amount ELSE expected_amount END) FROM `tabNitta Note` WHERE status !='Draft' AND status NOT LIKE CONCAT(\'%%\','Rejected',\'%%\')  AND sn_in_budget_sheet=%(name)s AND name != %(note_name)s),0) as amount
	 FROM `tabCapex Expense` WHERE name=%(name)s
	""",values={'name':name,'note_name':note_name},as_dict=1)
	return {'Status':True,'data':details}

# mail scheduled to call daily (in hooks)
@frappe.whitelist()
def sendMail():
	users_list = frappe.db.sql("""SELECT next_approval_by,note.name as doc_name,note.note_no as note_no FROM `tabNitta Note` note INNER JOIN `tabNitta Approval Flow` flow ON flow.parent=note.name  WHERE flow.status='Pending'  AND note.status !='Draft' AND DATE_ADD(DATE(assigned_date) ,INTERVAL alert_in_days DAY) <=CURRENT_DATE()   """,as_dict=1)
	
	check_user=[]
	for user in users_list:
		is_checked = user['next_approval_by'] in check_user
		
		if(not is_checked):		
			res = list(filter(lambda x: (x.next_approval_by==user['next_approval_by']),users_list))
			check_user.append(user['next_approval_by'])
			doc_links=[]
			for r in res:
				doc_link = get_url_to_form('Nitta Note',r['doc_name'])
				doc_links.append({"doc_link":doc_link,'name':r['note_no']})

			self.is_send_mail=frappe.get_doc('Nitta Constant').enable_email_notifications
			if(self.is_send_mail):
				args={
				"message":"You have some pending note for validation",
				"doc_links":doc_links,
				}
				frappe.sendmail(template='remainder',subject="Note Remainder",recipients=user['next_approval_by'],args=args,header=['Note Remainder', 'green'],)

@frappe.whitelist()	
def get_entity_type(departmentfunction):
	entity_type = frappe.db.get_all('Department and Function',filters={'name1':departmentfunction},fields=['entity_type'])
	return entity_type[0].entity_type

@frappe.whitelist()	
def save_internal_order_no(name,internal_order_no):
	frappe.db.set_value('Nitta Note',name,{
		'internal_order_no':internal_order_no
	})

@frappe.whitelist()	
def change_status_to_cancel(name):
	frappe.db.set_value('Nitta Note',name,{
		'status':'Cancelled'
	})	
	
@frappe.whitelist()
def remove_file_backgroud(files):
    if isinstance(files, str):
        files = json.loads(files)
    frappe.enqueue(remove_file, queue='long', files=files)

def remove_file(files):
    for file in files:
        frappe.delete_doc("File", file)
	

def get_attached_files(doctype,docname):
	nitta_note = frappe.get_doc(doctype,docname)
	file_names=[]

	# Other Attachment
	for attachment in nitta_note.other_attachments:
		if(attachment.file_name):
			file_names.append(attachment.file_name)

	# Commercial Comparison Files (vendor quotations)
	for attachment in nitta_note.vendors:
		if(attachment.file_name):
			file_names.append(attachment.file_name)

	# Technical Comparison file
	if nitta_note.technical_comparison_file_name:
		file_names.append(nitta_note.technical_comparison_file_name)

	# Commercial Comparison file
	if nitta_note.commercial_comparison_file_name:
		file_names.append(nitta_note.commercial_comparison_file_name)

	return file_names
	
@frappe.whitelist()
def remove_unused_files(doctype,docname):
	# Get attached files
	file_names=get_attached_files(doctype,docname)

	# Get unattached files
	unattached_files = frappe.get_all("File",
		filters={
			"attached_to_doctype": doctype,
			"attached_to_name": docname,
			"name":["not in",file_names],
			"is_private":1
		},
		pluck='name'
		)
	
	if unattached_files:
		# Delete the attached files
		remove_file_backgroud(unattached_files)

@frappe.whitelist()
def download_pdf(doctype,docname):	
	
	files=[]

	# Creating and save Print format to public files folder
	html = frappe.get_print(doctype, docname, 'Nitta Note Format', doc=None,)
	pdf = get_pdf(html)
	res = write_file(pdf,docname+'_print.pdf',is_private=0)
	files.append(res)

	# Get attached file names
	file_names=get_attached_files(doctype,docname)
	
	# Get file urls
	file_urls=frappe.get_all("File",
		filters={"name":["IN",file_names]},
		fields=['file_url'],
		pluck='file_url'
		)
	
	# Get file from file url 
	for file_url in file_urls:
		files.append(
			get_file_path(file_url)
			)
		
	# Merging
	merger = PdfMerger()
	for file in files:
		merger.append(file)
	save_file_name ='files/'+docname+'.pdf'
	merger.write(get_site_path()+'/public/'+save_file_name)
	merger.close()

	return save_file_name