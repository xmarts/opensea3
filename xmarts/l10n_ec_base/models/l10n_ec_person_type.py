from odoo import fields, models


class L10nEcPersonType(models.Model):
	_name = "l10n.ec.person.type"
	_description = "Person Type"
	_sql_constraints = [(
		"name_unique",
		"unique(name)",
		"This person type already exists"
	)]

	active = fields.Boolean(
		string="Active",
		default=True
	)
	code = fields.Char(
		string="Code",
		required=True
	)
	name = fields.Char(
		string="Person type",
		required=True
	)
