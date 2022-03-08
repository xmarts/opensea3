from odoo import fields, models


class ResCompany(models.Model):
	_inherit = "res.company"

	code_cash_management = fields.Char(string="Cash management company code")
