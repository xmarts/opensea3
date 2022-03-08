# -*- coding: utf-8 -*-

from odoo import api, fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    l10n_ec_sri_key_id = fields.Many2one(
	    "l10n.ec.sri.key",
	    string="Electronic Sign"
    )
    emission_code = fields.Selection([
        ("1", "Normal"),
        ("2", "Indisponibilidad")],
        string="Emission Type",
        required=True,
        default="1"
    )
    env_service = fields.Selection([
	    ("1", "Test"),
        ("2", "Production")],
        string="Environment Type",
        required=True,
        default="1"
    )


