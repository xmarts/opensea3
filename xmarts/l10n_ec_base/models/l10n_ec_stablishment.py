# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class L10nEcStablishment(models.Model):
	_name = "l10n.ec.stablishment"
	_description = "Stablishment"
	_rec_name = "emission_point_prefix"
	_sql_constraints = [(
		"emission_unique",
		"unique(name,entity_id,company_id)",
		"You cannot duplicate emission points"
	)]

	active = fields.Boolean(
		default=True,
		string="Active"
	)
	name = fields.Char(
		string="Stablishment",
		required=True,
		size=3
	)
	entity_id = fields.Many2one(
		"l10n.ec.emission",
		string="Print point",
		required=True
	)
	company_id = fields.Many2one(
		"res.company",
		string="Company",
		default=lambda self: self.env.user.company_id
	)
	emission_point_prefix = fields.Char(
		string="Emission Point Prefix",
		compute="_get_prefix_name",
		store=True
	)
	electronic_invoice = fields.Boolean(
		string="Allow electronic invoice",
		default=True
	)
	electronic_creditnote = fields.Boolean(
		string="Allow electronic credit note",
		default=True
	)
	electronic_debitnote = fields.Boolean(
		string="Allow electronic debit note",
		default=True
	)
	electronic_liqpurchase = fields.Boolean(
		string="Allow electronic liq purchase note",
		default=True
	)
	electronic_withholding = fields.Boolean(
		string="Allow electronic withholding",
		default=True
	)
	invoice_sequence_id = fields.Many2one(
		"ir.sequence",
		string="Invoice Sequence"
	)
	creditnote_sequence_id = fields.Many2one(
		"ir.sequence",
		string="Credit Note Sequence"
	)
	debitnote_sequence_id = fields.Many2one(
		"ir.sequence",
		string="Debit Note Sequence"
	)
	liqpurchase_sequence_id = fields.Many2one(
		"ir.sequence",
		string="Liq Purchase Sequence"
	)
	withholding_sequence_id = fields.Many2one(
		"ir.sequence",
		string="Withholding Sequence"
	)
	invoice_journal_id = fields.Many2one(
		"account.journal",
		string="Invoice Journal"
	)
	creditnote_journal_id = fields.Many2one(
		"account.journal",
		string="Invoice Journal"
	)
	liqpurchase_journal_id = fields.Many2one(
		"account.journal",
		string="Invoice Journal"
	)

	@api.depends("name", "entity_id")
	def _get_prefix_name(self):
		for point in self:
			point.emission_point_prefix = u"{0}-{1}".format(
				point.name,
				point.entity_id.name,
			)

	@api.model
	def create(self, vals):
		""" Create sequence for earch document"""
		entity = self.env["l10n.ec.emission"].browse(vals["entity_id"])
		name = "{}-{}".format(vals["name"], entity.name)
		vals.update({
			"invoice_sequence_id": self.env["ir.sequence"].create({
				"name": "{}-invoice".format(name),
				"padding": 9
			}).id,
			"creditnote_sequence_id":  self.env["ir.sequence"].create({
				"name": "{}-creditnote".format(name),
				"padding": 9
			}).id,
			"debitnote_sequence_id": self.env["ir.sequence"].create({
				"name": "{}-debitnote".format(name),
				"padding": 9
			}).id,
			"liqpurchase_sequence_id": self.env["ir.sequence"].create({
				"name": "{}-liqpurchase".format(name),
				"padding": 9
			}).id,
			"withholding_sequence_id": self.env["ir.sequence"].create({
				"name": "{}-withholding".format(name),
				"padding": 9
			}).id,
		})
		return super(L10nEcStablishment, self).create(vals)

	def unlink(self):
		""" Overwrite unlink method """
		for point in self:
			res = self.env["account.move"].search(
				[("l10n_ec_emission_point_id", "=", point.id)]
			)
			if res:
				raise ValidationError(
					"This emission point is related to a document. ()".format(
						[i.name for i in res])
				)
		return super(self, L10nEcStablishment).unlink()
