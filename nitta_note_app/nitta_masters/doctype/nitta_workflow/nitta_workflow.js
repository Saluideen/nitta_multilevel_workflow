// Copyright (c) 2023, Sajith K and contributors
// For license information, please see license.txt

frappe.ui.form.on('Nitta Workflow', {
	onload_post_render: function (frm) {
		frm.events.setting_property(frm)
	},
	note_type: function (frm) {
		frm.events.setting_property(frm)
	},

	refresh: function (frm) {
		frm.events.transition_rules_role_filter(frm)
		frm.events.copy_to_role_filter(frm)
	},

	expense_category: function (frm) {
		frm.doc.item_category = undefined
		frm.refresh_field('item_category')
		frm.set_query('item_category', function () {
			return {
				"filters": {
					'expense_category': frm.doc.expense_category
				}
			}
		})
	},


	setting_property: function (frm) {
		if (frm.doc.note_type == 'Financial') {
			frm.set_df_property('item_category', 'reqd', 1);
			frm.set_df_property('budget_provision', 'reqd', 1);
			frm.set_df_property('expense_category', 'reqd', 1);
			frm.set_df_property('upper_limit', 'reqd', 1);
			frm.set_df_property('lower_limit', 'reqd', 1);

			frm.set_df_property('item_category', 'hidden', 0);
			frm.set_df_property('budget_provision', 'hidden', 0);
			frm.set_df_property('expense_category', 'hidden', 0);
			frm.set_df_property('upper_limit', 'hidden', 0);
			frm.set_df_property('lower_limit', 'hidden', 0);
			frm.set_df_property('is_pre_approval', 'hidden', 0);



		}

		if (frm.doc.note_type == 'Non Financial') {
			frm.set_df_property('item_category', 'reqd', 0);
			frm.set_df_property('budget_provision', 'reqd', 0);
			frm.set_df_property('expense_category', 'reqd', 0);
			frm.set_df_property('upper_limit', 'reqd', 0);
			frm.set_df_property('lower_limit', 'reqd', 0);

			frm.set_df_property('item_category', 'hidden', 1);
			frm.set_df_property('budget_provision', 'hidden', 1);
			frm.set_df_property('expense_category', 'hidden', 1);
			frm.set_df_property('upper_limit', 'hidden', 1);
			frm.set_df_property('lower_limit', 'hidden', 1);
			frm.set_df_property('is_pre_approval', 'hidden', 1);


		}
	},

	transition_rules_role_filter: function (frm) {

		// Approval flow Child table Role Filter
		frm.fields_dict['transition_rules'].grid.get_field('role').get_query = function (doc, cdt, cdn) {
			var child = locals[cdt][cdn];

			if (child.department != 'From Note') {
				return {
					query: "nitta_note_app.nitta_masters.doctype.nitta_workflow.nitta_workflow.get_department_role",
					filters: { 'division': 'All', 'departmentfunction': child.department ? child.department : 'undefined' }
				};
			}


		}
	},

	copy_to_role_filter: function (frm) {

		// Approval flow Child table Role Filter
		frm.fields_dict['copy_to'].grid.get_field('role').get_query = function (doc, cdt, cdn) {
			var child = locals[cdt][cdn];

			if (child.department != 'From Note') {
				return {
					query: "nitta_note_app.nitta_masters.doctype.nitta_workflow.nitta_workflow.get_department_role",
					filters: { 'division': 'All', 'departmentfunction': child.department ? child.department : 'undefined' }
				};
			}


		}
	}
});
frappe.ui.form.on('Nitta Workflow Transition', {
	// Reset role,user in department change
	department(frm, cdt, cdn) {
		let child = locals[cdt][cdn]
		frappe.model.set_value(child.doctype, child.name, 'role', undefined)

	},

})
frappe.ui.form.on('Nitta Copy To', {
	// Reset role,user in department change
	department(frm, cdt, cdn) {
		let child = locals[cdt][cdn]
		frappe.model.set_value(child.doctype, child.name, 'role', undefined)

	},

})