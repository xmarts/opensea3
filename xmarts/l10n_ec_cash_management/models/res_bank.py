from odoo import models, fields, api, _


class ResBank(models.Model):
	_inherit = "res.bank"

	pichincha_bank_code = fields.Char(string="Pichincha Bank Code")
	guayaquil_bank_code = fields.Char(string="Guayaquil Bank Code")

