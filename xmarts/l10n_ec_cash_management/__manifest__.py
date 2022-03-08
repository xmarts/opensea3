# -*- coding: utf-8 -*-
{
    'name': "Cash Managemetnt",
    'summary': """ Genera archivo de cash management para pagos.""",
    'description': """
        Archivo de pagos para bancos:\n
        - Pichincha.\n
        - Produbanco.\n,
        - Guayaquil.\n
        - Pacífico.\n
    """,
    'author': "[Xmarts]elymar.alfaro@xmarts.com",
    'website': "https://www.erp.xmarts.com",
    'category': 'Accounting',
    'version': '14.0.1.0.0',
    'depends': ['l10n_ec_base', 'account_payment_order'],
    'data': [
	    'data/account_payment_method_data.xml',
	    'views/account_payment_line_views.xml',
	    'views/res_bank_views.xml',
	    'views/res_partner_bank_views.xml',
	    'views/res_partner_views.xml',
	    'views/res_company_views.xml',
    ]
}
