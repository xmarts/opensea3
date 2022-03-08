# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class L10nLatamIdentificationType(models.Model):
	_name = "l10n_latam.identification.type"
	_inherit = "l10n_latam.identification.type"

	code = fields.Char(string="Code")
