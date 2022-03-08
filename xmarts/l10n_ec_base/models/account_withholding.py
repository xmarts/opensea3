from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

STATES_VALUE = {"draft": [("readonly", False)]}


class AccountWithholding(models.Model):
	_name = "account.withholding"
	_inherit = ["mail.thread", "mail.activity.mixin"]
	_description = "Withholding Documents"
	_order = "date DESC, name DESC"
	_sql_constraints = [(
		"unique_number_type",
		"unique(name,withholding_type,partner_id)",
		u"Withholding Number Might Be Unique."
	)]

	@api.constrains("move_id", "state")
	def _constrains_move_id(self):
		""" Validates there is not another withholding
		 for the same move that is not cancel
		:return: None
		"""
		for wh in self:
			rec = self.search([
				("id", "!=", wh.id),
				("move_id", "=", wh.move_id.id),
				("state", "!=", "cancel")])
			if rec:
				raise ValidationError(
					"There is already a withholding for"
					" this document. Cancel it first"
				)

	def _get_at_wh(self):
		""" Method for ATS """
		self.ensure_one()
		return {
			"retencion": True,
			"estabRetencion1": self.l10n_ec_emission_point_id.name,
			"ptoEmiRetencion1": self.l10n_ec_emission_point_id.entity_id.name,
			"secRetencion1": self.name[7:17],
			"autRetencion1": self.numero_autorizacion,
			"fechaEmiRet1": self.date.strftime('%d/%m/%Y')
		}

	# @api.onchange("move_id")
	# def _onchange_validate_tax_lines(self):
	# 	for wh in self:
	# 		if wh.move_wh_id and

	@api.depends("tax_ids.amount")
	def _compute_total(self):
		[
			ret.update({"amount_total": sum(tax.amount for tax in ret.tax_ids)})
			for ret in self
		]

	@api.constrains("name")
	def _validate_document_number(self):
		for wh in self:
			wh.l10n_latam_document_type_id._format_document_number(wh.name)

	@api.onchange("move_id")
	def _onchange_move_id(self):
		""" Change taxes if invoice change """
		for wh in self:
			wh.tax_ids = [(5,)]
			wh.tax_ids = wh.move_id.invoice_line_ids._get_withholding_line()

	@api.onchange("date")
	@api.constrains("date")
	def _check_date(self):
		""" Validates Withholding Date"""
		for wh in self:
			if wh.date and wh.move_id:
				days = wh.date - wh.move_id.date
				if days.days > 6:
					raise ValidationError(
						u"Error en fecha de retención. Tiene "
						u"5 días desde la fecha de factura para"
						u" aplicar una retención."
					)

	def unlink(self):
		for wh in self:
			if wh.state == "done" or wh.move_wh_id.posted_before:
				raise ValidationError(
					"Can't unlink if the withholding "
					"is validated or it was posted."
				)
		res = super().unlink()
		return res

	def _action_number(self):
		""" Writes the withholding sequence and set state done
        :return:
        """
		for wh in self:
			if (
					wh.move_wh_id and
					wh.move_wh_id.posted_before
					or wh.withholding_type != "in_invoice"
			):
				continue
			emission_point = wh.l10n_ec_emission_point_id
			if wh.move_id:
				emission_point = wh.move_id.l10n_ec_emission_point_id
			wh.name = "{}-{}".format(
				emission_point.emission_point_prefix,
				emission_point.withholding_sequence_id.next_by_id()
			)
		return True

	def button_validate(self):
		""" Botón de validación.
		 Añade secuencia a la retención y crea asiento
		 :return True
        """
		for wh in self:
			if not wh.tax_ids:
				raise ValidationError(
					"There are not taxes in the withholding lines.")
			wh._action_number()
			wh.move_id.write({"withholding_id": wh.id})
			wh.create_move()
			wh.state = "done"
		return True

	def _get_move_lines(self):
		self.ensure_one()
		return [(0, 0, {
			"partner_id": self.partner_id.id,
			"account_id": (
				line.tax_id.invoice_repartition_line_ids[-1].account_id.id
			),
			"name": self.name,
			"credit": abs(line.amount),
			"debit": 0.00
		}) for line in self.tax_ids] + [(0, 0, {
			"partner_id": self.partner_id.id,
			"account_id": (
				self.withholding_type == "in_invoice"
				and self.partner_id.property_account_payable_id.id
				or self.move_id.partner_id.property_account_receivable_id.id
			),
			"name": self.name,
			"credit": 0.00,
			"debit": abs(self.amount_total)
		})]

	def _create_move(self):
		self.ensure_one()
		move_id = self.env["account.move"].create({
			"partner_id": self.partner_id.id,
			"move_type": "entry",
			"journal_id": self.move_id.journal_id.id,
			"l10n_latam_document_number": self.name,
			"l10n_latam_document_type_id": (
				self.l10n_latam_document_type_id.id),
			"ref": self.name,
			"date": self.date,
			"line_ids": self._get_move_lines()
		})
		move_id.action_post()
		self.move_wh_id = move_id.id
		return move_id

	def create_move(self):
		"""
        Generacion de asiento contable para aplicar como
        pago a factura relacionada;
        :return: account.move(records)
        """
		validate_line = lambda line: (
				line.account_id.reconcile
				and line.account_id.internal_type in ("receivable", "payable")
				and not line.reconciled
		)
		move_ids = self.env["account.move"]
		for wh in self:
			move_id = wh._create_move()
			(
					move_id.line_ids.filtered(validate_line)
					+ wh.move_id.line_ids.filtered(validate_line)
			).reconcile()
			move_ids |= move_id
			wh.write({"state": "done"})
		return move_ids

	def button_cancel(self):
		""" Cancel withholding and withholding move
		:return: True
		"""
		for wh in self:
			if wh.move_wh_id:
				if wh.move_wh_id:
					wh.move_wh_id.button_draft()
					wh.move_wh_id.button_cancel()
			wh.state = "cancel"
			return True

	def button_draft(self):
		""" Set to draft
		:return: True
		"""
		for wh in self:
			wh.state = "draft"
			return True

	@api.model
	def _get_default_name(self):
		if self.env.context.get("withholding_type") == "in_invoice":
			return "/"

	@api.model
	def _get_document_type(self):
		doc_type = False
		if self.env.context.get("withholding_type") == "in_invoice":
			doc_type = self.env["l10n_latam.document.type"].search(
				[("l10n_ec_type", "=", "in_withhold")])
		elif self.env.context.get("withholding_type") == "out_invoice":
			doc_type = self.env["l10n_latam.document.type"].search(
				[("l10n_ec_type", "=", "out_withhold")])
		return doc_type

	company_id = fields.Many2one(
		"res.company",
		string="Company",
		required=True,
		change_default=True,
		readonly=True,
		states={"draft": [("readonly", False)]},
		default=lambda self: self.env.user.company_id
	)
	name = fields.Char(
		string="Withholding Number",
		size=17,
		default=lambda self: self._get_default_name(),
		copy=False
	)
	manual = fields.Boolean(
		string="Manual Number",
		readonly=True,
		states=STATES_VALUE,
		default=True
	)
	l10n_ec_emission_point_id = fields.Many2one(
		"l10n.ec.stablishment",
		string="Emission Point",
		states=STATES_VALUE,
		default=lambda self: self.env.user.l10n_ec_emission_point_id
	)
	withholding_type = fields.Selection([
		("in_invoice", u"Supplier Wittholding"),
		("out_invoice", u"Customer Wittholding"),
		("other", "Others")],
		string="Wittholding Type",
		default=lambda self: self._context.get("withholding_type")
	)
	l10n_latam_document_type_id = fields.Many2one(
		"l10n_latam.document.type",
		string="Document Type",
		default=lambda self: self._get_document_type()
	)
	date = fields.Date(
		string="Emission Date",
		readonly=True,
		states={"draft": [("readonly", False)]},
		default=fields.Date.today(),
		required=True
	)
	move_id = fields.Many2one(
		"account.move",
		string="Document",
		required=False,
		states=STATES_VALUE,
		copy=False,
	)
	move_wh_id = fields.Many2one(
		"account.move",
		string="Withholding Move",
	)
	tax_ids = fields.One2many(
		"account.invoice.tax",
		"withholding_id",
		string="Tax Details",
		readonly=True,
		states=STATES_VALUE,
		copy=False
	)
	partner_id = fields.Many2one(
		"res.partner",
		string="Partner",
		related='move_id.partner_id',
		readonly=True
	)
	state = fields.Selection(
		[
			("draft", "Draft"),
			("done", "Done"),
			("cancel", "Cancelled")
		],
		readonly=True,
		string="State",
		default="draft"
	)
	currency_id = fields.Many2one(
		"res.currency",
		string="Currency",
		required=True,
		readonly=True,
		states={"draft": [("readonly", False)]},
		default=lambda self: self.env.user.company_id.currency_id
	)
	amount_total = fields.Monetary(
		compute="_compute_total",
		string="Total",
		store=True,
		readonly=True
	)
