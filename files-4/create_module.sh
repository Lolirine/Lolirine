#!/bin/bash

# Script de création automatique du module Box Contact Redirect pour Odoo 18.1
# Usage: ./create_module.sh

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║  Création du module Box Contact Redirect pour Odoo 18.1     ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

# Créer la structure des dossiers
echo "📁 Création de la structure des dossiers..."
mkdir -p box_contact_redirect/controllers
mkdir -p box_contact_redirect/models
mkdir -p box_contact_redirect/views

# Fichier 1: __init__.py principal
echo "📝 Création de __init__.py..."
cat > box_contact_redirect/__init__.py << 'EOF'
# -*- coding: utf-8 -*-

from . import models
from . import controllers
EOF

# Fichier 2: __manifest__.py
echo "📝 Création de __manifest__.py..."
cat > box_contact_redirect/__manifest__.py << 'EOF'
# -*- coding: utf-8 -*-
{
    'name': 'Box Contact Redirect',
    'version': '18.1.1.0',
    'category': 'Website/Website',
    'summary': 'Remplace le bouton ajouter au panier par un bouton contact pour les box disponibles',
    'description': """
        Module personnalisé pour la gestion de garde-meubles
        ======================================================
        
        * Ajoute un champ pour indiquer si un box est disponible
        * Remplace le bouton "Ajouter au panier" par un bouton "Nous contacter" 
          pour les box marqués comme disponibles
        * Redirige vers le formulaire de contact avec les informations du box
        
        Compatible avec Odoo 18.1
    """,
    'author': 'Custom Development',
    'website': '',
    'depends': ['website_sale'],
    'data': [
        'views/product_template_views.xml',
        'views/website_sale_templates.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
EOF

# Fichier 3: controllers/__init__.py
echo "📝 Création de controllers/__init__.py..."
cat > box_contact_redirect/controllers/__init__.py << 'EOF'
# -*- coding: utf-8 -*-

from . import main
EOF

# Fichier 4: controllers/main.py
echo "📝 Création de controllers/main.py..."
cat > box_contact_redirect/controllers/main.py << 'EOF'
# -*- coding: utf-8 -*-

from odoo import http
from odoo.http import request


class BoxContactController(http.Controller):
    
    @http.route(['/contactus'], type='http', auth="public", website=True, sitemap=False)
    def contact_form_box(self, box_name=None, box_id=None, **kwargs):
        """
        Gère l'affichage du formulaire de contact avec les informations du box
        """
        values = {}
        
        if box_name:
            values['box_name'] = box_name
        if box_id:
            values['box_id'] = box_id
            # Récupérer plus d'informations sur le produit si nécessaire
            product = request.env['product.template'].sudo().browse(int(box_id))
            if product.exists():
                values['product'] = product
                # Pré-remplir le message avec les infos du box
                default_message = f"Bonjour,\n\nJe suis intéressé(e) par le box : {box_name}\n\nMerci de me recontacter.\n"
                values['default_description'] = default_message
        
        # Utiliser le template de contact standard d'Odoo
        return request.render("website.contactus", values)
EOF

# Fichier 5: models/__init__.py
echo "📝 Création de models/__init__.py..."
cat > box_contact_redirect/models/__init__.py << 'EOF'
# -*- coding: utf-8 -*-

from . import product_template
EOF

# Fichier 6: models/product_template.py
echo "📝 Création de models/product_template.py..."
cat > box_contact_redirect/models/product_template.py << 'EOF'
# -*- coding: utf-8 -*-

from odoo import models, fields, api


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    box_require_contact = fields.Boolean(
        string='Rediriger vers contact',
        default=False,
        help="Si coché, le bouton 'Ajouter au panier' sera remplacé par un bouton 'Nous contacter' sur le site web"
    )
    
    box_is_available = fields.Boolean(
        string='Box disponible',
        default=True,
        help="Indique si le box est actuellement disponible à la location"
    )
EOF

# Fichier 7: views/product_template_views.xml
echo "📝 Création de views/product_template_views.xml..."
cat > box_contact_redirect/views/product_template_views.xml << 'EOF'
<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <data>
        <!-- Extend Product Template Form View -->
        <record id="product_template_form_view_inherit_box_contact" model="ir.ui.view">
            <field name="name">product.template.form.inherit.box.contact</field>
            <field name="model">product.template</field>
            <field name="inherit_id" ref="product.product_template_form_view"/>
            <field name="arch" type="xml">
                <xpath expr="//page[@name='sales']" position="inside">
                    <group string="Gestion Box">
                        <field name="box_is_available"/>
                        <field name="box_require_contact" invisible="not box_is_available"/>
                    </group>
                </xpath>
            </field>
        </record>
    </data>
</odoo>
EOF

# Fichier 8: views/website_sale_templates.xml
echo "📝 Création de views/website_sale_templates.xml..."
cat > box_contact_redirect/views/website_sale_templates.xml << 'EOF'
<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <data>
        <!-- Personnalisation du bouton d'achat pour les box -->
        <template id="product_add_to_cart_inherit_box" inherit_id="website_sale.product" name="Box Contact Button">
            <xpath expr="//div[@id='product_detail']//form[@action='/shop/cart/update']" position="replace">
                <t t-if="product.box_require_contact and product.box_is_available">
                    <!-- Bouton de contact pour les box disponibles nécessitant un contact -->
                    <div class="js_product js_main_product mt-3">
                        <a t-attf-href="/contactus?box_name={{ product.name }}&amp;box_id={{ product.id }}" 
                           class="btn btn-primary btn-lg w-100 a-submit">
                            <i class="fa fa-envelope"/> Nous contacter pour ce box
                        </a>
                        <p class="text-muted mt-2">
                            <i class="fa fa-info-circle"/> Ce box est disponible. Contactez-nous pour finaliser votre réservation.
                        </p>
                    </div>
                </t>
                <t t-else="">
                    <!-- Comportement normal pour les autres produits -->
                    <form t-if="product._is_add_to_cart_possible()" 
                          action="/shop/cart/update" 
                          method="POST" 
                          class="js_product js_main_product mt-3">
                        <input type="hidden" name="csrf_token" t-att-value="request.csrf_token()"/>
                        <input type="hidden" class="product_id" name="product_id" t-att-value="product.id"/>
                        <input type="hidden" class="product_template_id" name="product_template_id" t-att-value="product.product_tmpl_id.id"/>
                        
                        <div class="js_product_change">
                            <t t-if="product.product_variant_ids">
                                <div t-if="len(product.product_variant_ids) &gt; 1" class="mb-3">
                                    <t t-call="website_sale.variants"/>
                                </div>
                            </t>
                            
                            <div class="product_quantity mb-3">
                                <label class="control-label">Quantité</label>
                                <div class="css_quantity input-group oe_website_spinner">
                                    <span class="input-group-prepend">
                                        <a href="#" class="btn btn-secondary js_add_cart_json" aria-label="Retirer un" title="Retirer un">
                                            <i class="fa fa-minus"></i>
                                        </a>
                                    </span>
                                    <input type="text" class="form-control quantity" name="add_qty" value="1"/>
                                    <span class="input-group-append">
                                        <a href="#" class="btn btn-secondary js_add_cart_json float_left" aria-label="Ajouter un" title="Ajouter un">
                                            <i class="fa fa-plus"></i>
                                        </a>
                                    </span>
                                </div>
                            </div>
                        </div>
                        
                        <div id="add_to_cart_wrap" class="mt-3">
                            <a id="add_to_cart" class="btn btn-primary btn-lg w-100 a-submit" href="#">
                                <i class="fa fa-shopping-cart"/> Ajouter au panier
                            </a>
                        </div>
                    </form>
                </t>
            </xpath>
        </template>

        <!-- Template pour la vue liste/grille des produits -->
        <template id="products_item_inherit_box" inherit_id="website_sale.products_item" name="Box Contact Button Grid">
            <xpath expr="//form[hasclass('js_add_cart_json')]" position="replace">
                <t t-if="product.box_require_contact and product.box_is_available">
                    <a t-attf-href="/contactus?box_name={{ product.name }}&amp;box_id={{ product.id }}" 
                       class="btn btn-primary w-100 a-submit">
                        <i class="fa fa-envelope"/> Nous contacter
                    </a>
                </t>
                <t t-else="">
                    <form action="/shop/cart/update" method="post" class="js_add_cart_json d-none d-md-inline-block">
                        <input type="hidden" name="csrf_token" t-att-value="request.csrf_token()"/>
                        <input type="hidden" name="product_id" t-att-value="product.product_variant_id.id"/>
                        <button type="submit" class="btn btn-primary w-100 a-submit">
                            <i class="fa fa-shopping-cart"/> Ajouter au panier
                        </button>
                    </form>
                </t>
            </xpath>
        </template>
    </data>
</odoo>
EOF

echo ""
echo "✅ Module créé avec succès !"
echo ""
echo "📦 Structure créée :"
tree box_contact_redirect/ 2>/dev/null || find box_contact_redirect/ -type f
echo ""
echo "🚀 Prochaines étapes :"
echo "   1. git add box_contact_redirect/"
echo "   2. git commit -m 'Add box_contact_redirect module v18.1.1.0'"
echo "   3. git push origin master"
echo "   4. Dans Odoo : Apps > Mettre à jour > Installer 'Box Contact Redirect'"
echo ""
echo "✨ Terminé !"
