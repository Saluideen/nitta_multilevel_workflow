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