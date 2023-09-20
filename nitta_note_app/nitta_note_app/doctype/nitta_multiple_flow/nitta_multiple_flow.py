# Copyright (c) 2023, Sajith K and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.share import add as add_share

class NittaMultipleflow(Document):
	def after_insert(self):
		self.date=frappe.utils.today()
		self.set_workflow()
		self.save()
	
	
	def on_update(self):		
		
		if not self.status=="Draft":
			

			# update approval flow
			self.update_workflow()
			if self.next_approval_by is not None:
					
				# Convert the user_list string back to a list
				users = self.next_approval_by.split(', ')

				for user in users:

				# Doc Share For Next Approver
					add_share(self.doctype, self.name, user=user, read=1, write=1, submit=0, share=1, everyone=0, notify=0)
			# else:
			# 	self.next_approval_by=None
			# 	self.status="Final Approved"

			
		self.reload()
	
	def update_assigned_date(self,level):
		approval_flow=frappe.get_all("Nitta Multiple Approval Flow",filters={'parent':self.name,'parenttype':self.doctype,'level':level})
		if len(approval_flow)>0:
			for d in approval_flow:
				approval=frappe.get_doc("Nitta Multiple Approval Flow",d['name'])
				approval.assigned_date=frappe.utils.now()
				approval.save()
		else:
			frappe.throw("Assign Approval flow")

	def update_updated_date(self,index):
		approval_flow=frappe.get_all("Nitta Multiple Approval Flow",filters={'parent':self.name,'parenttype':self.doctype,'idx':index})
		if len(approval_flow)>0:
			approval=frappe.get_doc("Nitta Multiple Approval Flow",approval_flow[0].name)
			approval.updated_date=frappe.utils.now()
			approval.save()
		else:
			frappe.throw("Assign Approval flow")

	def update_workflow(self):
		self.current_approval_level=0
		self.max_approval_level=0
		self.status="Initiated"
		self.rejected=False
		self.modify=False

		current_user_index =0
		# Create a list to store users at the same approval level
		next_approval_users = []
		for index,approval in enumerate(self.workflow,start=1):
			self.max_approval_level+=1
			
			if approval.status=='Approved':
				self.current_approval_level+=1
			if approval.status=='Rejected':
				self.current_approval_level+=1
			# 	self.rejected=True
			if approval.status=='Modify':
				self.modify=True
			if approval.user ==frappe.session.user and approval.status!='Pending':
				current_user_index=index
		
		if self.current_approval_level==0:
			
			level=self.workflow[self.current_approval_level].level
			level_count=self.workflow[self.current_approval_level].level_count
			# Function call to get_level
			result = get_level(level, self.name)

			# Access the values in the result dictionary
			user = result['user']
			status = result['status']
			pending=result['pending']
			self.next_approval_by=user
			if status=='status':
				
				if int(pending)==int(level_count):
					print("pending",pending,level_count)
					self.status="Initiated"
				
		elif self.current_approval_level <= self.max_approval_level:
			level=self.workflow[self.current_approval_level-1].level
			# Function call to get_level
			result = get_level(level, self.name)

			# Access the values in the result dictionary
			user = result['user']
			status = result['status']
			pending=result['pending']
			rejected=result['Rejected']
			approved=result['Approved']
			self.next_approval_by=user
			if status=="Rejected":
				self.rejected=True
			# 	self.status = (
			# 	'<span style="color: red;">Level {}</span><span style="color:red;font-weight:bold"> Rejected</span> ('
			# 	'<span style="color: green;">Approved: {}</span> '
			# 	'<span style="color: red;">Rejected: {}</span> '
			# 	'<span style="color: orange;">Pending: {}</span>)'.format(level, approved, rejected, pending)
			# )
				self.status='Level '+level+" Rejected "+'('+" approved: "+str(approved)+" rejected"+str(rejected)+" pending: "+str(pending)+')'
			if status=="Final Approved":
			# 	self.status = (
			# 	'<span style="color:green;font-weight:bolder"> Final Approved</span> ('
			# 	'<span style="color: green;">Approved: {}</span> '
			# 	'<span style="color: red;">Rejected: {}</span> '
			# 	'<span style="color: orange;">Pending: {}</span>)'.format(level, approved, rejected, pending)
			# )
				self.status="Final Approved "+'('+" Approved: "+str(approved)+" Rejected: "+str(rejected)+" pending: "+str(pending)+')'
			if status=="Approved":
			# 	self.status = (
			# 	'<span style="color: green;">Level {}</span><span style="color:green;font-weight:bold"> Approved</span> ('
			# 	'<span style="color: green;">Approved: {}</span> '
			# 	'<span style="color: red;">Rejected: {}</span> '
			# 	'<span style="color: orange;">Pending: {}</span>)'.format(level, approved, rejected, pending)
			# )
				self.status='Level '+level+" Approved "+'('+" approved: "+str(approved)+" rejected: "+str(rejected)+" pending: "+str(pending)+')'
			if status=='status':
				approval_flow = self.workflow[self.current_approval_level]
			# 	self.status = (
			# 	'<span style="color: blue;">Level {}</span> ('
			# 	'<span style="color: green;">Approved: {}</span> '
			# 	'<span style="color: red;">Rejected: {}</span> '
			# 	'<span style="color: orange;">Pending: {}</span>)'.format(level, approved, rejected, pending)
			# )
				self.status='Level '+level+'('+" approved: "+str(approved)+" rejected: "+str(rejected)+" pending: "+str(pending)+')'
			if not self.rejected and not self.modify:
				self.update_assigned_date(level)
				if current_user_index>0:
					self.update_updated_date(current_user_index)	
				
				approval_flow = self.workflow[self.current_approval_level-1]
				
			# else:
				
			# 	approval_flow = self.workflow[self.current_approval_level+1]
				
			# 	if current_user_index>0:
			# 		self.update_updated_date(current_user_index)	

		# else:
		# 	print("approval",self.current_approval_level,self.workflow[self.current_approval_level-1].level)
		# 	level=self.workflow[self.current_approval_level-1].level
		# 	# Function call to get_level
		# 	result = get_level(level, self.name)

		# 	# Access the values in the result dictionary
			
		# 	status = result['status']
		
			
			
			
		# 	if status=="Rejected":
		# 		self.rejected=True
		# 		self.status='Level '+level+"Rejected"+"Approved:"+str(approved)+"Rejected"+str(rejected)+"pending"+str(pending)
			
		# 	if status=="Approved":
		# 		self.status='Level '+level+"Approved"+"Approved:"+str(approved)+"Rejected"+str(rejected)+"pending"+str(pending)
		
			
		# 	self.next_approval_by=None
			
		
		# set assign date for first user in approval flow
		if self.status=='Initiated':
			self.update_assigned_date(level)
			
		
		self.db_update()


	def set_workflow(self):
		if self.is_multilevel:
			workflow_type="Multiple"
		else:
			workflow_type="Normal"
		workflows=frappe.get_all('Nitta demo Workflow',filters={
				'type': workflow_type
				
				},
				fields=['name'])

		if len(workflows)>0:
			self.workflow_name=workflows[0].name
			# Get workflow transitions
			workflow_transitions=get_workflow_transition(self.workflow_name)
			for transition in workflow_transitions['data']:
				self.append("workflow", {'role': transition['role'],
					'user': transition['name'],
					'department': transition['department'],
					'status':'Pending',
					'alert_in_days':transition['alert_in_days'],
					'level':transition['level'],
					'level_count':transition['level_count']
					})
			
