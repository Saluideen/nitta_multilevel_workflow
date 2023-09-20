// Copyright (c) 2023, Sajith K and contributors
// For license information, please see license.txt

frappe.ui.form.on('Nitta Multiple flow', {
	refresh: function(frm) {
		frappe.call({
			method:
			  "nitta_note_app.nitta_note_app.doctype.nitta_multiple_flow.nitta_multiple_flow.get_employee_details",
			args: {
			  name: frappe.session.user,
			},
			callback: function (r) {
			  frm.doc.division = r.message[0].division;
			
			  frm.refresh_field("division");
			 
			},
		  });


		 
			if (!frm.is_new() && frm.doc.status == "Draft") {
			  cur_frm.page.add_action_item("Initiate", function () {
				frm.doc.status = "Initiated";
				frm.refresh_field("status");
				frm.dirty();
				frm.save();
			  });
			  frm.change_custom_button_type("Initiate", null, "primary");
			}
		  
			// Approve Button

			if (
				frm.doc.next_approval_by .includes(frappe.session.user) &&
				frm.doc.status != "Final Approved"
			  ) {
				frm.page.add_action_item("Approve ", () => {
				  let index = frm.doc.workflow.findIndex(
					(el) => el.user == frappe.session.user && el.status != "Approved"
				  );
				  frm.doc.workflow[index].status = "Approved";
				  frm.refresh_field("workflow");
				  frm.dirty();
				  frm.save();
				});
			  }
			  if (
				frm.doc.next_approval_by .includes(frappe.session.user) &&
				frm.doc.status != "Final Approved"
			  ) {
				frm.page.add_action_item("Reject ", () => {
				  let index = frm.doc.workflow.findIndex(
					(el) => el.user == frappe.session.user && el.status != "Rejected"
				  );
				  frm.doc.workflow[index].status = "Rejected";
				  frm.refresh_field("workflow");
				  frm.dirty();
				  frm.save();
				});
			  }
		

	},
	// is_multilevel:function(frm){
	// // 	//   hide transition table
	// //   hide transition table
	// if(frm.doc.is_multilevel=="1")
	// {
	// 	frm.set_df_property("workflow", "hidden", 0);
	// }
	// else
	// {
	// 	frm.set_df_property("workflow", "hidden", 1);
	// }
	// },
	
});

