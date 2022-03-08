# -*- coding: utf-8 -*-

from odoo import api, fields, models


class AccountAtsSupport(models.Model):
    _name = "account.ats.support"
    _description = "Voucher Support"

    @api.depends("code", "name")
    def name_get(self):
        res = []
        for record in self:
            name = "%s - %s" % (record.code, record.name)
            res.append((record.id, name))
        return res

    code = fields.Char(
        string="Code",
        size=2,
        required=True
    )
    name = fields.Char(
        string="Support type",
        size=128,
        required=True
    )

