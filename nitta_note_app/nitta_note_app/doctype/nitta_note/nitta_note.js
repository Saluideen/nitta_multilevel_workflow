// Copyright (c) 2023, Sajith K and contributors
// For license information, please see license.txt
// frappe.require([
// 	"assets/nitta_note_app/css/workflow_table.css",
// ]);

frappe.ui.form.on('Nitta Note', {

	///////////////////////////////// Events /////////////////////////////////////////
	validate: function (frm) {
		if (frm.doc.project_start_date && frm.doc.project_completion_date) {
			let project_start_date = new Date(frm.doc.project_start_date)
			let project_completion_date = new Date(frm.doc.project_completion_date)
			if (project_completion_date < project_start_date) {
				frappe.msgprint('Completion Date should be greater than Start Date')
				frappe.validated = false
			}
		}

		if (frm.doc.expected_amount <= 0) {
			frappe.msgprint('Expected amount should be greater than 1')
			frappe.validated = false
		}

		if (frm.doc.gl_account_no || frm.doc.sn_in_budget_sheet) {
			if (frm.doc.expected_amount > frm.doc.budget_amount_rs) {
				return new Promise(function (resolve, reject) {
					frappe.confirm(
						"<h5>Expected amount is greater than Budgetted amount.</h5><br>Do you want to continue?",
						function () {
							var negative = 'frappe.validated = false';
							resolve(negative);
						},
						function () {
							reject();
						}
					)
				})
			}
		}
	},

	refresh: function (frm) {

		if (frm.is_new()) {
			frm.set_df_property("other_attachments", "hidden", 1)
			frm.set_df_property("vendors", "hidden", 1)
			frm.set_df_property("technical_comparision", "hidden", 1)
			frm.set_df_property("view_technical_comparision", "hidden", 1)
			frm.set_df_property("upload_technical_comparison", "hidden", 1)
			frm.set_df_property("upload_commercial_comparison", "hidden", 1)
			frm.doc.note_no = undefined
			frm.doc.date = undefined
			frm.refresh_field('note_no')
			frm.refresh_field('date')
		} else {
			frm.set_df_property("other_attachments", "hidden", 0)
			frm.set_df_property("vendors", "hidden", 0)
			frm.set_df_property("technical_comparision", "hidden", 0)
			frm.set_df_property("view_technical_comparision", "hidden", 0)
			frm.set_df_property("upload_technical_comparison", "hidden", 0)
			frm.set_df_property("upload_commercial_comparison", "hidden", 0)

			// frm.events.remove_unused_files(frm) 
			frm.events.download_pdf_setting(frm)
		}

		if (frm.is_new() || frm.doc.status == "Draft") {
			frm.set_df_property("revised_amount", "hidden", 1)
		}

		// To remove Dulicate and other menu items
		// frm.page.clear_menu()
		// cur_frm.page.menu_btn_group.find(`[data-label="Duplicate"]`).parent().parent().remove()

		// add default value to other attachments and disable attachment button
		frm.events.attachment_settings(frm)

		// add default value to cost estimate table
		frm.events.cost_estimate_settings(frm)

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

		//set financial field
		frm.events.set_financial_field(frm)

		//set pre approval check box
		frm.events.set_preapproval(frm)

		//set internal order no update button
		frm.events.internal_order_no_setting(frm)

		frm.events.technical_comparision_ui(frm)

		frm.events.set_cancel_button(frm)
	},
	financial_year: function (frm) {
		frm.events.clear_financial_field(frm)
		frm.events.set_financial_field(frm)
	},
	division: function (frm) {
		if (!frm.doc.division) {
			frm.doc.departmentfunction = undefined;
			frm.refresh_field('departmentfunction')
		}
		else {
			frm.events.set_department(frm);
		}

		frm.events.clear_financial_field(frm)
		frm.events.set_financial_field(frm)

	},
	expense_category: function (frm) {

		frm.events.clear_financial_field(frm)
		frm.doc.item_category = undefined
		frm.refresh_field('item_category')
		frm.events.set_financial_field(frm)
		frm.set_query('item_category', function () {
			return {
				"filters": {
					'expense_category': frm.doc.expense_category
				}
			}
		})
		frm.events.set_preapproval(frm)
	},
	item_category: function (frm) {
		frm.events.set_preapproval(frm)
	},
	gl_account_no: function (frm) {
		// Getting GL Details
		frm.doc.budget_amount_rs = 0;
		frm.refresh_field("budget_amount_rs");
		frm.doc.description = undefined;
		frm.refresh_field("description");
		frm.doc.internal_order_no = undefined;
		frm.refresh_field("internal_order_no");
		frm.doc.sn_in_budget_sheet = undefined;
		frm.refresh_field("sn_in_budget_sheet");

		frappe.call({
			method: "nitta_note_app.nitta_note_app.doctype.nitta_note.nitta_note.get_gl_details",
			args: {
				name: frm.doc.gl_account_no ? frm.doc.gl_account_no : 'undefined',
				note_name: frm.doc.name
			},
			freeze: true,
			callback: function (r) {
				let data = r.message.data
				frm.doc.budget_amount_rs = data[0].budget_amount;
				frm.refresh_field("budget_amount_rs");
				frm.doc.description = data[0].description;
				frm.refresh_field("description");
			},
			error: function (err) {
				frappe.msgprint(err);
			}
		});
	},
	sn_in_budget_sheet: function (frm) {
		// Getting Budget details
		frm.doc.budget_amount_rs = 0;
		frm.refresh_field("budget_amount_rs");
		frm.doc.description = undefined;
		frm.refresh_field("description");
		frm.doc.gl_account_no = undefined;
		frm.refresh_field("gl_account_no");
		frm.doc.internal_order_no = undefined;
		frm.refresh_field("internal_order_no");
		frappe.call({
			method: "nitta_note_app.nitta_note_app.doctype.nitta_note.nitta_note.capex_expense_details",
			args: {
				name: frm.doc.sn_in_budget_sheet ? frm.doc.sn_in_budget_sheet : 'undefined',
				note_name: frm.doc.name
			},
			freeze: true,
			callback: function (r) {
				let data = r.message.data
				frm.doc.budget_amount_rs = data[0].amount;
				frm.refresh_field("budget_amount_rs");
				frm.doc.description = data[0].project;
				frm.refresh_field("description");
			},
			error: function (err) {
				frappe.msgprint(err);
			}
		});
	},
	work_flow_name: function (frm) {
		// Getting Workflow Trasitions
		frappe.call({
			method: "nitta_note_app.nitta_note_app.doctype.nitta_note.nitta_note.get_workflow_transition",
			args: {
				work_flow_name: frm.doc.work_flow_name ? frm.doc.work_flow_name : 'undefined',
				division: frm.doc.division ? frm.doc.division : 'undefined',
				note_department: frm.doc.departmentfunction ? frm.doc.departmentfunction : 'undefined'
			},
			freeze: true,
			callback: function (r) {
				let data = r.message.data
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
			method: "nitta_note_app.nitta_note_app.doctype.nitta_note.nitta_note.get_copy_to",
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
	download_technical_comparison: async function (frm) {
		window.open(frm.doc.technical_comparison_file)
	},
	remove_technical_comparison: async function (frm) {
		if (frappe.user.name=='Administrator' || frm.doc.status == 'Draft' || frm.doc.status.toLowerCase().indexOf('modify') > -1) {
			frm.doc.technical_comparison_file_name = undefined;
			frm.doc.technical_comparison_file = undefined;
			frm.refresh_field("technical_comparison_file");
			frm.dirty();
		}
	},
	upload_technical_comparison: async function (frm) {
		if (frappe.user.name=='Administrator' || frm.doc.status == 'Draft' || frm.doc.status.toLowerCase().indexOf('modify') > -1) {
			let file_doc = await frm.events.uploadPrivateFile(frm)
			frm.doc.technical_comparison_file_name = file_doc.name;
			frm.doc.technical_comparison_file = file_doc.file_url;
			frm.refresh_field("technical_comparison_file")
			frm.dirty();
		}
	},
	download_commercial_comparison: async function (frm) {
		window.open(frm.doc.commercial_comparison_file)
	},
	remove_commercial_comparison: async function (frm) {
		if (frappe.user.name=='Administrator' || frm.doc.status == 'Draft' || frm.doc.status.toLowerCase().indexOf('modify') > -1) {
			frm.doc.commercial_comparison_file_name = undefined;
			frm.doc.commercial_comparison_file = undefined;
			frm.refresh_field("commercial_comparison_file");
			frm.dirty();
		}
	},
	upload_commercial_comparison: async function (frm) {
		if (frappe.user.name=='Administrator' || frm.doc.status == 'Draft' || frm.doc.status.toLowerCase().indexOf('modify') > -1) {
			let file_doc = await frm.events.uploadPrivateFile(frm)
			frm.doc.commercial_comparison_file_name = file_doc.name;
			frm.doc.commercial_comparison_file = file_doc.file_url;
			frm.refresh_field("commercial_comparison_file")
			frm.dirty();
		}
	},
	proposal_type: function (frm) {
		if (frm.doc.proposal_type == 'Full Proposal') {
			frm.doc.is_pre_approval_note = false;
		} else {
			frm.doc.is_pre_approval_note = true;
		}
		frm.refresh_field("is_pre_approval_note");
		frm.dirty();
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
				query: "nitta_note_app.nitta_note_app.doctype.nitta_note.nitta_note.get_divisions",
				filters: { "user": frappe.session.user }
			};
		});

		if (!frm.doc.division) {
			frappe.call({
				method: 'nitta_note_app.nitta_note_app.doctype.nitta_note.nitta_note.get_divisions',
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
				query: "nitta_note_app.nitta_note_app.doctype.nitta_note.nitta_note.get_department",
				filters: { "user": frappe.session.user, "division": frm.doc.division ? frm.doc.division : 'undefined' }
			};
		});

		if (!frm.doc.departmentfunction) {
			frappe.call({
				method: 'nitta_note_app.nitta_note_app.doctype.nitta_note.nitta_note.get_department',
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
				query: "nitta_note_app.nitta_note_app.doctype.nitta_note.nitta_note.get_department_role",
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
				query: "nitta_note_app.nitta_note_app.doctype.nitta_note.nitta_note.get_nitta_user",
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
				query: "nitta_note_app.nitta_note_app.doctype.nitta_note.nitta_note.get_department_role",
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
				query: "nitta_note_app.nitta_note_app.doctype.nitta_note.nitta_note.get_nitta_user",
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
			method: 'nitta_note_app.nitta_note_app.doctype.nitta_note.nitta_note.get_entity_type',
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
					expense_category: frm.doc.expense_category,
					budget_provision: frm.doc.budget_provision,
					item_category: frm.doc.item_category,
					lower_limit: ['<=', frm.doc.expected_amount],
					upper_limit: ['>=', frm.doc.expected_amount],
					is_pre_approval: frm.doc.is_pre_approval_note,
					note_type: 'Financial',
					entity_type: ['in', entity_type]
				}
			}
		})
	},
	attachment_settings: function (frm) {
		//disable sidebar attachments section
		$(".form-attachments").hide();

		if (frm.is_new()) {
			//add default names to attachment table
			let attachments = ['ROI worksheet (for Capital projects)', 'Techno commercial comparison', 'Estimate of the work']
			attachments.forEach(element => {

				let found = false
				if (frm.doc.other_attachments) {
					found = frm.doc.other_attachments.find(function (record) {
						return record.name1 === element;
					});
				}
				if (!found) {
					frm.add_child('other_attachments', {
						name1: element
					});

				}

			});

			frm.refresh_field("other_attachments")
		}
	},
	cost_estimate_settings: function (frm) {
		if (frm.is_new()) {
			// Add Default value for other amount
			let other_amount = ["Labour", "Material", "Tax"]
			other_amount.forEach(element => {
				let found = false
				if (frm.doc.cost_estimate) {
					found = frm.doc.cost_estimate.find(function (record) {
						return record.title === element;
					});
				}
				if (!found) {
					frm.add_child('cost_estimate', {
						title: element,
						amount: 0
					});
				}
			});

			frm.refresh_field("cost_estimate")
		}
	},
	texteditor_settings: function (frm) {
		$('.ql-editor').css({ height: '100px' });
	},
	download_pdf_setting: function (frm) {
		frm.add_custom_button("Preview", function () {
			frappe.call({
				method: 'nitta_note_app.nitta_note_app.doctype.nitta_note.nitta_note.download_pdf',
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
								method: 'nitta_note_app.nitta_note_app.doctype.nitta_note.nitta_note.change_status_to_cancel',
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
		frm.set_df_property("expense_category", 'read_only', value)
		frm.set_df_property("budget_provision", 'read_only', value)
		frm.set_df_property("item_category", 'read_only', value)
		frm.set_df_property("expected_amount", 'read_only', value)
		frm.set_df_property("division", 'read_only', value)
		frm.set_df_property("departmentfunction", 'read_only', value)
		frm.set_df_property("financial_year", 'read_only', value)
		frm.set_df_property("approval_flow", 'read_only', value)
		frm.set_df_property("work_flow_name", 'read_only', value)
		frm.set_df_property("copy_to", 'read_only', value)
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
							method: 'nitta_note_app.nitta_note_app.doctype.nitta_note.nitta_note.remove_file_backgroud',
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
			method: 'nitta_note_app.nitta_note_app.doctype.nitta_note.nitta_note.remove_unused_files',
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
	internal_order_no_setting: function (frm) {
		if (frm.doc.status == "Final Approved") {
			frm.add_custom_button("Update Internal Order No", function () {
				if (frm.doc.internal_order_no) {
					frappe.call({
						method: 'nitta_note_app.nitta_note_app.doctype.nitta_note.nitta_note.save_internal_order_no',
						args: { "name": frm.docname, "internal_order_no": frm.doc.internal_order_no },
						freeze: true,
						callback: (r) => {
							frappe.msgprint('Updated Internal Order Number')
						},
						error: (r) => {
							frappe.msgprint(r);
						}
					})
				}
				else {
					frappe.msgprint('Internal Order Number cannot be empty')
				}
			})
			frm.change_custom_button_type("Update Internal Order No", null, "primary");
			frm.set_df_property("internal_order_no", 'hidden', 0)
		} else {
			frm.set_df_property("internal_order_no", 'hidden', 1)
		}
	},
	set_preapproval: function (frm) {
		if (frm.doc.expense_category == 'Capex' && frm.doc.item_category == 'Capex Projects') {
			frm.set_df_property('proposal_type', 'hidden', 0)
		} else {
			frm.set_df_property('proposal_type', 'hidden', 1)
			frm.doc.is_pre_approval_note = 0
			frm.doc.proposal_type = 'Full Proposal'
		}
	},
	clear_financial_field: function (frm) {
		frm.doc.budget_amount_rs = 0;
		frm.refresh_field("budget_amount_rs");
		frm.doc.description = undefined;
		frm.refresh_field("description");
		frm.doc.gl_account_no = undefined;
		frm.refresh_field("gl_account_no");
		frm.doc.internal_order_no = undefined;
		frm.refresh_field("internal_order_no");
		frm.doc.sn_in_budget_sheet = undefined;
		frm.refresh_field("sn_in_budget_sheet");
	},
	set_financial_field: function (frm) {
		if (frm.doc.expense_category == 'Capex') {
			frm.set_df_property('sn_in_budget_sheet', 'hidden', 0);
			frm.set_df_property('gl_account_no', 'hidden', 1);
			frm.set_df_property('nature_of_expenditure', 'hidden', 0);
			frm.set_df_property('description', 'hidden', 0);
			frm.set_df_property('budget_amount_rs', 'hidden', 0);

			frm.set_query('sn_in_budget_sheet', function () {
				return {
					'filters': {
						'financial_year': frm.doc.financial_year ? frm.doc.financial_year : 'undefined',
						'division': frm.doc.division ? frm.doc.division : 'undefined'
					}
				}
			})

		} else if (frm.doc.expense_category == 'Revenue') {
			frm.set_df_property('sn_in_budget_sheet', 'hidden', 1);
			frm.set_df_property('gl_account_no', 'hidden', 0);
			frm.set_df_property('nature_of_expenditure', 'hidden', 1);
			frm.set_df_property('description', 'hidden', 0);
			frm.set_df_property('budget_amount_rs', 'hidden', 0);


			frm.set_query('gl_account_no', function () {
				return {
					'filters': {
						'financial_year': frm.doc.financial_year ? frm.doc.financial_year : 'undefined',
						'division': frm.doc.division ? frm.doc.division : 'undefined'
					}
				}
			})
		} else {
			frm.set_df_property('sn_in_budget_sheet', 'hidden', 1);
			frm.set_df_property('description', 'hidden', 1);
			frm.set_df_property('budget_amount_rs', 'hidden', 1);
			frm.set_df_property('nature_of_expenditure', 'hidden', 1);
			frm.set_df_property('gl_account_no', 'hidden', 1);

		}

	},
	amount_calculation: function (frm, cdt, cdn) {
		let child = locals[cdt][cdn]
		child.amount = parseFloat(child.quantity ? child.quantity : 0) * parseFloat(child.price ? child.price : 0)
		frm.refresh_field('cost_estimate')
		frm.events.expected_amount_calculation(frm)
	},
	expected_amount_calculation: function (frm) {
		let other_amount = 0
		if (frm.doc.cost_estimate) {
			frm.doc.cost_estimate.forEach((el) => {
				other_amount += parseFloat((el.amount ? el.amount : 0))
			})
		}
		if (frm.is_new() || frm.doc.status == "Draft") {
			frm.doc.expected_amount = other_amount
			frm.refresh_field('expected_amount')
		} else {
			frm.doc.revised_amount = other_amount
			frm.refresh_field('revised_amount')
		}
	},
	technical_comparision_ui: function (frm) {
		let comparison_array = frm.doc.technical_comparision || []
		let ui_vendors = []
		let ui_parameter = []
		let ui_data = new Array()
		let i = 0
		let j = 0

		for (let i = 0; i < comparison_array.length; i++) {
			ui_data[i] = new Array()
		}

		comparison_array.forEach((el) => {
			if (el.vendor && el.parameter) {
				if (!ui_vendors.some((v) => v.vendor == el.vendor)) {
					ui_vendors.push({ vendor: el.vendor, index: i })
					i++
				}
				if (!ui_parameter.some((v) => v.parameter == el.parameter)) {
					ui_parameter.push({ parameter: el.parameter, index: j })
					j++
				}
				// finding 2D Index
				let vendor_index = ui_vendors.findIndex((f) => f.vendor == el.vendor)
				let parameter_index = ui_parameter.findIndex((f) => f.parameter == el.parameter)
				ui_data[parameter_index][vendor_index] = el.data
			}
		})

		// Set View Html component
		if (comparison_array.length == 0) {
			frm.set_df_property('view_technical_comparision', 'hidden', 1)
		} else {
			frm.set_df_property('view_technical_comparision', 'hidden', 0)
			// Adding data to Html component
			$(frappe.render_template("technical_comparision_ui", {
				vendors: ui_vendors,
				parameters: ui_parameter,
				data: ui_data
			})
			).appendTo(frm.fields_dict.view_technical_comparision.$wrapper.empty());

		}
	}
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

frappe.ui.form.on('Nitta Vendor Quotations', {
	download(frm, cdt, cdn) {
		let child = locals[cdt][cdn]
		window.open(child.document)
	},
	upload: async function (frm, cdt, cdn) {
		if (frappe.user.name=='Administrator' || frm.doc.status == 'Draft' || frm.doc.status.toLowerCase().indexOf('modify') > -1) {
			let file_doc = await frm.events.uploadPrivateFile(frm);
			frappe.model.set_value(cdt, cdn, "file_name", file_doc.name);
			frappe.model.set_value(cdt, cdn, "document", file_doc.file_url);
		}
	}
});

frappe.ui.form.on('Nitta Attachments', {
	download(frm, cdt, cdn) {
		let child = locals[cdt][cdn]
		window.open(child.attachment)
	},
	upload: async function (frm, cdt, cdn) {
		if (frappe.user.name=='Administrator' || frm.doc.status == 'Draft' || frm.doc.status.toLowerCase().indexOf('modify') > -1) {
			let file_doc = await frm.events.uploadPrivateFile(frm);
			frappe.model.set_value(cdt, cdn, "attachment", file_doc.file_url);
			frappe.model.set_value(cdt, cdn, "file_name", file_doc.name);
		}
	}
});

frappe.ui.form.on('Nitta Technical Comparision', {
	technical_comparision_remove(frm, cdt, cdn) {
		frm.events.technical_comparision_ui(frm)
	},
	vendor(frm, cdt, cdn) {
		frm.events.technical_comparision_ui(frm)
	},
	data(frm, cdt, cdn) {
		frm.events.technical_comparision_ui(frm)
	},
	parameter(frm, cdt, cdn) {
		frm.events.technical_comparision_ui(frm)
	}
});

frappe.ui.form.on('Nitta Other Amount', {
	cost_estimate_remove(frm, cdt, cdn) {
		frm.events.expected_amount_calculation(frm)
	},
	amount(frm, cdt, cdn) {
		frm.events.expected_amount_calculation(frm)
	},
	quantity(frm, cdt, cdn) {
		frm.events.amount_calculation(frm, cdt, cdn)
	},
	price(frm, cdt, cdn) {
		frm.events.amount_calculation(frm, cdt, cdn)
	}
});