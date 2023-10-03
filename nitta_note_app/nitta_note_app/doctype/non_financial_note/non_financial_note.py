# Copyright (c) 2023, Sajith K and contributors
# For license information, please see license.txt

import frappe
import PyPDF2
import json
from datetime import date,datetime
from frappe.model.document import Document
from frappe.desk.form.assign_to import add as add_assignment
from frappe.share import add as add_share
from frappe.utils import get_url_to_form
from frappe.utils.pdf import get_pdf
from frappe.utils.file_manager import get_file,download_file,get_file_path,write_file,save_file
from PyPDF2 import PdfMerger
from PIL import Image
import os
from frappe.utils import get_site_path

class NonFinancialNote(Document):
	
	is_send_mail=False
	
	def before_insert(self):
		# set initiated by
		self.initiated_by=frappe.session.user
		#clear attachments when duplicating file
		for attachment in self.attachments:
			attachment.attachment=None
			attachment.file_name=None

	def before_save(self):
		doc= self.get_doc_before_save()
		if(doc):
			if self.status=="Draft":
				#set workflow on change
				if(doc.departmentfunction !=self.departmentfunction):
					self.work_flow_name=None
					self.approval_flow=[]
					self.set_workflow()
				#change note no on change
				if(doc.division != self.division
				or doc.departmentfunction != self.departmentfunction
				or doc.financial_year != self.financial_year):
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
					doc_link = get_url_to_form('Non Financial Note',self.name)
					args={
					"message":user_name+" Requested to approve "+self.note_no+", Title:"+self.title+", Department:"+self.departmentfunction,
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
+
*********
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
				'note_type': 'Non Financial',
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
			if old_doc.title != self.title:
				self.add_comment('Edit', 'changed value of <span>Title</span> from <b>{0}</b> to <b>{1}<b>'.format(old_doc.title,self.title))
			if old_doc.background != self.background:
				self.add_comment('Edit', 'changed value of <span>Background</span>')
			if old_doc.details_of_the_proposal != self.details_of_the_proposal:
				self.add_comment('Edit', 'changed value of <span>Proposal Details</span>')
			if old_doc.benefits != self.benefits:
				self.add_comment('Edit', 'changed value of <span>Benefits And Recommendation</span>')

			# Checking the Attachments table changes
			if old_doc.attachments != self.attachments:
				# set the changes of Attachments table fields
				for i in range(len(old_doc.attachments) if len(old_doc.attachments)<=len(self.attachments) else len(self.attachments)):
					edit_comment='changed value of Attachments in <b>Row {0}</b>'.format(i+1)
					is_edited=False
					if self.attachments[i].name1 != old_doc.attachments[i].name1:
						edit_comment+=' Name from <b>{0}</b> to <b>{1}</b>'.format(old_doc.attachments[i].name1,self.attachments[i].name1)
						is_edited=True
					if self.attachments[i].attachment != old_doc.attachments[i].attachment:
						edit_comment+=' Attachment from <b>{0}</b> to <b>{1}</b>'.format(old_doc.attachments[i].attachment,self.attachments[i].attachment)
						is_edited=True
					if(is_edited):
						self.add_comment('Edit', edit_comment)	

				# checking of the Attachments insertion or deletion
				if len(self.attachments) > len(old_doc.attachments):
					for i in range(len(old_doc.attachments),len(self.attachments)):
						self.add_comment('Edit', 'Added new <b>Row {0}</b> to <span>Attachments</span> with Name:<b>{1}</b>, Attachments:<b>{2}</b>'.format(i+1,self.attachments[i].name1,self.attachments[i].attachment))
				else:
					for i in range(len(self.attachments),len(old_doc.attachments)):
						self.add_comment('Edit', 'Deleted <b>Row {0}</b> to <span>Attachments</span> with Name:<b>{1}</b>, Attachments:<b>{2}</b>'.format(i+1,old_doc.attachments[i].name1,old_doc.attachments[i].attachment))
	  

	def set_note_no(self):
		# Get Division Code
		division=frappe.get_doc("Division",self.division)
		# Get Department Code
		department=frappe.get_doc("Department and Function",self.departmentfunction)
		# Get count
		count=frappe.db.count(self.doctype,{'division':self.division,'departmentfunction':self.departmentfunction,'financial_year':self.financial_year,'status':['!=','Draft']})
		if not self.status == 'Draft':
			self.note_no='NF'+'/'+division.short_name+'/'+department.short_name+'/'+self.financial_year+'/'+str(count+1)
		else:
			self.note_no='NF'+'/'+division.short_name+'/'+department.short_name+'/'+self.financial_year+'/'+self.name

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
def get_workflow_transition(work_flow_name,division,note_department):
	transitions = frappe.get_all('Nitta Workflow Transition',filters={'parent':work_flow_name,'parenttype':'Nitta Workflow'},fields=['role','department','alert_in_days'],order_by='idx')	
	data=[]
	for transition in transitions:
		print("/////////////////////Transition////////////////////")
		print(transition)
		department = []
		if(transition.department=='From Note'):
			department.append(note_department)
		else:
			department.append(transition.department)
		
		user_role = frappe.db.sql("""
			SELECT r.role,u.name,r.departmentfunction as department,r.division  FROM `tabNitta User` u INNER JOIN `tabNitta User Role` r ON r.parent=u.name 
			WHERE (r.division IN (%(division)s) OR r.division='Corporate') AND (r.departmentfunction IN (%(department)s) OR r.departmentfunction='All') AND r.role IN (%(role)s) 
			""",values={'division':division,'department':department,'role':transition.role},as_dict=1)

		print(user_role)
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


# mail scheduled to call daily (in hooks)
@frappe.whitelist()
def sendMail():
	users_list = frappe.db.sql("""SELECT next_approval_by,note.name as doc_name,note.note_no as note_no FROM `tabNon Financial Note` note INNER JOIN `tabNitta Approval Flow` flow ON flow.parent=note.name  WHERE flow.status='Pending'  AND note.status !='Draft' AND DATE_ADD(assigned_date ,INTERVAL alert_in_days DAY) <=CURRENT_DATE()   """,as_dict=1)
	
	check_user=[]
	for user in users_list:
		is_checked = user['next_approval_by'] in check_user
		
		if(not is_checked):		
			res = list(filter(lambda x: (x.next_approval_by==user['next_approval_by']),users_list))
			check_user.append(user['next_approval_by'])
			doc_links=[]
			for r in res:
				doc_link = get_url_to_form('Non Financial Note',r['doc_name'])
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
def remove_file_backgroud(files):
    if isinstance(files, str):
        files = json.loads(files)
    frappe.enqueue(remove_file, queue='long', files=files)
    
@frappe.whitelist()	
def change_status_to_cancel(name):
	frappe.db.set_value('Non Financial Note',name,{
		'status':'Cancelled'
	})  

def remove_file(files):
    for file in files:
        frappe.delete_doc("File", file)
	

def get_attached_files(doctype,docname):
	nitta_note = frappe.get_doc(doctype,docname)
	file_names=[]

	# Other Attachment
	for attachment in nitta_note.attachments:
		if(attachment.file_name):
			file_names.append(attachment.file_name)

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
def download_pdf(doctype, docname):
    files = []
    html = frappe.get_print(doctype, docname, 'Nitta Non Financial Format', doc=None)
    pdf = get_pdf(html)
    res = write_file(pdf, docname + '_print.pdf', is_private=0)
    files.append(res)
    
    file_names = get_attached_files(doctype, docname)
    file_urls = frappe.get_all("File",
                               filters={"name": ["IN", file_names]},
                               fields=['file_url'],
                               pluck='file_url'
                               )
    
    for file_url in file_urls:
        file_path = get_file_path(file_url)
        file_extension = os.path.splitext(file_path)[1].lower()
        
        if file_extension in ['.jpg', '.jpeg', '.png']:
            img = Image.open(file_path)
            
            # Define the desired page size (in points)
            page_width = 612  # 8.5 inches
            page_height = 792  # 11 inches
            
            # Calculate the scaling factor to fit the image within the page
            img_width, img_height = img.size
            scaling_factor = min(page_width / img_width, page_height / img_height)
            img_width *= scaling_factor
            img_height *= scaling_factor
            
            # Resize the image
            img = img.resize((int(img_width), int(img_height)))
            
            img_pdf_path = file_path.replace(file_extension, '.pdf')
            img_pdf = img.convert('RGB')
            img_pdf.save(img_pdf_path)
            files.append(img_pdf_path)
        elif file_extension == '.pdf':
            files.append(file_path)
    
    # Merging PDFs and image PDFs
    merger = PdfMerger()
    for file in files:
        try:
            if file.endswith('.pdf') and os.path.exists(file):
                merger.append(file)
        except FileNotFoundError as e:
            print(f"Error appending {file}: {e}")
    
    save_file_name = 'files/' + docname + '.pdf'
    save_file_path = get_site_path() + '/public/' + save_file_name
    merger.write(save_file_path)
    merger.close()
    
    # # Optionally, remove the temporary image PDFs
    # for file in files:
    #     if file.endswith('.pdf') and os.path.exists(file):
    #         os.remove(file)
    
    return save_file_name*-/