import base64
from datetime import datetime, date
import tempfile

from lxml import etree
import xml.etree.ElementTree as ET


from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

COMPROBANTE = {
    "Factura": "01",
    "Comprobante de Retención": "07"
}


class L10nEcImportDocument(models.Model):
    _name = "l10n.ec.import.document"
    _description = "Import SRI documents"
    _order = "date_from desc"

    name = fields.Char(
        string="Description",
        readonly=True
    )
    date_from = fields.Date(
        string="Date from",
        required=True,
        default=fields.Date.today()
    )
    date_to = fields.Date(
        string="Date to",
        required=True,
        default=fields.Date.today()
    )
    file_type = fields.Selection([
        ("xml", "xml"),
        ("txt", "txt")],
        string="File type",
        default="xml",
        required=True
    )
    file_ids = fields.One2many(
        "l10n.ec.import.file.line",
        "import_id",
        string="Files"
    )
    line_ids = fields.One2many(
        "l10n.ec.import.document.line",
        "import_id",
        string="Archivos XML"
    )
    invoice_counter = fields.Integer(
        compute="_compute_invoice_counter",
        string="N° invoices"
    )
    withholding_counter = fields.Integer(
        compute="_compute_invoice_counter",
        string="N° withholdings"
    )
    state = fields.Selection([
        ("draft", _("Draft")),
        ("imported", _("Imported")),
        ("close", _("Close")),
        ("cancel", _("Cancel"))],
        string=_("State"),
        default="draft",
    )

    @api.constrains("date_from", "date_to")
    def _constraint_date(self):
        for doc in self:
            if doc.date_from and doc.date_to and doc.date_from > doc.date_to:
                raise ValidationError("Date from cannot be higher than date to")

    @api.onchange("date_from", "date_to")
    def _onchange_name(self):
        for imp in self:
            imp.name = u"Import from {} to {}".format(imp.date_from, imp.date_to)

    def _compute_invoice_counter(self):
        for doc in self:
            doc.invoice_counter = len(
                doc.line_ids.filtered(
                    lambda x: x.l10n_latam_document_type_id.code == "01")
            )
            doc.withholding_counter = len(
                doc.line_ids.filtered(
                    lambda x: x.l10n_latam_document_type_id.code == "07")
            )

    def button_close(self):
        for doc in self:
            doc.state = "close"

    def button_cancel(self):
        for doc in self:
            doc.state = "cancel"

    def action_import_file(self):
        """ Imports documents"""
        for imp in self:
            txt = (".txt", ".TXT")
            xml = (".xml", ".XML")
            for doc in imp.file_ids:
                if doc.attachment_name[-4:] in txt:
                    self._import_txt(doc)
                elif doc.attachment_name[-4:] in xml:
                    self._import_xml(doc)

    def button_validate(self):
        for doc in self:
            doc.state = "cancel"

    def _import_txt(self, doc):
        """ Imports TXT invoices
        :param doc: doc line
        :return:
        """
        txt_lines = base64.b64decode(doc.attachment)
        header = str(txt_lines).split("\\n")
        txt_split2 = []
        list_prov = []
        invoices = []
        for item in header[2:]:
            txt_split2.append(item.split("\\t"))
        for i, line in enumerate(txt_split2):
            if (i+1) % 2 == 0:
                list_prov.append(line[0])
                invoices.append(list_prov)
            else:
                list_prov = line
        for inv in invoices:
            doc_type = self.env["l10n_latam.document.type"].search([
                ("code", "=", COMPROBANTE[str(inv[0].encode("iso-8859-1").decode("unicode_escape").encode("utf-8").decode("utf-8"))])
            ], limit=1)
            partner_id = self.env["res.partner"].search([
                ("vat", "=", inv[2])], limit=1)
            move_id = self.env["account.move"].search([(
                "l10n_latam_document_number", "=", inv[1])])
            self.env["l10n.ec.import.document.line"].create({
                "import_id": doc.import_id.id,
                "l10n_latam_document_type_id": doc_type.id,
                "l10n_latam_document_number": inv[1],
                "partner_id": partner_id.id,
                "vat": inv[2],
                "reconciled_sri": True if move_id else False,
                "partner_name": partner_id.name or str(inv[3]),
                "emission_date": datetime.strptime(inv[4], "%d/%m/%Y").date().strftime("%Y-%m-%d"),
                "access_key": inv[8],
                "authorization_code": inv[9],
                "amount": inv[-1],
            })
        doc.import_id.state = "imported"

    def _import_xml(self, doc):
        """ Import XML File
        :param doc:
        :return:
        """
        data = base64.decodebytes(doc.attachment)
        fobj = tempfile.NamedTemporaryFile(delete=False)
        fname = fobj.name
        fobj.write(data)
        fobj.close()
        file_xml = open(fname, "r")
        read_xml = file_xml.read()
        read_xml = read_xml.replace('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>', '')
        read_xml = read_xml.replace('<?xml version="1.0" encoding="UTF-8"?>', '')
        root = etree.fromstring(read_xml)
        comprobante = root.find(".//comprobante")
        comprobante_CDATA = comprobante.text
        comprobante = ET.fromstring(comprobante_CDATA)
        list_ids = []
        move_ids = []
        doc_name = "{}-{}-{}".format(
            comprobante.find(".//estab").text,
            comprobante.find(".//ptoEmi").text,
            comprobante.find(".//secuencial").text
        )
        doc_type = self.env["l10n_latam.document.type"].search([
            ("code", "=", COMPROBANTE[comprobante.tag.title()])], limit=1)
        partner = self.env["res.partner"].search([
            ("vat", "=", comprobante.find(".//ruc").text)])
        if not partner:
            partner = self.env["res.partner"].create({
                "vat": comprobante.find(".//ruc").text,
                "name": comprobante.find(".//razonSocial").text,
                "country_id": self.env.ref("base.ec").id,
                "street": comprobante.find(".//dirMatriz"),
                "l10n_latam_identification_type_id": self.env.ref("l10n_ec_base.ec_ruc").id
            })
        move_id = self.env["account.move"].search([(
            "l10n_latam_document_number", "=", doc_name)])
        import_line = self.env["l10n.ec.import.document.line"].create({
            "import_id": self.id,
            "l10n_latam_document_type_id": doc_type.id,
            "l10n_latam_document_number": doc_name,
            "vat": partner.vat,
            "partner_name": partner.name,
            "emission_date": datetime.strptime(
                comprobante.find(".//fechaEmision").text, "%d/%m/%Y").
                date().strftime("%Y-%m-%d"),
            "access_key": comprobante.find(".//claveAcceso").text,
            "authorization_code": root.find(".//numeroAutorizacion").text,
            "amount": comprobante.find(".//total").text,
            "partner_id": partner.id,
        })
        list_ids.append(import_line.id)
        account_move = self.env["account.move"].create({
            "partner_id": partner.id,
	        "fiscal_position_id": partner.property_account_position_id.id,
            "move_type": "in_invoice",
            "invoice_date": datetime.strptime(
                comprobante.find(".//fechaEmision").text, "%d/%m/%Y").
                date().strftime("%Y-%m-%d"),
	        "auth_number": root.find(".//numeroAutorizacion").text,
            "l10n_latam_document_number": doc_name,
        })
        account_move.write({"l10n_latam_document_type_id": doc_type.id})
        move_lines = []
        for line in comprobante.find(".//detalles").findall(".//detalle"):
            product = self.env["product.product"].search([
                ("default_code", "=", line.find("codigoPrincipal").text)
            ])
            if not product:
                product = self.env["product.product"].create({
                    "default_code": line.find("codigoPrincipal").text,
                    "name": line.find("descripcion").text,
                })
            if not product.property_account_expense_id:
                raise ValidationError("The expenses account is not configured")
            price_unit = float(line.find(".//precioUnitario").text)
            discount = float(line.find(".//descuento").text) * 100 / price_unit
            tax_id = self.env["account.tax"].search([
                ("type_tax_use", "=", "purchase"),
                ("amount", "=", line.find(".//tarifa").text)
            ])
            move_lines.append((0, 0, {
                "product_id": product.id,
                "name": line.find(".//descripcion").text,
                "quantity": float(line.find(".//cantidad").text),
                "price_unit": price_unit,
                "discount": discount,
                "tax_ids": [tax_id[0].id],
                "move_id": account_move.id,
                "account_id": product.property_account_expense_id.id
            }))
        account_move.write({"invoice_line_ids": move_lines})
        #move_ids.append(account_move.id)
        doc.import_id.state = "imported"
