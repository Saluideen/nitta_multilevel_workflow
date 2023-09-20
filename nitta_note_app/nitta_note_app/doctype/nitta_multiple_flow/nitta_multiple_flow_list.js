frappe.listview_settings['Nitta Multiple flow'] = {
    add_fields: ['status'],
    hide_name_column: true,
    get_indicator(doc) {
        if (doc.status == 'Initiated') {
            return [doc.status, 'yellow', 'status,=,' + doc.status];
        }
        if (doc.status.includes('Level')) {
            if (doc.status.includes('Rejected')) {
                return [doc.status, 'red', 'status,like,%Level%Rejected%'];
            }
            if (doc.status.includes('Approved')) {
                return [doc.status, 'green', 'status,like,%Level%Approved%'];
            }
            return [doc.status, 'blue', 'status,like,%Level%'];
        }
        if (doc.status.includes('Final Approved')) {
            return [doc.status, 'green', 'status,like,Final Approved'];
        }
        if (doc.status.includes('Rejected')) {
            return [doc.status, 'red', 'status,like,Rejected'];
        }
        // Default case: No specific color
        return [doc.status, '', ''];
    },
};
