// Copyright (c) 2023, Sajith K and contributors
// For license information, please see license.txt

frappe.ui.form.on('Nitta demo Workflow', {
	refresh: function(frm) {
		

	},
	before_save(frm){
		frm.events.sort(frm)
	},
	sort:function(frm){
		
            // set all data from child table to workflow array
			let workflow = get_workflow(frm);
			frm.clear_table("transition");
			  // Now, add all the data from the workflow array to the child table
			workflow.forEach(function (record) {
			  frm.add_child("transition", {
				department: record.department,
				role: record.role,
				level: record.level,
				
			  });
			});

	},

	
});
function get_workflow(frm) {
	let workflow = [];
	let childTableData = frm.doc.transition || [];
  
	for (var i = 0; i < childTableData.length; i++) {
	  workflow.push(childTableData[i]);
	}
	workflow.sort((a, b) => {
	  // Assuming "level" is a numeric property in each object
	  return a.level - b.level;
	});
  
	return workflow;
  }



