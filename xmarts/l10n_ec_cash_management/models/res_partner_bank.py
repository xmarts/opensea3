from odoo import api, fields, models


class ResPartnerBank(models.Model):
	_inherit = "res.partner.bank"

	bank_acc_type = fields.Selection([
		("AHO", "Ahorros"),
		("CTE", "Corriente"),
		("VIR", "Virtual")],
		string="Account Type",
		default="AHO",
	)
