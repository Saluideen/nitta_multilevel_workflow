# Copyright (c) 2023, Sajith K and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class NittademoWorkflow(Document):
	# pass
	def before_save(self):
		transition_rows = self.transition
		level_counts = {}

		# Iterate through child table rows to calculate total counts for each level
		for row in transition_rows:
			level = row.level
  
			# Initialize the count if it doesn't exist
			if level not in level_counts:
				level_counts[level] = 0

			# Increment the total count for the current level
			level_counts[level] += 1
		# Sort transition_rows based on the "level" field
		transition_rows = sorted(transition_rows, key=lambda x: x.level)

		# Update the "level_count" field for each row with the total count for its level
		for row in transition_rows:
			level = row.level
			row.level_count = level_counts.get(level, 0)
		
