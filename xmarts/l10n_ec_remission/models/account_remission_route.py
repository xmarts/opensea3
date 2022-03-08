from odoo import api, fields, models


class AccountRemissionRoute(models.Model):
	_name = "account.remission.route"
	_description = "Routes for Remission Guide"

	name = fields.Char(string="Name")
