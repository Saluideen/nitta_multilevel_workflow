// Copyright (c) 2023, Sajith K and contributors
// For license information, please see license.txt

frappe.ui.form.on("Nitta Multiple flow", {
  refresh: function (frm) {
    //  Initiate Button
    frm.events.initiate_button(frm);

    // Approve ,Reject and ownership_change,Assign Button
    frm.events.buttons(frm);
  },


  initiate_button: function (frm) {
    if (!frm.is_new() && frm.doc.status == "Draft") {
      cur_frm.page.add_action_item("Initiate", function () {
        frm.doc.status = "Initiated";
        frm.refresh_field("status");
        frm.dirty();
        frm.save();
      });
      frm.change_custom_button_type("Initiate", null, "primary");
    }
  },
  buttons: function (frm) {
    if (frm.doc.next_approval_by.includes(frappe.session.user)) {
      let is_approved = false;
      let is_pending = false; //for ownership
      let is_ownership = false;
      for (let i of frm.doc.workflow) {
        if (
          i.user == frappe.session.user &&
          (i.status == "Approved" || i.status == "Ownership Changed")
        ) {
          is_approved = true;
        }
        if (i.user == frappe.session.user && i.status == "Pending") {
          is_pending = true;
        }
        if (i.user == frappe.session.user && i.status == "Ownership Changed") {
          is_ownership = true;
        }
      }

      if (is_approved == false) {
        frm.page.add_action_item("Approve", () => {
          var index = frm.doc.workflow.findIndex(
            (el) => el.user == frappe.session.user && el.status != "Approved"
          );
          frm.doc.workflow[index].status = "Approved";
          frm.refresh_field("workflow");
          frm.dirty();
          frm.save();
        });
      }

      // reject button
      if (is_approved == false) {
        frm.page.add_action_item("Reject ", () => {
          var index = frm.doc.workflow.findIndex(
            (el) => el.user == frappe.session.user && el.status != "Approved"
          );
          frm.doc.workflow[index].status = "Rejected";
          frm.refresh_field("workflow");
          frm.dirty();
          frm.save();
        });
      }
      if (is_ownership == false) {
        // Assign Button
        frm.page.add_action_item("Assign ", () => {
          frm.events.assign_user(frm, { status: "Assign" });
        });
      }
      // ownership button
      if (is_pending == true) {
        frm.page.add_action_item("Change Ownership", () => {
          var index = frm.doc.workflow.findIndex(
            (el) =>
              el.user == frappe.session.user && el.status != "Ownership Changed"
          );
          // frm.trigger("assign_user","Ownership changed")
          frm.events.assign_user(frm, { status: "Ownership Changed" });
          // frm.doc.workflow[index].status = "Ownership Changed";
          // frm.refresh_field("workflow");
          // frm.dirty();
          // frm.save();
        });
      }
    }
  },

  assign_user: function (frm, args) {
    let currentUserLevel = getCurrentUserLevel(frm);
    let status = args || "";
    console.log("status", status);

    // Create the dialog box
    var dialog = new frappe.ui.Dialog({
      title: __("Assign New Roles"),
      fields: [
        {
          fieldname: "department",
          label: __("Department"),
          fieldtype: "Link",
          in_list_view: 1,

          options: "Department and Function",
          reqd: 1,
        },
        {
          fieldname: "role",
          label: __("Role"),
          in_list_view: 1,

          fieldtype: "Link",
          options: "Nitta Role",
          reqd: 1,
        },
        {
          fieldname: "user",
          label: __("User"),
          in_list_view: 1,

          fieldtype: "Link",
          options: "Nitta User",
          reqd: 1,
          get_query: function () {
            if (dialog.get_value("department") && dialog.get_value("role")) {
              return {
                query:
                  "nitta_note_app.nitta_note_app.doctype.nitta_multiple_flow.nitta_multiple_flow.get_department",
                filters: {
                  department: dialog.get_value("department"),
                  role: dialog.get_value("role"),
                },
              };
            }
          },
        },
        {
          fieldname: "level",
          label: __("Level"),
          in_list_view: 1,

          fieldtype: "Link",
          options: "Nitta Level",
          reqd: 1,

          // Apply a filter to display levels greater than or equal to the current user's level
          get_query: function (frm) {
            return {
              filters: [["Nitta Level", "level", ">=", currentUserLevel]],
            };
          },
        },
        {
          fieldname: "alert_in_days",
          label: __("Alert in Days"),
          in_list_view: 1,
          default: "2",
          fieldtype: "Data",
          reqd: 1,
        },
      ],
      primary_action_label: __("Assign"),
      primary_action: function () {
        let values = dialog.get_values() || [];

        let child_table = frm.fields_dict["workflow"];

        if (values) {
          let is_found = false;
          if (frm.doc.workflow) {
            is_found = frm.doc.workflow.find(function (record) {
              return (
                record.department == values.department &&
                record.role == values.role &&
                record.user == values.user
              );
            });
          }
          if (!is_found) {
            let level_count = get_levelcount(values.level, frm);

            frm.add_child("workflow", {
              department: values.department,
              role: values.role,
              level: values.level,
              alert_in_days: values.alert_in_days,
              user: values.user,
              level_count: level_count,
            });
            // frm.save();
            // Change ownership status if a value was passed
            if (status.status == "Ownership Changed") {
              var index = frm.doc.workflow.findIndex(
                (el) =>
                  el.user == frappe.session.user &&
                  el.status != "Ownership Changed"
              );
              if (index !== -1) {
                frm.doc.workflow[index].status = "Ownership Changed";
              }
            }
          } else {
            frappe.msgprint("This assignment already exists.");
          }

          // set all data from child table to workflow array
          let workflow = get_workflow(frm);
          frm.clear_table("workflow");
          // Now, add all the data from the workflow array to the child table
          workflow.forEach(function (record) {
            frm.add_child("workflow", {
              department: record.department,
              role: record.role,
              level: record.level,
              alert_in_days: record.alert_in_days,
              user: record.user,
              level_count: record.level_count,
              status: record.status,
              assigned_date: record.assigned_date,
              updated_date: record.updated_date,
            });
          });

          frm.save();

          child_table.grid.refresh();
        }

        frm.refresh_field("workflow");

        dialog.hide();
      },
    });

    dialog.show();
  },
});

// Function to retrieve the current user's level from the 'workflow' child table
function getCurrentUserLevel(frm) {
  let childTableData = frm.doc.workflow || [];
  let currentUser = frappe.session.user;

  // Find the level for the current user
  var currentUserLevel = null;

  for (var i = 0; i < childTableData.length; i++) {
    if (childTableData[i].user === currentUser) {
      currentUserLevel = childTableData[i].level;
      break;
    }
  }

  return currentUserLevel;
}
// calculate level count after  assign new user
function get_levelcount(level, frm) {
  let childTableData = frm.doc.workflow || [];
  let level_count;
  for (var i = 0; i < childTableData.length; i++) {
    if (childTableData[i].level === level) {
      level_count = parseInt(childTableData[i].level_count) + 1;
      childTableData[i].level_count = level_count;
    }
  }

  return level_count;
}

function get_workflow(frm) {
  let workflow = [];
  let childTableData = frm.doc.workflow || [];

  for (var i = 0; i < childTableData.length; i++) {
    workflow.push(childTableData[i]);
  }
  workflow.sort((a, b) => {
    // Assuming "level" is a numeric property in each object
    return a.level - b.level;
  });

  return workflow;
}
