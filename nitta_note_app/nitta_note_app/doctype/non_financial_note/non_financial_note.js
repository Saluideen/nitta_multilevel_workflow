// Copyright (c) 2023, Sajith K and contributors
// For license information, please see license.txt
// frappe.require([
// 	"assets/nitta_note_app/css/workflow_table.css",
// ]);

frappe.ui.form.on('Non Financial Note', {

	///////////////////////////////// Events /////////////////////////////////////////
	refresh: function (frm) {

		if (frm.is_new()) {
			frm.set_df_property("attachments", "hidden", 1)
			frm.doc.note_no = undefined;
			frm.doc.date = undefined;
			frm.refresh_field('note_no')
			frm.refresh_field('date')
		} else {
			frm.set_df_property("attachments", "hidden", 0)
			// frm.events.remove_unused_files(frm) 
			frm.events.download_pdf_setting(frm)
		}

		// add default value to other attachments and disable attachment button
		frm.events.attachment_settings(frm)

		//set text editor height
		frm.events.texteditor_settings(frm)

		//set approval flow, pre approval note and workflow table
		frm.events.set_approval_flow(frm)

		//apply workflow style
		frm.events.apply_workflow_table_style(frm)

		//set financial year
		frm.events.set_financial_year(frm)

		//set division
		frm.events.set_division(frm)

		//set initiate,approve and reject buttons
		frm.events.set_approval_button(frm)

		frm.events.set_cancel_button(frm)

	},
	division: function (frm) {
		if (!frm.doc.division) {
			frm.doc.departmentfunction = undefined;
			frm.refresh_field('departmentfunction')
		}
		else {
			frm.events.set_department(frm);
		}
	},
	work_flow_name: function (frm) {
		// Getting Workflow Trasitions
		frappe.call({
			method: "nitta_note_app.nitta_note_app.doctype.non_financial_note.non_financial_note.get_workflow_transition",
			args: {
				work_flow_name: frm.doc.work_flow_name ? frm.doc.work_flow_name : 'undefined',
				division: frm.doc.division ? frm.doc.division : 'undefined',
				note_department: frm.doc.departmentfunction ? frm.doc.departmentfunction : 'undefined'
			},
			freeze: true,
			callback: function (r) {
				let data = r.message.data
				console.log(data)
				frm.doc.approval_flow = undefined;
				data.forEach(d => {
					frm.add_child('approval_flow', {
						role: d.role,
						nitta_user: d.name,
						department: d.department
					})
				});
				frm.refresh_field("approval_flow")
			},
			error: function (err) {
				frappe.msgprint(err);
			}
		});

		// Getting Copy To
		frappe.call({
			method: "nitta_note_app.nitta_note_app.doctype.non_financial_note.non_financial_note.get_copy_to",
			args: {
				work_flow_name: frm.doc.work_flow_name ? frm.doc.work_flow_name : 'undefined',
				division: frm.doc.division ? frm.doc.division : 'undefined',
				note_department: frm.doc.departmentfunction ? frm.doc.departmentfunction : 'undefined'
			},
			freeze: true,
			callback: function (r) {
				let data = r.message.data
				frm.doc.copy_to = undefined;
				data.forEach(d => {
					frm.add_child('copy_to', {
						role: d.role,
						nitta_user: d.name,
						department: d.department
					})
				});
				frm.refresh_field("copy_to")

			},
			error: function (err) {
				frappe.msgprint(err);
			}
		});
	},



	//////////////////////////////////// Custom methods ////////////////////////////////////
	set_financial_year: function (frm) {
		frm.set_query("financial_year", function () {
			return {
				filters: { "is_active": true }
			};
		});
		if (!frm.doc.financial_year) {
			frappe.db.get_list('Nitta Financial Year', {
				fields: ['name'],
				filters: {
					is_active: true
				}
			}).then(records => {
				if (records.length > 0) {
					frm.doc.financial_year = records[0].name;
					frm.refresh_field('financial_year')
				}
			})
		}
	},
	set_division: function (frm) {
		frm.set_query("division", function () {
			return {
				query: "nitta_note_app.nitta_note_app.doctype.non_financial_note.non_financial_note.get_divisions",
				filters: { "user": frappe.session.user }
			};
		});
		if (!frm.doc.division) {
			frappe.call({
				method: 'nitta_note_app.nitta_note_app.doctype.non_financial_note.non_financial_note.get_divisions',
				args: {
					"doctype": "Division",
					"searchfield": "",
					"start": 0,
					"page_len": 1,
					"txt": "",
					filters: { "user": frappe.session.user }
				},
				freeze: true,
				callback: (r) => {
					let division_array = [].concat(...r.message);
					if (division_array.includes('Corporate')) {
						frm.doc.division = "Corporate"
					} else {
						frm.doc.division = r.message[0][0];
					}
					frm.refresh_field('division');
					//set department/function
					frm.events.set_department(frm);
				},
				error: (r) => {
					frappe.msgprint(r);
				}
			})
		}
	},
	set_department: function (frm) {

		frm.doc.departmentfunction = undefined;
		frm.refresh_field('departmentfunction')


		frm.set_query("departmentfunction", function () {
			return {
				query: "nitta_note_app.nitta_note_app.doctype.non_financial_note.non_financial_note.get_department",
				filters: { "user": frappe.session.user, "division": frm.doc.division ? frm.doc.division : 'undefined' }
			};
		});

		if (!frm.doc.departmentfunction) {
			frappe.call({
				method: 'nitta_note_app.nitta_note_app.doctype.non_financial_note.non_financial_note.get_department',
				args: {
					"doctype": "Department and Function",
					"searchfield": "",
					"start": 0,
					"page_len": 1,
					"txt": "",
					filters: { "user": frappe.session.user, "division": frm.doc.division ? frm.doc.division : 'undefined' }
				},
				freeze: true,
				callback: (r) => {

					frm.doc.departmentfunction = r.message[0][0];
					frm.refresh_field('departmentfunction');

				},
				error: (r) => {
					frappe.msgprint(r);
				}
			})
		}
	},
	set_approval_button: function (frm) {

		//clear all buttons
		frm.page.clear_actions_menu();

		// Initiate
		if (!frm.is_new() && frm.doc.initiated_by == frappe.session.user && frm.doc.status == "Draft") {

			frm.page.add_action_item('Initiate', () => {
				if (frm.doc.approval_flow.length > 0) {
					frm.doc.status = 'Initiated'
					frm.refresh_field("status")
					frm.dirty()
					frm.save()
				} else {
					frappe.msgprint('Please Fill Approval Flow')
				}

			})
		}

		// Approve, Modify Or Reject 
		if (frm.doc.next_approval_by == frappe.session.user) {

			frm.page.add_action_item('Approve', () => {
				let index = frm.doc.approval_flow.findIndex((el) => el.nitta_user == frappe.session.user && el.status != 'Approved')
				frm.doc.approval_flow[index].status = 'Approved'
				frm.refresh_field("approval_flow")
				frm.dirty()
				frm.save()
			})
			if (frm.doc.approval_flow.findIndex((el) => el.status == 'Modify') == -1) {
				frm.page.add_action_item('Modify', () => {
					let index = frm.doc.approval_flow.findIndex((el) => el.nitta_user == frappe.session.user && el.status != 'Approved')
					frm.doc.approval_flow[index].status = 'Modify'
					frm.refresh_field("approval_flow")
					frm.dirty()
					frm.save()
				})
			}
			if (frm.doc.approval_flow.findIndex((el) => el.status == 'Rejected') == -1) {
				frm.page.add_action_item('Reject', () => {

					let index = frm.doc.approval_flow.findIndex((el) => el.nitta_user == frappe.session.user && el.status != 'Approved')
					frm.doc.approval_flow[index].status = 'Rejected'
					frm.refresh_field("approval_flow")
					frm.dirty()
					frm.save()
				})
			}
		}
	},
	set_approval_flow: function (frm) {

		// clear workflow on duplication (creating new doc)
		if (frm.is_new()) {
			frm.events.clear_workflow(frm);
		}

		// disable document save for user if once approved and not modify
		if (frappe.user.name!='Administrator' && !frm.is_new() && frm.doc.status != 'Draft' && frm.doc.status.toLowerCase().indexOf('modify') == -1) {
			frm.disable_save()
		}

		// make fields read only once initiated
		if (!frm.is_new() && frm.doc.status != 'Draft') {
			frm.events.page_read_permission(frm, 1)
		}

		// make workflow fields visible and set 
		if (!frm.is_new() && frm.doc.status == 'Draft') {
			frm.events.set_workflow_settings(frm);
			frm.events.set_workflow_name(frm);
		}

		// Approval flow Child table Role Filter
		frm.fields_dict['approval_flow'].grid.get_field('role').get_query = function (doc, cdt, cdn) {
			var child = locals[cdt][cdn];
			let department = ''

			if (child.department == 'From Note') {
				department = frm.doc.departmentfunction
			} else {
				department = child.department
			}
			return {
				query: "nitta_note_app.nitta_note_app.doctype.non_financial_note.non_financial_note.get_department_role",
				filters: { 'division': frm.doc.division ? frm.doc.division : 'undefined', 'departmentfunction': department ? department : 'undefined' }
			};
		}

		// Approval flow Child table User Filter
		frm.fields_dict['approval_flow'].grid.get_field('nitta_user').get_query = function (doc, cdt, cdn) {
			var child = locals[cdt][cdn];
			let department = ''

			if (child.department == 'From Note') {
				department = frm.doc.departmentfunction
			} else {
				department = child.department
			}
			return {
				query: "nitta_note_app.nitta_note_app.doctype.non_financial_note.non_financial_note.get_nitta_user",
				filters: { "role": child.role ? child.role : 'undefined', 'division': frm.doc.division ? frm.doc.division : 'undefined', 'departmentfunction': department ? department : 'undefined' }
			};
		}

		// Copy to Child table Role Filter
		frm.fields_dict['copy_to'].grid.get_field('role').get_query = function (doc, cdt, cdn) {
			var child = locals[cdt][cdn];
			let department = ''

			if (child.department == 'From Note') {
				department = frm.doc.departmentfunction
			} else {
				department = child.department
			}
			return {
				query: "nitta_note_app.nitta_note_app.doctype.non_financial_note.non_financial_note.get_department_role",
				filters: { 'division': frm.doc.division ? frm.doc.division : 'undefined', 'departmentfunction': department ? department : 'undefined' }
			};
		}

		// Copy To Child table User Filter
		frm.fields_dict['copy_to'].grid.get_field('nitta_user').get_query = function (doc, cdt, cdn) {
			var child = locals[cdt][cdn];
			let department = ''

			if (child.department == 'From Note') {
				department = frm.doc.departmentfunction
			} else {
				department = child.department
			}
			return {
				query: "nitta_note_app.nitta_note_app.doctype.non_financial_note.non_financial_note.get_nitta_user",
				filters: { "role": child.role ? child.role : 'undefined', 'division': frm.doc.division ? frm.doc.division : 'undefined', 'departmentfunction': department ? department : 'undefined' }
			};
		}

		//make approval_flow table fileds read_only if is_editable=0
		let non_editable_fields = ['department', 'role', 'nitta_user']
		frm.fields_dict['approval_flow'].grid.grid_rows.forEach((grid_row) => {
			if (grid_row.doc.is_editable === 0) {
				grid_row.docfields.forEach((df) => {
					if (non_editable_fields.includes(df.fieldname)) {
						df.read_only = 1;
					}
				});
			}
		});
	},
	set_workflow_name: async function (frm) {
		// Getting Entity Type
		let entity_type = ['All']
		await frappe.call({
			method: 'nitta_note_app.nitta_note_app.doctype.non_financial_note.non_financial_note.get_entity_type',
			args: { "departmentfunction": frm.doc.departmentfunction },
			freeze: true,
			callback: (r) => {
				entity_type.push(r.message);
			},
			error: (r) => {
				frappe.msgprint(r);
			}
		})

		let res = frm.set_query('work_flow_name', () => {
			return {
				filters: {
					note_type: 'Non Financial',
					entity_type: ['in', entity_type]
				}
			}
		})
	},
	attachment_settings: function (frm) {
		//disable sidebar attachments section
		$(".form-attachments").hide();
	},
	texteditor_settings: function (frm) {
		$('.ql-editor').css({ height: '100px' });
	},
	download_pdf_setting: function (frm) {
		frm.add_custom_button("Preview", function () {
			frappe.call({
				method: 'nitta_note_app.nitta_note_app.doctype.non_financial_note.non_financial_note.download_pdf',
				args: {
					doctype: frm.doctype,
					docname: frm.docname
				},
				freeze: true,
				callback: (r) => {
					window.open('http://' + window.location.host + '/' + r.message)
				},
				error: (r) => {
					frappe.msgprint(r);
				}
			})
		})

	},
	set_cancel_button: function (frm) {
		if (frm.doc.status == "Final Approved") {
			if (frappe.user_roles.includes("Nitta Admin", "Administrator")) {
				frm.add_custom_button("Cancel", function () {
					frappe.confirm(
						"<h5>Do you want to cancel the document?</h5>",
						function () {
							frappe.call({
								method: 'nitta_note_app.nitta_note_app.doctype.non_financial_note.non_financial_note.change_status_to_cancel',
								args: { "name": frm.docname },
								freeze: true,
								callback: (r) => {
									frappe.msgprint('Document status changed into Cancelled');
									window.location.reload();
								},
								error: (r) => {
									frappe.msgprint(r);
								}
							})
						},
						function () {
							// reject();
						}
					)
				})
			}
		}
	},
	clear_workflow: function (frm) {
		frm.doc.work_flow_name = undefined;
		frm.refresh_field('work_flow_name');
		frm.doc.approval_flow = undefined;
		frm.refresh_field('approval_flow');
		frm.doc.current_approval_level = undefined;
		frm.refresh_field('current_approval_level');
		frm.doc.max_approval_level = undefined;
		frm.refresh_field('max_approval_level');
		frm.doc.next_approval_by = undefined;
		frm.refresh_field('next_approval_by');
		frm.doc.copy_to = undefined;
		frm.refresh_field('copy_to');
		frm.doc.status = 'Draft';
		frm.refresh_field('status');

		frm.set_df_property('work_flow_name', 'hidden', 1);
		frm.set_df_property('initiated_by', 'hidden', 1);
		frm.set_df_property('status', 'hidden', 1);
		frm.set_df_property('approval_flow', 'hidden', 1);
		frm.set_df_property('next_approval_by', 'hidden', 1);
		frm.set_df_property('copy_to', 'hidden', 1);
	},
	set_workflow_settings: function (frm) {
		frm.set_df_property('work_flow_name', 'hidden', 0);
		frm.set_df_property('initiated_by', 'hidden', 0);
		frm.set_df_property('status', 'hidden', 0);
		frm.set_df_property('approval_flow', 'hidden', 0);
		frm.set_df_property('next_approval_by', 'hidden', 0);
		frm.set_df_property('copy_to', 'hidden', 0);
	},
	apply_workflow_table_style: function (frm) {
		$(".frappe-control[data-fieldname='approval_flow']")
			.find(".grid-body")
			.find("[data-fieldname='status']")
			.each(function () {
				if ($(this).text() === "Approved") {
					$(this).css({
						"color": "#05B01F",
						"background-color": "#D9F0D8",
						"font-weight": "bold"
					});
				}
				else if ($(this).text() === "Rejected") {
					$(this).css({
						"color": "#B00505",
						"background-color": "#F0D8D8",
						"font-weight": "bold"
					});
				} else if ($(this).text() === "Modify") {
					$(this).css({
						"color": "#FFA500",
						"background-color": "#FBFCDE",
						"font-weight": "bold"
					});
				}
				else {
					$(this).css({
						"color": "black",
						"background-color": "#FFFFFF",
						"font-weight": "bold"
					});
				}
			});
	},
	page_read_permission: function (frm, value) {
		frm.set_df_property("approval_flow", 'read_only', value)
		frm.set_df_property("work_flow_name", 'read_only', value)
		frm.set_df_property("copy_to", 'read_only', value)
		frm.set_df_property("division", 'read_only', value)
		frm.set_df_property("departmentfunction", 'read_only', value)
		frm.set_df_property("financial_year", 'read_only', value)
	},
	uploadPrivateFile: async function (frm) {
		let file_doc = await new Promise((resolve, reject) => {
			new frappe.ui.FileUploader({
				doctype: frm.doctype,
				docname: frm.docname,
				allow_multiple: false,
				restrictions: {
					allowed_file_types: [".pdf"]
				},
				folder: 'Home/Attachments',
				on_success: (file_doc) => {
					if (file_doc.file_url.includes('/private/')) {
						resolve(file_doc);
					} else {
						frappe.call({
							method: 'nitta_note_app.nitta_note_app.doctype.non_financial_note.non_financial_note.remove_file_backgroud',
							args: {
								files: [file_doc.name],
							},
							freeze: true,
							callback: (r) => {
								frappe.msgprint("select Private file")
							},
							error: (r) => {
								frappe.msgprint(r)
							}
						})
					}
				}
			});
		});
		return file_doc;
	},
	remove_unused_files: function (frm) {
		frappe.call({
			method: 'nitta_note_app.nitta_note_app.doctype.non_financial_note.non_financial_note.remove_unused_files',
			args: {
				doctype: frm.doctype,
				docname: frm.docname
			},
			freeze: true,
			error: (r) => {
				frappe.msgprint(r)
			}
		})
	},
});

