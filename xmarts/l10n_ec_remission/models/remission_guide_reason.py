from odoo import fields, models


class RemissionGuideReason(models.Model):
	_name = "remission.guide.reason"
	_description = "Remission Guide Reason"
	_sql_constraints = [(
		"name_unique",
		"unique(name)",
		"You cannot duplicate reason"
	)]

	name = fields.Char(string="Name")
