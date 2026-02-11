{
    'name': 'Lolirine - Peppol EAS Codes Extension',
    'version': '19.0.1.0.0',
    'category': 'Accounting',
    'summary': 'Adds missing Peppol EAS codes for international invoicing',
    'description': """
        Extends the Peppol EAS (Electronic Address Scheme) selection field
        on res.partner with all standard codes from the official Peppol
        EAS code list (https://docs.peppol.eu/poacc/billing/3.0/codelist/eas/).

        This fixes import errors when receiving Peppol invoices from
        international partners using EAS codes not included in the base
        Belgian localization (e.g. 0106 for Netherlands KvK).
    """,
    'author': 'Lolirine SPRL',
    'website': 'https://lolirine.be',
    'depends': ['account_edi_ubl_cii', 'account_peppol'],
    'data': [],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
