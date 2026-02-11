with open(f'{module_path}/__manifest__.py', 'w') as f:
    f.write("""{
    'name': 'Lolirine - Peppol EAS Codes Extension',
    'version': '19.0.1.0.0',
    'category': 'Accounting',
    'summary': 'Adds missing Peppol EAS codes for international invoicing',
    'depends': ['account_edi_ubl_cii', 'account_peppol'],
    'data': [],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
""")
