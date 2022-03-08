from odoo import fields, models


class AccountPaymentLine(models.Model):
	_inherit = "account.payment.line"

	bank_payment_method = fields.Selection([
			("CTA", "Crédito o débito a cuenta"),
			("CHQ", "Cheque"),
			("EFE", "Efectivo"),
			("REC", "Recaudación"),
		],
		string="Bank payment method",
		default="CTA",
	)
