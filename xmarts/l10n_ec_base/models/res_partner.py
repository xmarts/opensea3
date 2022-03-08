
from odoo import _, api, fields, models
try:
    import stdnum
    from stdnum.util import clean

# from stdnum import ec
except ImportError:
    from . import ec
from odoo.exceptions import ValidationError

import logging

_logger = logging.getLogger(__name__)


def verify_final_consumer(vat):
    all_number_9 = False
    try:
        all_number_9 = vat and all(int(number) == 9 for number in vat) or False
    except ValueError as e:
        _logger.debug("Vat is not only numbers %s", e)
    return all_number_9 and len(vat) == 13


class ResPartner(models.Model):
    _inherit = "res.partner"

    l10n_ec_loc = fields.Boolean(
        string="Ecuadorian Localization",
        related="company_id.l10n_ec_loc",
        store=True
    )
    l10n_ec_person_type_id = fields.Many2one(
        "l10n.ec.person.type",
        string="Person Type",
        related="property_account_position_id.l10n_ec_person_type_id"
    )
    l10n_latam_identification_type_id = fields.Many2one(
        "l10n_latam.identification.type",
        string="Identification Type",
        index=True,
        auto_join=True,
        default=lambda self: self.env.ref(
            "l10n_ec_base.ec_final",
            raise_if_not_found=False
        ),
        help="The type of identification"
    )
    country_id = fields.Many2one(
        "res.country",
        default=lambda self: self.env.user.company_id.country_id
    )
    vat = fields.Char(
        string="Identification Number",
        default="9999999999999",
        help="Identification Number for selected type",
        required=True
    )
    authorization_ids = fields.One2many(
        "account.authorization",
        "partner_id",
        string="Authorizations"
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
    is_force_keep_accounting = fields.Selection([
        ("SI", "Yes"),
        ("NO", "No")],
        string="Keep Accounting",
        related="property_account_position_id.is_force_keep_accounting"
    )
    is_special_taxpayer = fields.Selection([
        ("SI", "Yes"),
        ("000", "No")],
        string="Special TaxPayer",
        default="000",
        related="property_account_position_id.is_special_taxpayer"
    )
    taxpayer_code = fields.Char(
        string="Taxpayer Code",
        default="000",
        help="Authorized Code"
    )
    issue_withholding = fields.Boolean(
        string="Issues Withholding",
        related="property_account_position_id.agent"
    )

    @api.onchange("property_account_position_id")
    def _onchange_person_type(self):
        for par in self:
            par.l10n_ec_person_type_id = par.property_account_position_id.l10n_ec_person_type_id.id
            par.issue_withholding = par.property_account_position_id.agent
    #
    # @staticmethod
    # def _get_type_id(external_id, vat):
    #    document_type = {
    #                        external_id == "l10n_ec_base.ec_ruc": "ruc",
    #                        external_id == "l10n_ec_base.ec_id": "ci",
    #                    }.get(True) or False
    #    return (document_type and getattr(ec, document_type).is_valid(vat)
    #            or False)

    def is_valid_ruc_ec(self, vat):
        ci = stdnum.util.get_cc_module("ec", "ci")
        ruc = stdnum.util.get_cc_module("ec", "ruc")
        if len(vat) == 10:
            return ci.is_valid(vat)
        elif len(vat) == 13:
            if vat[2] == "6" and ci.is_valid(vat[:10]):
                return True
            else:
                return ruc.is_valid(vat)
        return False

    def check_vat_ec(self, vat):
        vat = clean(vat, ' -.').upper().strip()
        return self.is_valid_ruc_ec(vat)
    #
    # @api.constrains("vat", "country_id", "l10n_latam_identification_type_id")
    # def check_vat(self):
    #     """  Overwrite check vat method
    #     :return: True(Boolean)
    #     """
    #     for partner in self:
    #         values = partner.l10n_latam_identification_type_id. \
    #             get_external_id().values()
    #         if list(values)[0] == "l10n_ec_base.ec_final":
    #             continue
    #         [external_id] = values
    #         if (
    #                 external_id not in (
    #                 "l10n_ec_base.ec_ruc", "l10n_ec_base.ec_id")
    #         ):
    #             continue
    #         res = partner._get_type_id(external_id, partner.vat)
    #         if not res:
    #             raise ValidationError("Error en el identificador.")
    #         return True

    @api.constrains("vat", "country_id", "l10n_latam_identification_type_id")
    def check_vat(self):
        it_ruc = self.env.ref("l10n_ec_base.ec_ruc", False)
        it_dni = self.env.ref("l10n_ec_base.ec_id", False)
        ecuadorian_partners = self.filtered(
            lambda x: x.country_id == self.env.ref("base.ec")
        )
        for partner in ecuadorian_partners:
            if partner.vat:
                if partner.l10n_latam_identification_type_id.id in (
                        it_ruc.id,
                        it_dni.id,
                ):
                    if partner.l10n_latam_identification_type_id.id == it_dni.id and len(partner.vat) != 10:
                        raise ValidationError(
                            _('If your identification type is %s, it must be 10 digits')
                            % it_dni.display_name)
                    if partner.l10n_latam_identification_type_id.id == it_ruc.id and len(partner.vat) != 13:
                        raise ValidationError(
                            _('If your identification type is %s, it must be 13 digits')
                            % it_ruc.display_name)
                    final_consumer = verify_final_consumer(partner.vat)
                    if final_consumer:
                        valid = True
                    else:
                        valid = self.is_valid_ruc_ec(partner.vat)
                    if not valid:
                        error_message = ""
                        if partner.l10n_latam_identification_type_id.id == it_dni.id:
                            error_message = _(
                                "VAT %s is not valid for an Ecuadorian DNI, "
                                "it must be like this form 0915068258") % partner.vat
                        if partner.l10n_latam_identification_type_id.id == it_ruc.id:
                            error_message = _(
                                "VAT %s is not valid for an Ecuadorian company, "
                                "it must be like this form 0993143790001") % partner.vat
                        raise ValidationError(error_message)
        return super(ResPartner, self - ecuadorian_partners).check_vat()

    @api.constrains("vat", "l10n_latam_identification_type_id")
    def _constraint_identification(self):
        """ Validates there is not another
         partner with the same identification
        :return:
         """

        for par in self:
            rec = self.search([
                ("id", "!=", par.id), ("vat", "=", par.vat),
                (
                    "l10n_latam_identification_type_id",
                    "=", par.l10n_latam_identification_type_id.id
                ),
                (
                    "l10n_latam_identification_type_id",
                    "!=", self.env.ref("l10n_ec_base.ec_final").id
                ),
            ])
            if rec and rec.parent_id:
                continue
            elif rec and not rec.parent_id:
                raise ValidationError(
                    "There is already a contact with this identification"
                 )
    #
    # @staticmethod
    # def _get_identification_external(identification):
    #     if not identification:
    #         return
    #     [external_id] = identification.get_external_id().values()
    #     return external_id

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
            partners = self.search(
                [("vat", operator, name)] + args, limit=limit
            )
            if not partners:
                partners = self.search(
                    [("name", operator, name)] + args, limit=limit
                )
        else:
            partners = self.search(args, limit=limit)
        return partners.name_get()