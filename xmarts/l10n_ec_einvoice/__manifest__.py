# -*- coding: utf-8 -*-
{
    "name": "Electronic Documents for Ecuador",
    "version": "14.0.1.0.0",
    "author": "",
    "category": "Localization",
    "license": "AGPL-3",
    "complexity": "normal",
    "data": [
        "security/ir.model.access.csv",
        "data/ir_config_parameter.xml",
        "data/sequence.xml",
	    "views/l10n_ec_sri_key_views.xml",
	    "views/l10n_ec_sri_authorization_views.xml",
        "views/account_move_views.xml",
	    "views/account_withholding_views.xml",
        "views/res_company_views.xml",
	    "report/edocument_layouts.xml",
        "report/report_einvoice.xml",
	    "report/report_edebitnote.xml",
	    "report/report_ecreditnote.xml",
	    "report/report_eliq_purchase.xml",
	    "report/report_ewithholding.xml",
	    "edi/einvoice_edi.xml",
    ],
    "depends": ["l10n_ec_base"]
}
