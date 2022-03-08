# -*- coding: utf-8 -*-

from odoo import fields, models


class L10nEcEmission(models.Model):
	_name = "l10n.ec.emission"
	_description = "Emission Point"
	_sql_constraints = [(
		"name_unique",
		"unique(name)",
		"You cannot duplicate emission points"
	)]

	active = fields.Boolean(
		string="Active",
		default=True
	)
	name = fields.Char(
		string="Emission point",
		required=True
	)
