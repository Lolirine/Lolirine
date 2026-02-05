{
    'name': 'Lolirine Pool - Variant Images & Colors',
    'version': '19.0.2.0.0',
    'category': 'Sales/Product',
    'summary': 'Gérer les images et couleurs des variantes depuis la fiche produit',
    'description': """
        Permet de modifier les images et couleurs des valeurs d'attributs
        directement depuis la configuration des variantes sur la fiche produit.
        
        Fonctionnalités:
        - Onglet "Visuels des variantes" sur la fiche produit
        - Wizard d'édition des images/couleurs par valeur d'attribut
        - Preview des visuels dans la configuration des variantes
        - Swatches améliorés sur le site web (couleur et image)
        - Support display_type 'image' et 'color'
    """,
    'author': 'Lolirine SPRL',
    'website': 'https://www.lolirine.be',
    'depends': [
        'product',
        'sale',
        'website_sale',
    ],
    'data': [
        'security/ir.model.access.csv',
        'wizard/attribute_visual_wizard_views.xml',
        'wizard/variant_image_wizard_views.xml',
        'views/product_template_views.xml',
        'views/product_attribute_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'lolirine_pool_variant_images/static/src/scss/variant_images.scss',
        ],
        'web.assets_frontend': [
            'lolirine_pool_variant_images/static/src/scss/variant_swatches.scss',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