@frappe.whitelist()
def get_level(level,name):

	status_count=0
	user=frappe.db.sql("""select user,status,level_count from `tabNitta Multiple Approval Flow` where parent=%(name)s 
	and level=%(level)s  """,
	values={'name':name,'level':level},as_dict=1)
	pending_count=sum(1 for user_info in user if user_info['status'] == 'Pending')
	approved_count=sum(1 for user_info in user if user_info['status'] == 'Approved')
	rejected_count=sum(1 for user_info in user if user_info['status'] == 'Rejected')
	if pending_count==0:

		
		if float(approved_count) >= float(user[0]['level_count']) * 0.5:
			next_level =int(level )+ 1  # Calculate the next level as the immediate number after the current level
			users=frappe.db.sql("""select user,status,level_count from `tabNitta Multiple Approval Flow` where parent=%(name)s and level=%(level)s  """,
			values={'name':name,'level':next_level},as_dict=1)
			if(len(users)>0):
				
				
				user_emails = [u['user'] for u in users]
				
				next_approval_by = ', '.join(user_emails)
				
				return {'user':next_approval_by,'Approved':approved_count,"Rejected":rejected_count,"pending":pending_count,'status':"Approved"}
			else:
				
				return {'user':None,'Approved':approved_count,"Rejected":rejected_count,"pending":pending_count,'status':"Final Approved"}
		else:
			return {'user':None,'Approved':approved_count,"Rejected":rejected_count,"pending":pending_count,'status':"Rejected"}

	else:
		
	# Extract the user emails and join them into a single string
		user_emails = [u['user'] for u in user]
		next_approval_by = ', '.join(user_emails)
		return {'user':next_approval_by,'Approved':approved_count,"Rejected":rejected_count,"pending":pending_count,'status':'status'}
	
	


@frappe.whitelist()
def get_workflow_transition(work_flow_name):
	transitions = frappe.get_all('Nitta Multiple Transition',filters={'parent':work_flow_name},fields=['role','department','alert_in_days','level','level_count'],order_by='idx')	
	data=[]
	for transition in transitions:
		department = []
		if(transition.department=='From Note'):
			department.append(note_department)
		else:
			department.append(transition.department)
		
		user_role = frappe.db.sql("""
			SELECT r.role,u.name,r.departmentfunction as department,r.division  FROM `tabNitta User` u INNER JOIN `tabNitta User Role` r ON r.parent=u.name 
			WHERE  (r.departmentfunction IN (%(department)s) OR r.departmentfunction='All') AND r.role IN (%(role)s) 
			""",values={'department':department,'role':transition.role},as_dict=1)

		
		# If count of user is more than one filter appropriate users based on division and depratment
		if len(user_role)==1:
			data.append({'role':user_role[0].role,'name':user_role[0].name,'department':user_role[0].department,'alert_in_days':transition.alert_in_days,'level':transition.level,'level_count':transition.level_count})
		
	return {'Status':True,'data':data}

@frappe.whitelist()
def get_employee_details(name):
	return frappe.db.sql("""SELECT role.division FROM `tabNitta User` employee inner join `tabNitta User Role` role 
	on employee.name=role.parent
	WHERE  employee.email=%(name)s""",values={'name':name},as_dict=1)
