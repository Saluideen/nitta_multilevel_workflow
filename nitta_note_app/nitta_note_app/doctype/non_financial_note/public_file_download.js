// download_pdf_setting: function (frm) {
//     if (frm.doc.status == "Final Approved") {
//         frm.add_custom_button("Download", function () {
//             frappe.call({
//                 method: 'nitta_note_app.nitta_note_app.doctype.non_financial_note.non_financial_note.download_pdf',
//                 args: { "name": frm.docname },
//                 freeze: true,
//                 callback: (r) => {
//                     window.open('http://' + window.location.host + '/' + r.message)
//                 },
//                 error: (r) => {
//                     frappe.msgprint(r);
//                 }
//             })

//         })
//     }

// },