# -*- coding: utf-8 -*-

from odoo import api, fields, models


class ResPartner(models.Model):
	_inherit = "res.partner"

	is_carrier = fields.Boolean(
		string="Is Carrier?",
		default=False
	)
