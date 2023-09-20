// Copyright (c) 2023, Sajith K and contributors
// For license information, please see license.txt

frappe.ui.form.on('Nitta Vendors', {
	// refresh: function(frm) {

	// }

	vendor_name: function (frm) {
		let vendor_name = frm.doc.vendor_name
		frm.doc.vendor_code = vendor_name.split(' ').map(x => x[0].toUpperCase()).join('')
		frm.refresh_field("vendor_code")
	}
});
