from odoo import fields, models


class L10nEcSriPayment(models.Model):
	_name = "l10n.ec.sri.payment"
	_description = "Sri Payment Methods"

	name = fields.Char(string="Name")
	code = fields.Char(string="Code")