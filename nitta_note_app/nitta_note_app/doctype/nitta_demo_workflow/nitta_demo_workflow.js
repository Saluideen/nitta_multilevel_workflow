// Copyright (c) 2023, Sajith K and contributors
// For license information, please see license.txt

frappe.ui.form.on('Nitta demo Workflow', {
	// refresh: function(frm) {

	// }
});
// frappe.ui.form.on('Nitta Multiple Transition', {
//     level: function (frm, cdt, cdn) {
//         var child = locals[cdt][cdn];
//         var level = child.level;

//         // Initialize level count
//         var levelCount = 0;

//         // Iterate through child table rows to count same-level rows
//         frm.doc.transition.forEach(function (row) {
//             if (row.level === level) {
//                 levelCount++;
//             }
//         });

//         // Update the "Level Count" field in rows with the same level
//         frm.doc.transition.forEach(function (row) {
//             if (row.level === level) {
//                 frappe.model.set_value(row.doctype, row.name, 'level_count', levelCount);
//             }
//         });

//         // Refresh the form to update the display
//         frm.refresh();
//     }
// });


