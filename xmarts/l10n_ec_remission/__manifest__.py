# -*- coding: utf-8 -*-
{
    "name": "Remisiones para Ecuador",
    "version": "14.0.1.0.0",
    "category": "Accounting",
    "license": "AGPL-3",
    "depends": ["l10n_ec_einvoice", "stock", "sale"],
    "author": "[XMARTS]Pedro Romero, Elymar Alfaro",
    "website": "www.xmarts.com",
    "data": [
        "security/ir.model.access.csv",
	    "data/remission.guide.reason.csv",
	    "reports/report_eremission_guide.xml",
	    "wizards/generate_remission_guide_views.xml",
	    "views/account_move_views.xml",
	    "views/account_remission_guide_line_views.xml",
	    "views/account_remission_guide_views.xml",
	    "views/l10n_ec_emission_views.xml",
	    "views/stock_picking_views.xml",
	    "views/res_partner_view.xml",
    ]
}
