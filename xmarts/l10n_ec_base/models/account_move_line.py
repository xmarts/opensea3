from collections import defaultdict
from odoo import api, fields, models


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    def _compute_withholding_line_taxes(self):
        """Computes Withholding Taxes """
        return self.tax_ids._origin.with_context(
            force_sign=self.move_id._get_tax_force_sign()
        ).with_context(withholding=True).compute_all(
            (-1 if self.move_id.is_inbound() else 1) * (
                self.price_unit * (1 - (self.discount / 100.0))
            ),
            currency=self.currency_id,
            quantity=self.quantity,
            product=self.product_id,
            partner=self.partner_id,
            is_refund=self.move_id.move_type in ("out_refund", "in_refund"),
            handle_price_include=True,
        )

    def _get_withholding_by_group(self, tax_multp):
        account_tax = self.env["account.tax"]
        res = defaultdict(lambda: defaultdict(float))
        for line in self:
            for tax in line._compute_withholding_line_taxes()["taxes"]:
                tax_group_id = account_tax.browse(tax["id"]).tax_group_id
                res[tax_group_id]["amount"] += tax_multp * tax["amount"]
                res[tax_group_id]["base"] += (
                        line.currency_id and line.company_currency_id
                        and line.currency_id != line.company_currency_id
                        and line.company_currency_id._convert(
                        (
                            (
                                tax_group_id.l10n_ec_type == "vat12"
                                and 0.12 or 1
                             ) * tax["base"]
                        ),
                            line.currency_id, line.company_id,
                            line.date or fields.Date.context_today(self)
                        ) or (
		                        tax_group_id.l10n_ec_type == "vat12"
		                        and 0.12 or 1
                        ) * tax["base"])
        return res

    def _get_withholding_line(self, tax_multp=1):
        account_tax = self.env["account.tax"]
        res = defaultdict(lambda: defaultdict(float))
        repartition_line = self.env["account.tax.repartition.line"]
        for line in self:
            for tax in line._compute_withholding_line_taxes()["taxes"]:
                tax_group_id = account_tax.browse(tax["id"]).tax_group_id
                tax_repartition_line = repartition_line.browse(
                    tax["tax_repartition_line_id"]
                )
                tax_id = tax_repartition_line.invoice_tax_id \
                         or tax_repartition_line.refund_tax_id
                res[tax_id]["amount"] += tax_multp * tax["amount"]
                res[tax_id]["account_id"] = tax_repartition_line.account_id.id
                res[tax_id]["base"] += (
	                line.currency_id and line.company_currency_id
	                and line.currency_id != line.company_currency_id
	                and line.company_currency_id._convert(
		                (
			                (
				                tax_group_id.l10n_ec_type == "wh_vat"
				                and 0.12 or 1
			                ) * tax["base"]
		                ), line.currency_id, line.company_id,
	                    line.date or fields.Date.context_today(self)
                    ) or (
		                tax_group_id.l10n_ec_type == "wh_vat"
		                and 0.12 or 1
	                ) * tax["base"]
                )
        return [
            (0, 0, {
                "tax_id": tax_id.id,
                "group_id": tax_id.tax_group_id.id,
                "amount": vals["amount"],
                "base": vals["base"],
                "account_id": vals["account_id"],
            }) for tax_id, vals in res.items()
        ]
