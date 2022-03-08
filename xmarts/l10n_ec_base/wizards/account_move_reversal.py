from odoo import api, fields, models, _


class AccountMoveReversal(models.TransientModel):
	_inherit = "account.move.reversal"

	l10n_ec_emission_point_id = fields.Many2one(
		"l10n.ec.stablishment",
		string="Emission Point",
		compute="_compute_l10n_ec_emission_point_id"
	)
	auth_number = fields.Char(
		string="Purchase Invoice Authorization",
		size=49
	)

	@api.depends('move_ids')
	def _compute_l10n_ec_emission_point_id(self):
		for record in self:
			move_ids = record.move_ids._origin
			record.residual = len(move_ids) == 1 and move_ids.amount_residual or 0
			record.currency_id = len(move_ids.currency_id) == 1 and move_ids.currency_id or False
			record.l10n_ec_emission_point_id = move_ids.l10n_ec_emission_point_id if len(move_ids) == 1 else (any(move.l10n_ec_emission_point_id for move in move_ids) or False)

	@api.depends("l10n_latam_document_type_id")
	def _compute_l10n_latam_manual_document_number(self):
		self.l10n_latam_manual_document_number = False
		for rec in self.filtered('move_ids'):
			move = rec.move_ids[0]
			if move.journal_id and move.journal_id.l10n_latam_use_documents:
				rec.l10n_latam_manual_document_number = (
					self.env['account.move']._is_manual_document_number(move.journal_id, move)
				)

	def _prepare_default_reversal(self, move):
		""" Set the default document type and number in the new 
		revsersal move taking into account the ones selected in
		the wizard """
		res = super(AccountMoveReversal, self)._prepare_default_reversal(move)
		res.update({
			"l10n_latam_document_number": "",
			"ref": self.reason,
			"auto_post": False,
			"auth_number": self.auth_number,
			"l10n_ec_emission_point_id": self.l10n_ec_emission_point_id.id,
		})
		return res
