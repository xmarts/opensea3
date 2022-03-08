from datetime import datetime

from odoo import api, fields, models


def change_special_caracters(text):
	characters = {
		u'Á': u'A',
		u'á': u'a',
		u'É': u'E',
		u'é': u'e',
		u'Í': u'I',
		u'í': u'i',
		u'Ó': u'O',
		u'ó': u'o',
		u'Ú': u'U',
		u'ú': u'u',
		u'Ü': u'U',
		u'ü': u'u',
		u'Ñ': u'N',
		u'ñ': 'n',
	}
	for ori, new in characters.iteritems():
		text = text.replace(ori, new)
	return text


TIPO_IDENT = {"c": "C", "r": "R", "p": "P"}


class AccountPaymentOrder(models.Model):
	_inherit = "account.payment.order"

	@api.depends("payment_type")
	def _compute_bank_orientation_code(self):
		for r in self:
			if r.payment_type == "outbound":
				r.bank_orientation_code = "PA"
			else:
				r.bank_orientation_code = "CO"

	bank_orientation_code = fields.Selection([
		("PA", "Pago"),
		("CO", "Cobro")],
		string="Bankc Orientation Code",
		compute=_compute_bank_orientation_code,
		store=True,
	)

	def generate_payment_file(self):
		self.ensure_one()
		today = fields.Date.context_today(self)
		#DATE = datetime.strptime(today, '%Y-%m-%d').strftime('%y%m%d')
		if self.payment_method_id.code == "pa_pichincha":
			filename = "pagos_cash_management_pichincha.txt"
			file_str = ""
			for seq, i in enumerate(self.payment_line_ids, 1):
				file_str += "\t".join(
					[
						self.bank_orientation_code,
						str(seq),
						i.currency_id.name,
						"{:.2f}".format(i.amount_currency)
							.replace(".", "")
							.replace(",", ""),
						i.bank_payment_method,
						i.partner_bank_id.bank_acc_type,
						i.partner_bank_id.sanitized_acc_number,
						i.communication[:39],
						i.partner_id.l10n_latam_identification_type_id.name[0] or "N",
						i.partner_id.vat,
						i.partner_id.name,
						i.partner_bank_id.bank_id.pichincha_bank_code or "",
						]
				)
				file_str += "\n"
			return (file_str.encode("utf-8"), filename)
		elif self.payment_method_id.code == "pm_alianza":
			filename = "PAGO_ALIANZA.txt"
			file_str = ""
			for line in self.payment_line_ids:
				file_str += "\t".join(
					[
						line.partner_bank_id.sanitized_acc_number,
						line.partner_id.name,
						"asistentecontable@sary-collection.com",  # TODO: verificar si el empleado tiene correo electronico personal
						str(line.amount_currency),
					]
				)
				file_str += "\n"
				return (file_str.encode("utf-8"), filename)
		elif self.payment_method_id.code == "pa_guayaquil":
			filename = "PAGOS_MULTICASH_%Y%m%d_SEC.txt"
			file_str = ""
			for seq, i in enumerate(self.payment_line_ids, 1):
				file_str += "\t".join(
					[
						self.bank_orientation_code,
						self.company_partner_bank_id.sanitized_acc_number.rjust(10, '0'),
						str(seq),
						i.partner_bank_id.sanitized_acc_number[:10] or ''.rjust(10, '0'),
						i.currency_id.name,
						"{:.2f}".format(i.amount_currency)
							.replace(".", "")
							.replace(",", "").rjust(13, '0'),
						i.bank_payment_method,
						i.partner_bank_id.guayaquil_bank_code if i.bank_payment_method == "CTA" else "0017",
						i.partner_bank_id.bank_acc_type if i.bank_payment_method == "CTA" else " ",
						i.partner_bank_id.sanitized_acc_number[:10].rjust(10, '0') if i.bank_payment_method == "CTA" else " ",
						i.partner_id.l10n_latam_identification_type_id.name[0],
						i.partner_id.vat,
						i.partner_id.name[:40],
						i.communication,
						"{} | {}".format(i.communication, i.partner_id.email),
					]
				)
				file_str += "\n"
				return (file_str.encode("utf-8"), filename)
		elif self.payment_method_id.code == "pa_internacional":
			filename = "PAGOSCASH_INTERNACIONAL.txt"
			file_str = ""
			for seq, i in enumerate(self.payment_line_ids, 1):
				file_str += "\t".join(
					[
						self.bank_orientation_code,
						str(seq),
						i.currency_id.name,
						"{:.2f}".format(i.amount_currency)
							.replace(".", "")
							.replace(",", "").rjust(13, '0'),
						i.bank_payment_method,
						i.partner_bank_id.bank_acc_type,
						i.partner_bank_id.sanitized_acc_number[:20],
						i.communication[:40],
						i.partner_id.l10n_latam_identification_type_id.name[0],
						i.partner_id.vat,
						i.partner_id.name[:41],
						i.partner_bank_id.guayaquil_bank_code,
					]
				)
				file_str += "\n"
				return (file_str.encode("utf-8"), filename)
		elif self.payment_method_id.code == "pa_produbanco":
			filename = "pagos_cash_management_produbanco.txt"
			file_str = "D{}{}{}{}N1\n".format(
				self.company_id.name.upper().ljust(40, ' ')[:40],
				self.bank_account_id.acc_number.replace('-', '').rjust(11, '0'),
				str(int(round(self.amount, 2) * 100)).rjust(14, '0'),
			#	DATE
			)
			for line in self.payment_line_ids:
				file_str += "\t".join(
					[
						"C",
						line.partner_id.name.upper().ljust(40, ' ')[:40],
						line.partner_bank_id.sanitized_acc_number.rjust(11, '0'),
						str(int(round(line.amount, 2) * 100)).rjust(14, '0'),
				#		DATE,
						"N1"
					]
				)
				file_str += "\n"
		else:
			return super(AccountPaymentOrder, self).generate_payment_file()



