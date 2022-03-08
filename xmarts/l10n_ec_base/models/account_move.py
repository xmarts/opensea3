from collections import defaultdict

from odoo import _, api, fields, models
from odoo.tools.misc import formatLang, format_date, get_lang
from odoo.exceptions import ValidationError

DOCUMENTOS_EMISION = ("out_invoice",  "out_refund")



SEQUENCE = {
	"18": "invoice_sequence_id",
	"05": "debitnote_sequence_id",
	"04": "creditnote_sequence_id",
	"03": "liqpurchase_sequence_id"
}


class AccountMove(models.Model):
	_inherit = "account.move"

	withholding_id = fields.Many2one(
		"account.withholding",
		string="Withholding",
		copy=False
	)
	has_withholding = fields.Boolean(
		compute="_check_withholding",
		string="Has withholding",
		store=True,
	)
	withholding_counter = fields.Integer(
		string="Withholding Count",
		compute="_compute_invoice_counters"
	)
	create_withholding_type = fields.Selection([
		("auto", "Automatic"),
		("manual", "Manual")],
		string="Numerar Retención",
		required=True,
		readonly=True,
		states={"draft": [("readonly", False)]},
		default="auto"
	)
	vat = fields.Char(
		related="partner_id.vat",
		string="Identification number"
	)
	is_electronic_document = fields.Boolean(
		string="Is electronic document",
		default=True
	)
	state = fields.Selection(
		selection_add=[
			("refund", "Refund")
		], ondelete={"refund": "cascade"}
	)
	auth_inv_id = fields.Many2one(
		"account.authorization",
		string="Stablishment",
		help="Authorization for document",
		copy=False
	)
	l10n_ec_emission_point_id = fields.Many2one(
		"l10n.ec.stablishment",
		string="Emission Point",
		domain="[('company_id', '=', company_id)]",
		default=lambda self: self.env.user.l10n_ec_emission_point_id or False
	)
	l10n_ec_sri_payment_id = fields.Many2one(
		"l10n.ec.sri.payment",
		string="Payment Method",
		copy=False,
		default=lambda self: self.env.ref(
			"l10n_ec_base.P20",
			raise_if_not_found=False
		)
	)
	support_id = fields.Many2one(
		"account.ats.support",
		string="Voucher Support",
		default=lambda self: self.env.ref(
			"l10n_ec_base.001",
			raise_if_not_found=False
		)
	)
	auth_number = fields.Char(
		string="Purchase Invoice Authorization",
		size=49
	)
	l10n_latam_document_code = fields.Char(
		string="Latam Document Code",
		related="l10n_latam_document_type_id.code",
		store=True
	)
	l10n_ec_loc = fields.Boolean(
		string="Ecuadorian Localization",
		related="company_id.l10n_ec_loc",
		store=True
	)
	l10n_latam_document_number = fields.Char(
		compute=False,
		inverse=False,
		store=True,
		copy=False,
		size=17
	)
	invoice_date = fields.Date(default=fields.Date.today())
	invoice_refund_counter = fields.Integer(
		compute="_compute_invoice_counters",
		string="# of Invoice Refunds",
	)
	# refund_id = fields.Many2one(
	# 	"account.move",
	# 	string="Invoice to refund"
	# )
	refund_move_ids = fields.Many2many(
		"account.move",
		"account_move_refund_rel",
		"move_id",
		"refund_id",
		string="Refund Details",
		domain="[('state', '=', 'refund')]"
	)
	refund_line_ids = fields.One2many(
		"account.move.refund.line",
		"move_id",
		string="Refund Details"
	)

	def _get_l10n_latam_documents_domain(self):
		""" Filter document types according to ecuadorian move_type """

		domain = super(AccountMove, self)._get_l10n_latam_documents_domain()
		if self.country_code == "EC":
			domain.append(
				{
					self.move_type == "out_invoice": (
						"l10n_ec_type", "=", "out_invoice"),
					self.move_type == "out_refund": (
						"l10n_ec_type", "=", "out_refund"),
					self.move_type == "in_invoice": (
						"l10n_ec_type", "=", "in_invoice"),
					self.move_type == "in_refund": (
						"l10n_ec_type", "=", "in_refund")
				}.get(True) or ())
		return domain

	@api.depends("l10n_latam_document_number", "move_type")
	def name_get(self):
		return [
			(move.id, move.l10n_latam_document_number or move.name)
			for move in self
			if move.move_type != "entry"
		]

	@api.model
	def name_search(self, name, args=None, operator="ilike", limit=80):
		""" Modifies name search method
        :param name:
        :param args:
        :param operator:
        :param limit:
        :return: """

		if not args:
			args = []
		if name:
			moves = self.search(
				[("l10n_latam_document_number", operator, name)] + args,
				limit=limit
			)
			if not moves:
				moves = self.search(
					[("name", operator, name)] + args, limit=limit
				)
		else:
			moves = self.search(args, limit=limit)
		return moves.name_get()

	@api.depends("l10n_latam_document_type_id", "journal_id")
	def _compute_l10n_latam_manual_document_number(self):
		""" Indicates if this document type uses a
        sequence or if the numbering is made manually """
		recs_with_journal_id = self.filtered(
			lambda x: x.journal_id and x.journal_id.l10n_latam_use_documents)
		for rec in recs_with_journal_id:
			rec.l10n_latam_manual_document_number = (
				self._is_manual_document_number(rec.journal_id, rec))
		remaining = self - recs_with_journal_id
		remaining.l10n_latam_manual_document_number = False

	def _is_manual_document_number(self, journal, move):
		return False

	@api.depends("restrict_mode_hash_table", "state")
	def _compute_show_reset_to_draft_button(self):
		for move in self:
			move.show_reset_to_draft_button = (
					not move.restrict_mode_hash_table
					and move.state in ("posted", "cancel", "refund"))

	def _get_last_sequence_domain(self, relaxed=False):
		where_string, param = super(
			AccountMove, self)._get_last_sequence_domain(relaxed)
		if (
				self.company_id.country_id.code == "EC"
				and self.l10n_latam_use_documents
		):
			where_string = where_string.replace(
				'journal_id = %(journal_id)s AND', '')
			where_string += ' AND l10n_latam_document_type_id = %(l10n_latam_document_type_id)s AND ' \
			                'company_id = %(company_id)s AND move_type IN (\'out_invoice\', \'out_refund\', \'entry\', \'in_invoice\')'
			param['company_id'] = self.company_id.id or False
			param[
				'l10n_latam_document_type_id'] = self.l10n_latam_document_type_id.id or 0
		return where_string, param

	def _l10n_ec_get_formatted_sequence(self, number=0):
		return '%s %06d' % (
			self.l10n_latam_document_type_id.doc_code_prefix, number)

	@api.depends("journal_id", "partner_id", "company_id", "move_type")
	def _compute_l10n_latam_available_document_types(self):
		self.ensure_one()
		self.l10n_latam_available_document_type_ids = False
		if self.move_type == "entry":
			return
		for rec in self.filtered(
				lambda x: x.journal_id
				          and x.l10n_latam_use_documents
				          and x.partner_id
		):
			rec.l10n_latam_available_document_type_ids = self.env[
				"l10n_latam.document.type"].search(
				rec._get_l10n_latam_documents_domain()
			)

	# @api.constrains("l10n_latam_document_number", "move_type", "partner_id")
	# def _constraints_unique_number(self):
	# 	""" Constraint for same document number and document type """
	# 	for inv in self:
	# 		if inv.move_type == "in_invoice":
	# 			rec = self.search(
	# 				[
	# 					("id", "!=", inv.id),
	# 					("l10n_latam_document_number", "=",
	# 					 inv.l10n_latam_document_number),
	# 					("l10n_latam_document_code", "=",
	# 					 inv.l10n_latam_document_code),
	# 					("partner_id", "=", inv.partner_id.id)])
	# 			if rec:
	# 				raise ValidationError(
	# 					"There is already a document with this"
	# 					" number for this partner {}".format(rec.id)
	# 				)

	@api.constrains('state', 'l10n_latam_document_type_id')
	def _check_l10n_latam_documents(self):
		pass

	@api.onchange("l10n_latam_document_number", "move_type")
	def _onchange_document_number(self):
		""" Validate Ref number if in_invoice"""
		for inv in self:
			if not inv.move_type or not inv.l10n_latam_document_number:
				return
			if (
					inv.move_type in ("in_invoice", "in_refund")
			and inv.l10n_latam_document_code in ('01', '05')
					and len(inv.l10n_latam_document_number) != 17
			):
				raise ValidationError("Ref Length must be of 17 digits")

	@api.onchange("partner_id")
	def _onchange_sri_payment_id(self):
		"""
		Sets payment method
		:return:
		"""
		for move in self:
			if move.partner_id and move.partner_id.l10n_ec_sri_payment_id:
				move.l10n_ec_sri_payment_id = move.partner_id.l10n_ec_sri_payment_id

	def _action_number(self):
		""" Gets number for document """
		for inv in self:
			if inv.posted_before or inv.l10n_latam_document_number:
				continue
			if (
					inv.move_type in ("out_invoice", "out_debit", "out_refund")
					or inv.move_type == "in_invoice"
					#and inv.is_electronic_document
					and inv.l10n_latam_document_code == "03"
			):
				inv.l10n_latam_document_number = "{0}-{1}".format(
					inv.l10n_ec_emission_point_id.emission_point_prefix,
					getattr(inv.l10n_ec_emission_point_id, SEQUENCE[inv.l10n_latam_document_code]).next_by_id().format()
				)

	@api.constrains("l10n_latam_document_number")
	def _validate_document_number(self):
		for inv in self:
			if inv.move_type == "in_invoice" and inv.l10n_latam_document_code == "01":
				inv.l10n_latam_document_type_id._format_document_number(
					inv.l10n_latam_document_number)

	def button_refund(self):
		self.state = "refund"

	def _compute_invoice_counters(self):
		for inv in self:
			inv.invoice_refund_counter = inv.search_count([
				("move_type", "in", ("out_refund", "in_refund")),
				("reversed_entry_id", "=", inv.id)])
			inv.withholding_counter = self.env["account.withholding"].search_count(
				[("move_id", "=", inv.id)])

	# def _validate_emission_point(self):
	# 	if not self.env.user.l10n_ec_emission_point_id and not \
	# 			self.l10n_ec_emission_point_id:
	# 		raise ValidationError("There is no emission point")

	def _get_invoice_reference_odoo_invoice(self):
		""" This computes the reference based on the Odoo format.
			We simply return the number of the invoice, defined on the journal
			sequence.
		"""
		self.ensure_one()
		return "{} {}".format(
			self.l10n_latam_document_type_id.doc_code_prefix,
			self.l10n_latam_document_number
		)

	def _post(self, soft=True):
		""" Adds numbering method before posting
        :param soft:
        :return: None
        """
		#self._validate_emission_point()
		try:
			self._action_number()
			super(AccountMove, self)._post()
			self._action_withholding_create()
		except Exception as e:
			raise ValidationError(e)

	@api.constrains("refund_line_ids", "invoice_line_ids")
	def _onchange_total_refund_line(self):
		""" Validates that amount total
         is the same than invoice
        :return:
        """
		for move in self:
			if move.refund_line_ids:
				tax_amount = round(sum(move.refund_line_ids.mapped("iva_amount")), 2)
				total = sum([i.total for i in move.refund_line_ids])
				if total != move.amount_total or tax_amount != move.amount_tax:
					raise ValidationError(
						"The total of Refunds can't be different"
						" than invoice total"
					)

	def _compute_withholding_count(self):
		for move in self:
			move.withholding_counter = self.env["account.withholding"]. \
				search_count([("move_id", "=", move.id)])

	def _group_withholding_lines(self):
		""" Helper to get the taxes grouped according their
		 account.tax.group. This method is only used when printing the invoice.
		:return:
		"""
		for move in self:
			lang_env = move.with_context(lang=move.partner_id.lang).env
			res = move.invoice_line_ids._get_withholding_by_group(
				-1 if move.is_inbound(True) else 1
			)
			move.amount_by_group = [
				                       i for i in move.amount_by_group
				                       if i[1]
			                       ] + [(
				group.name, amounts["amount"],
				amounts["base"],
				formatLang(
					lang_env, amounts["amount"], currency_obj=move.currency_id
				),
				formatLang(
					lang_env, amounts["base"], currency_obj=move.currency_id
				),
				len(res),
				group.id
			) for group, amounts in res.items()]

	def button_add_withholding(self):
		""" Adds a Withholding to document """
		if self.withholding_id and self.withholding_id.state != "cancel":
			raise ValidationError("Please first cancel the last withholding")
		doc_type = ""
		if self.move_type == "out_invoice":
			domain = [("l10n_ec_type", "=", "out_withhold")]
		elif self.move_type == "in_invoice":
			domain = [("l10n_ec_type", "=", "in_withhold")]
		doc_type = self.env["l10n_latam.document.type"].search(domain)
		return {
			"type": "ir.actions.act_window",
			"res_model": "account.withholding",
			"context": {
				"default_withholding_type": self.move_type,
				"default_move_id": self.id,
				"default_l10n_emission_point_id": self.env.user.l10n_ec_emission_point_id or False,
				"default_partner_id": self.partner_id.id,
				"default_l10n_latam_document_type_id": doc_type.id
			},
			"target": "current",
			"view_mode": "form",
		}

	@api.depends("invoice_line_ids.tax_ids")
	def _check_withholding(self):
		""" If withholding taxes in lines,
		creates a new withholding automatically
		:return:
		"""
		TAXES = ["wh_income_tax", "wh_vat"]
		for inv in self:
			for tax in inv.invoice_line_ids.tax_ids:
				if tax.tax_group_id.l10n_ec_type in TAXES:
					inv.has_withholding = True

	@api.depends(
		"line_ids.price_subtotal",
		"line_ids.tax_base_amount",
		"line_ids.tax_line_id",
		"partner_id",
		"currency_id"
	)
	def _compute_invoice_taxes_by_group(self):
		super(AccountMove, self)._compute_invoice_taxes_by_group()
		self._group_withholding_lines()

	def _action_withholding_create(self):
		"""
		Este método genera el documento de retención en varios escenarios
		considera casos de:
		* Generar retencion automaticamente
		* Generar retencion de reemplazo
		* Cancelar retencion generada
		"""
		for inv in self:
			if (
					not inv.has_withholding
					or not inv.move_type == "in_invoice"
					and not inv.l10n_latam_document_code == "01"
					or inv.date > fields.Date.context_today(inv)
			):
				continue
			if inv.withholding_id and inv.withholding_id.state != "cancel":
				raise ValidationError(
					"Cancel the last withholding to generate a new one"
				)
			ret_taxes = inv.invoice_line_ids.tax_ids.filtered(
				lambda l: l.tax_group_id.l10n_ec_type in [
					"wh_vat", "wh_income_tax"
				]
			)
			doc_type = self.env["l10n_latam.document.type"].search(
				[("l10n_ec_type", "=", "in_withhold")])
			emi_point = self.env.user.l10n_ec_emission_point_id
			withdrawing_data = {
				"partner_id": inv.partner_id.id,
				"move_id": inv.id,
				"l10n_latam_document_type_id": doc_type.id,
				"l10n_ec_emission_point_id": emi_point.id,
				"withholding_type": inv.move_type,
				"tax_ids": inv.invoice_line_ids._get_withholding_line(),
				"date": inv.date,
				"manual": False
			}
			withdrawing = self.env["account.withholding"].create(withdrawing_data)
			ret_taxes.write({"withholding_id": withdrawing.id})
			withdrawing.button_validate()
			inv.write({"withholding_id": withdrawing.id})
		return True

	def _get_ret_iva(self):
		"""
		Return (valRetBien10, valRetServ20,
		valorRetBienes,
		valorRetServicios, valorRetServ100)
		"""

		self.ensure_one()
		_get_amount = lambda line, tax: abs(
			tax._compute_amount(line.price_subtotal, line.price_unit,
			                    line.quantity, line.product_id)
		) * 0.12
		k = (
			"wh_vat_assets10", "wh_vat_services20"
			                   "wh_vat_services50", "wh_vat_services100"
		)
		amount_by_wh = defaultdict(float)
		for line in self.invoice_line_ids:
			for tax in line.tax_ids:
				l10n_ec_type = tax.tax_group_id.l10n_ec_type
				if l10n_ec_type not in ("wh_vat_assets", "wh_vat_services"):
					continue
				type_amount = f"{l10n_ec_type}{abs(tax.amount)}"
				amount_by_wh[
					type_amount if type_amount
					               in k else l10n_ec_type
				] += _get_amount(line, tax)
		return amount_by_wh

	def _amounts_by_tax_group(self):
		group = self.env["account.tax.group"].browse
		return {
			group(tax_group[-1]).l10n_ec_type: {
				"amount": tax_group[1],
				"base": tax_group[2],
			}
			for tax_group in self.amount_by_group
			if tax_group
		}

	# def _tax_by_l10n_ec_group(self, amount_by_group):
	# 	data = dict()
	# 	group = self.env["account.tax.group"].browse
	# #	for l in grou
	#
	# 	return group(amount_by_group[-1]).l10n_ec_type

	def get_ats_refund(self):
		""" Method for ATS """
		self.ensure_one()
		refund_id = self.search([
			("move_type", "in", ("out_refund", "in_refund")),
			("reversed_entry_id", "=", self.id)
		], limitw=1)
		if not refund_id:
			return {}
		auth = refund_id.auth_inv_id
		return {
			"es_nc": True,
			"docModificado": "01",
			"estabModificado": refund_id.l10n_latam_document_number[0:3],
			"ptoEmiModificado": refund_id.l10n_latam_document_number[3:6],
			"secModificado": refund_id.supplier_l10n_latam_document_number,
			"autModificado": refund_id.numero_autorizacion
			if auth.is_electronic else auth.name
		}

	def button_open_withholdings(self):
		""" Opens Withholdings List"""
		return {
			"type": "ir.actions.act_window",
			"res_model": "account.withholding",
			"context": {
				"default_move_id": self.id,
				"withholding_type": self.move_type
			},
			"domain": [("move_id", "=", self.id)],
			"target": "current",
			"views": [
				(self.env.ref("l10n_ec_base.view_account_withholding_tree").id, "tree"),
				(self.env.ref("l10n_ec_base.view_account_withholding_form_ec").id, "form"),
			],
			"view_mode": "tree,form",
		}
