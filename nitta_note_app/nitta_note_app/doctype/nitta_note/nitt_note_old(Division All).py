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
from frappe.utils.file_manager import get_file,download_file,get_file_path,write_file
from PyPDF2 import PdfMerger



from frappe.utils import get_site_path
class NittaNote(Document):

	def validate(self):
		self.total_amount=self.expected_amount
		
		
	def before_save(self):
		if self.status=="Draft":

			doc_list = frappe.get_list("Nitta Note",filters={'name':self.name})
			if(len(doc_list)>0):
				doc= frappe.get_doc("Nitta Note",self.name)
				if(float(doc.expected_amount)!=float(self.expected_amount)):
					self.approval_flow=[]
					self.set_workflow()

	def after_insert(self):
		self.note_no=self.name
		self.date=date.today()
		self.set_workflow()
		self.save()
		

	def on_trash(self):
		# prevent delete if initiated
		if not self.status=="Draft" and frappe.session.user!='Administrator':
			frappe.throw("Cannot delete initiated Note")


	def on_update(self):		
        # add changes to time line
		# self.add_changes_to_itmeline()
	


		if self.status=='Initiated':
			self.update_assigned_date(1)
		
		if not self.status=="Draft":
			# update approval flow
			self.update_workflow()

			# Doc Share For Next Approver
			add_share(self.doctype, self.name, user=self.next_approval_by, read=1, write=1, submit=0, share=1, everyone=0, notify=0)

			# Doc Assign to
			is_exist_assign = frappe.db.exists('ToDo',{'reference_type':self.doctype,'reference_name':self.name,'allocated_to':self.next_approval_by})
			if not is_exist_assign and self.next_approval_by:
				user_name = frappe.get_cached_value("User", frappe.session.user, "full_name")
				add_assignment({"doctype": self.doctype, "name": self.name, "assign_to": [self.next_approval_by]})
				doc_link = get_url_to_form('Nitta Note',self.name)
				args={
				"message":user_name+" Requested to approve "+self.name,
				"doc_link":{"doc_link":doc_link,'name':self.name},
				"header":['Request for Approval of '+self.name, 'green'],
				}
				frappe.sendmail(template='assign_to',subject="Request for Approval of "+self.name,recipients=[self.next_approval_by],args=args)	

		self.reload()


	def update_assigned_date(self,index):
		approval_flow=frappe.get_all("Nitta Approval Flow",filters={'parent':self.name,'parenttype':self.doctype,'idx':index})
		if len(approval_flow)>0:
			approval=frappe.get_doc("Nitta Approval Flow",approval_flow[0].name)
			approval.assigned_date=date.today()
			approval.save()
		else:
			frappe.throw("Assign Approval flow")

	def update_updated_date(self,index):
		approval_flow=frappe.get_all("Nitta Approval Flow",filters={'parent':self.name,'parenttype':self.doctype,'idx':index})
		if len(approval_flow)>0:
			approval=frappe.get_doc("Nitta Approval Flow",approval_flow[0].name)
			approval.updated_date=datetime.now()
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
			workflow_transitions=get_workflow_transition(self.work_flow_name,self.division,self.departmentfunction)
			for transition in workflow_transitions['data']:
				
				self.append("approval_flow", {'role': transition['role'],
						'nitta_user': transition['name'],
						'department': transition['department'],
						'status':'Pending',
						'alert_in_days':transition['alert_in_days'],
						'is_editable':False
						})
			copy_to= get_copy_to(self.work_flow_name,self.division,self.departmentfunction)
			for copy in copy_to['data']:
				self.append('copy_to',{
					'role': copy['role'],
					'nitta_user': copy['nitta_user'],
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
			# self.send_final_mail()
			if current_user_index>0:
				self.update_updated_date(current_user_index)	
			# Copy Sharing
			is_copy_to = frappe.get_all('Nitta CC',filters={'parent':self.name,'parenttype':self.doctype},fields=['nitta_user'])
			for copy in is_copy_to:
				# Doc Share For CC user
				add_share(self.doctype, self.name, user=copy.nitta_user, read=1, write=1, submit=0, share=1, everyone=0, notify=0)
		self.db_update()

	def send_final_mail(self):
		args={
		"message":"Note is Approved",
		
				}

		
		frappe.sendmail(template='noteapproved',subject="Note Approved",recipients=self.initiated_by,args=args,header=['Note Approved', 'green'],)


	def add_changes_to_timeline(self):
		old_doc = self.get_doc_before_save()
		if old_doc and old_doc.date_of_completion_of_project != self.date_of_completion_of_project:
			self.add_comment('Edit', '<span style="color:red">Date of completion of project</span> changed from <b>{0}</b> to <b>{1}<b>'.format(old_doc.date_of_completion_of_project,self.date_of_completion_of_project))


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
	if filters["user"] in ('Administrator','System Manager') or all_division:
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
	AND (r.departmentfunction = %(departmentfunction)s OR r.departmentfunction = 'All') GROUP BY r.role
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
			SELECT r.role,u.name,r.departmentfunction as department  FROM `tabNitta User` u INNER JOIN `tabNitta User Role` r ON r.parent=u.name WHERE r.division IN (%(division)s) AND r.departmentfunction IN (%(department)s) AND r.role IN (%(role)s) LIMIT 1 
			""",values={'division':division,'department':department,'role':transition.role},as_dict=1)
		if len(user_role)>0:
			data.append({'role':user_role[0].role,'name':user_role[0].name,'department':user_role[0].department,})
	
	return {'Status':True,'data':data}


@frappe.whitelist()
def get_gl_details(name,note_name):
	details=frappe.db.sql("""
	SELECT description,budget_amount- COALESCE((SELECT SUM(expected_amount) FROM `tabNitta Note` WHERE status !='Draft' AND status NOT LIKE CONCAT(\'%%\','Rejected',\'%%\')  AND gl_account_no=%(name)s AND name != %(note_name)s),0) as budget_amount
	FROM `tabRevenue Expense` WHERE name=%(name)s
	""",values={'name':name,'note_name':note_name},as_dict=1)
	return {'Status':True,'data':details}




@frappe.whitelist()
def capex_expense_details(name,note_name):
	details=frappe.db.sql("""
	SELECT project,amount- COALESCE((SELECT SUM(expected_amount) FROM `tabNitta Note` WHERE status !='Draft' AND status NOT LIKE CONCAT(\'%%\','Rejected',\'%%\')  AND sn_in_budget_sheet=%(name)s AND name != %(note_name)s),0) as amount
	 FROM `tabCapex Expense` WHERE name=%(name)s
	""",values={'name':name,'note_name':note_name},as_dict=1)
	return {'Status':True,'data':details}

@frappe.whitelist()
def sendMail():
	users_list = frappe.db.sql("""SELECT next_approval_by,note.name as doc_name FROM `tabNitta Note` note INNER JOIN `tabNitta Approval Flow` flow ON flow.parent=note.name  WHERE flow.status='Pending'  AND note.status !='Draft' AND DATE_ADD(DATE(assigned_date) ,INTERVAL alert_in_days DAY) <=CURRENT_DATE()   """,as_dict=1)
	
	check_user=[]
	for user in users_list:
		is_checked = user['next_approval_by'] in check_user
		
		if(not is_checked):
			
			res = list(filter(lambda x: (x.next_approval_by==user['next_approval_by']),users_list))
			check_user.append(user['next_approval_by'])
			doc_links=[]
			for r in res:
				doc_link = get_url_to_form('Nitta Note',user['doc_name'])
				doc_links.append({"doc_link":doc_link,'name':r['doc_name']})

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
	frappe.msgprint('Internal Order No Updated.')
	
	
@frappe.whitelist()
def remove_file_backgroud(files):
    if isinstance(files, str):
        files = json.loads(files)
    frappe.enqueue(remove_file, queue='long', files=files)

def remove_file(files):
    for file in files:
        frappe.delete_doc("File", file)
	
	
@frappe.whitelist()
def remove_unused_files(doctype,docname):
	# Get question images
	attached_vendors = frappe.get_all(
	"Nitta Vendor Quotations",
	filters={
	"parent": docname,
	

	},
	fields=['file_name'],
	pluck='file_name'
	)

	

	attachments = frappe.get_all(
	"Nitta Attachments",
	filters={
	"parent": docname,
	
	},
	fields=['file_name'],
	pluck='file_name'
	)

	# Get the attached files
	attached_files = frappe.get_all(
	"File",
	filters={
	"attached_to_doctype": doctype,
	"attached_to_name": docname,
	"name":["not in",attached_vendors+attachments],
	"is_private":1
	
	},
	pluck='name'
	)
	
	
	if attached_files:
	# Delete the attached files
		remove_file_backgroud(attached_files)



@frappe.whitelist()
def download_pdf(name):
	
	_path=[]

	# Creating and save Print format to public files folder
	html = frappe.get_print("Nitta Note", name, 'Nitta Note Format', doc=None,)
	pdf = get_pdf(html)
	res=write_file(pdf,name+'_print.pdf',is_private=0)
	_path.append(res)

	nitta_note = frappe.get_doc("Nitta Note",name)

	# Attachment Files
	attachments= nitta_note.other_attachments
	attachment_filename=[]
	for attachment in attachments:
		if(attachment.file_name):
			attachment_filename.append(attachment.file_name)
	

	attachment_file_name=frappe.get_all(
	"File",
	filters={
	"name":["IN",attachment_filename]
	
	},
	fields=['file_url']
	)

# Vendor Files

	vendors_attachment= nitta_note.vendors
	vendors_attachment_filename=[]
	for attachment in vendors_attachment:
		if(attachment.file_name):
			vendors_attachment_filename.append(attachment.file_name)
	

	vendor_file_name=frappe.get_all(
	"File",
	filters={
	"name":["IN",vendors_attachment_filename]
	
	},
	fields=['file_url']
	)

# Add Two attachments to single array
	file_name = vendor_file_name+attachment_file_name
	
	for attachment in file_name:
		p=get_file_path(attachment.file_url)
		_path.append(p)
		
	save_file_name ='files/'+name+'.pdf'
	pdfs = _path

# Merging
	merger = PdfMerger()
	for pdf in pdfs:
		merger.append(pdf)
	merger.write(get_site_path()+'/public/'+save_file_name)
	merger.close()

	return save_file_name


	
