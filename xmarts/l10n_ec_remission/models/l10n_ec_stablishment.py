# -*- coding: utf-8 -*-

from odoo import api, fields, models


class L10nEcEmission(models.Model):
	_inherit = "l10n.ec.stablishment"

	electronic_remission = fields.Boolean(
		string="Allow electronic remission",
		default=True
	)
	remission_guide_sequence_id = fields.Many2one(
		"ir.sequence",
		string="Remission Guide Sequence"
	)
