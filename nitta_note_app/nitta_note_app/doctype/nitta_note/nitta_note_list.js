
frappe.require([
    "assets/nitta_note_app/css/workflow_table.css",
]);

frappe.listview_settings['Nitta Note'] = {
    add_fields: ['status'],
    hide_name_column: true,
    get_indicator(doc) {

        if (doc.status == 'Initiated')
            return [doc.status, 'yellow', 'status,=,' + doc.status]
        if (doc.status.includes('Modify'))
            return [doc.status, 'orange', 'status,=,' + doc.status]
    },
    onload(listview) {
        // triggers once before the list is loaded
        if(frappe.user.name!='Administrator'){
            // listview.page.actions.
            // find(`[data-label="Edit"],[data-label="Assign%20To"],
            // [data-label="Print"],[data-label="Apply%20Assignment%20Rule"]`).
            // parent().parent().remove()
            cur_list.page.actions_btn_group.hide()
            cur_list.page.custom_actions.hide()
            cur_list.page.menu_btn_group.hide()
        }
    },
};