/////////////////child tables/////////////////////////////////

frappe.ui.form.on('Nitta Approval Flow', {
	department(frm, cdt, cdn) {
		let child = locals[cdt][cdn]
		// Reset role in department change
		frappe.model.set_value(child.doctype, child.name, 'role', undefined)
	},
	role(frm, cdt, cdn) {
		let child = locals[cdt][cdn]
		// Reset user in role change
		frappe.model.set_value(child.doctype, child.name, 'nitta_user', undefined)
	},
	before_approval_flow_remove(frm, cdt, cdn) {
		let child = locals[cdt][cdn]
		// prevent deletion of non editable row
		if (child.is_editable != true && frappe.session.user != "Administrator") {
			frappe.throw("Can't delete this row")
		}
	}
});

frappe.ui.form.on('Nitta CC', {
	department(frm, cdt, cdn) {
		let child = locals[cdt][cdn]
		// Reset role in department change
		frappe.model.set_value(child.doctype, child.name, 'role', undefined)
	},
	role(frm, cdt, cdn) {
		let child = locals[cdt][cdn]
		// Reset user in role change
		frappe.model.set_value(child.doctype, child.name, 'nitta_user', undefined)
	}
});

frappe.ui.form.on('Nitta Attachments', {
	download(frm, cdt, cdn) {
		let child = locals[cdt][cdn]
		window.open(child.attachment)
	},
	upload: async function (frm, cdt, cdn) {
		if (frappe.user.name == 'Administrator' || frm.doc.status == 'Draft' || frm.doc.status.toLowerCase().indexOf('modify') > -1) {
			let file_doc = await frm.events.uploadPrivateFile(frm);
			frappe.model.set_value(cdt, cdn, "attachment", file_doc.file_url);
			frappe.model.set_value(cdt, cdn, "file_name", file_doc.name);
		}
	}
});
