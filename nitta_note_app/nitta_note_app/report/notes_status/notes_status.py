# Copyright (c) 2022, Sajith K and contributors
# For license information, please see license.txt

import frappe
from datetime import date,datetime,timedelta
from dataclasses import dataclass


def execute(filters=None):
	columns, data = [], []
	columns=get_columns()
	data=get_data(filters)
	chart=get_chart(data)
	summary=get_summary(data)
	return columns, data, None, chart, summary

def get_columns():
	columns = [{
		"fieldname": "note_no",
		"label": "Note No",
		"fieldtype": "Data"
	},{
		"fieldname": "date",
		"label": "Date",
		"fieldtype": "Data"
	},{
		"fieldname": "division",
		"label": "Division",
		"fieldtype": "Data"
	},{
		"fieldname": "departmentfunction",
		"label": "Department",
		"fieldtype": "Data"
	},{
		"fieldname": "expense_category",
		"label": "Expense Category",
		"fieldtype": "Data"
	},{
		"fieldname": "amount",
		"label": "Amount",
		"fieldtype": "Data"
	},{
		"fieldname": "status",
		"label": "Status",
		"fieldtype": "Data"
	},{
		"fieldname": "initiated_by",
		"label": "Initiator",
		"fieldtype": "Data"
	},{
		"fieldname": "next_approval_by",
		"label": "Next Approver",
		"fieldtype": "Data"
	}
	]
	return columns

def get_data(filters):
	
	# Filters
	note_type="All"
	note_filter={}
	note_filter['Status']=['!=','Draft']
	# note date
	from_date=datetime.now()
	to_date=datetime.now()
	# getting current user roles
	get_roles = frappe.get_roles()

	for key in filters:
		if key in ["division","departmentfunction","expense_category"]:
			note_filter[key]=filters[key]
		if key=="from_date":
			from_date=filters[key]
		if key=="to_date":
			to_date=filters[key]
		if key=="note_type":
			note_type=filters[key]

	note_filter["date"]=['between',[from_date,to_date]]
	financial_notes=[]
	non_financial_notes=[]

	if "MD" in get_roles:
		# Get all Financial Notes
		financial_notes = frappe.get_all('Nitta Note',filters=note_filter,fields=['note_no','date',
		'division','departmentfunction','expense_category','expected_amount','revised_amount','status','initiated_by','next_approval_by'])

		# Get all Non Financial Notes
		non_financial_notes = frappe.get_all('Non Financial Note',filters=note_filter,fields=['note_no','date',
		'division','departmentfunction','status','initiated_by','next_approval_by'])
	else:
		# Get all Financial Notes
		financial_notes = frappe.get_list('Nitta Note',filters=note_filter,fields=['note_no','date',
		'division','departmentfunction','expense_category','expected_amount','revised_amount','status','initiated_by','next_approval_by'])

		# Get all Non Financial Notes
		non_financial_notes = frappe.get_list('Non Financial Note',filters=note_filter,fields=['note_no','date',
		'division','departmentfunction','status','initiated_by','next_approval_by'])

	# Get Amount and status
	for financial_note in financial_notes:
		financial_note['amount'] = financial_note.revised_amount if financial_note.revised_amount > 0 else financial_note.expected_amount


	if note_type=="All":
		notes=financial_notes+non_financial_notes
	elif note_type=="Financial":
		notes=financial_notes
	elif note_type=="Non Financial":
		notes=non_financial_notes

	return notes

def get_summary(datas):
	
	total_count = len(datas)
	rejected_count = len([data for data in datas if "rejected" in data.status.lower()])
	approved_count = len([data for data in datas if "final approved" in data.status.lower()])
	pending_count = total_count-(rejected_count+approved_count)
	
		
	return [
		{
			'value':total_count,
			'indicator':'Green',
			'label':'Total Notes',
			'datatype':'Int'
		},
		{
			'value':pending_count,
			'indicator':'Blue',
			'label':'Pending Notes',
			'datatype':'Int'
		},
		{
			'value':approved_count,
			'indicator':'Green',
			'label':'Approved Notes',
			'datatype':'Int'
		},
		{
			'value':rejected_count,
			'indicator':'Red',
			'label':'Rejected Notes',
			'datatype':'Int'
		},
	]

def get_chart(datas):
	
	#get unique departments
	departments=set()
	for data in datas:
		departments.add(data.departmentfunction)

	#Get Departments
	departments_data=frappe.get_all("Department and Function",fields=['name','short_name'])

	#Get department wise approved,pending and rejected
	approved=[]
	pending=[]
	rejected=[]
	department_code=[]

	for department in departments:
		rejected_count = len([data for data in datas if data.departmentfunction == department and "rejected" in data.status.lower()])
		approved_count = len([data for data in datas if data.departmentfunction == department and "final approved" in data.status.lower()])
		pending_count = len([data for data in datas if data.departmentfunction == department])-(rejected_count+approved_count)
		approved.append(approved_count)
		rejected.append(rejected_count)
		pending.append(pending_count)

		department_code.append([data for data in departments_data if data.name == department][0].short_name)

	chart={
		'data':{
			'labels':department_code,
			'datasets':[
				{'name':'Approved','values':approved},
				{'name':'Rejected','values':rejected},
				{'name':'Pending','values':pending}
				]
		},
		'type':'bar',
		'height':300,
		'colors': ["#00C698","#F25C54","#F7B267"]
	}
	return chart