@frappe.whitelist()
def download_pdf(name):
	
	_path=[]

	# Creating and save Print format to public files folder
	html = frappe.get_print("Non Financial Note", name, 'Nitta Non Financial Format', doc=None,)
	pdf = get_pdf(html)
	res=write_file(pdf,name+'_print.pdf',is_private=0)
	_path.append(res)

	nitta_note = frappe.get_doc("Non Financial Note",name)

	# Attachment Files
	attachments= nitta_note.attachments
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

	file_name = attachment_file_name
	
	
	for attachment in file_name:
		path=get_file_path(attachment.file_url)
		_path.append(path)
		
	save_file_name ='files/'+name+'.pdf'
	pdfs = _path
# Merging
	merger = PdfMerger()
	for pdf in pdfs:
		merger.append(pdf)
	merger.write(get_site_path()+'/public/'+save_file_name)
	merger.close()

	return save_file_name