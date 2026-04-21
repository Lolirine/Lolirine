<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <data>
        <!-- Vue Kanban pour afficher les images extraites -->
        <record id="view_pool_catalog_pdf_image_kanban" model="ir.ui.view">
            <field name="name">pool.catalog.pdf.image.kanban</field>
            <field name="model">pool.catalog.pdf.image</field>
            <field name="arch" type="xml">
                <kanban default_group_by="page_number">
                    <field name="id"/>
                    <field name="name"/>
                    <field name="page_number"/>
                    <field name="quality_score"/>
                    <field name="role"/>
                    <field name="image_final"/>
                    <field name="matched_product_id"/>
                    <field name="notes"/>
                    
                    <templates>
                        <t t-name="kanban-box">
                            <div class="oe_kanban_card oe_kanban_global_click" style="width: 300px;">
                                <div class="oe_kanban_content">
                                    <!-- Header avec informations -->
                                    <div class="oe_kanban_header">
                                        <div class="oe_kanban_header_left">
                                            <div class="o_kanban_record_title">
                                                <field name="name"/>
                                            </div>
                                        </div>
                                        <div class="oe_kanban_header_right">
                                            <span class="badge badge-info">Q:<field name="quality_score"/></span>
                                        </div>
                                    </div>
                                    
                                    <!-- Image principale -->
                                    <div class="text-center" style="padding: 10px;">
                                        <img t-att-src="kanban_image('pool.catalog.pdf.image', 'image_final', record.id.raw_value)" 
                                             alt="Image du produit"
                                             style="max-width: 250px; max-height: 200px; border: 1px solid #ddd; border-radius: 4px;"/>
                                    </div>
                                    
                                    <!-- Informations produit -->
                                    <div class="oe_kanban_details" style="padding: 5px;">
                                        <t t-if="record.matched_product_id.value">
                                            <strong>Produit:</strong> <field name="matched_product_id"/>
                                        </t>
                                        <t t-else="">
                                            <span class="text-muted">Aucun produit associé</span>
                                        </t>
                                        
                                        <div style="margin-top: 5px;">
                                            <span class="badge" t-att-class="{'badge-success': record.role.raw_value == 'primary', 
                                                                             'badge-secondary': record.role.raw_value == 'secondary',
                                                                             'badge-warning': record.role.raw_value == 'unassigned',
                                                                             'badge-danger': record.role.raw_value == 'rejected'}">
                                                <t t-esc="record.role.value"/>
                                            </span>
                                        </div>
                                        
                                        <!-- Notes du filtrage intelligent -->
                                        <t t-if="record.notes.value">
                                            <div style="font-size: 10px; color: #666; margin-top: 5px;">
                                                <field name="notes"/>
                                            </div>
                                        </t>
                                    </div>
                                    
                                    <!-- Actions -->
                                    <div class="oe_kanban_footer">
                                        <div class="oe_kanban_footer_left">
                                            <span style="font-size: 10px; color: #888;">
                                                Page <field name="page_number"/>
                                            </span>
                                        </div>
                                        <div class="oe_kanban_footer_right">
                                            <div class="dropdown">
                                                <a class="dropdown-toggle btn" data-toggle="dropdown" href="#" role="button" aria-haspopup="true" aria-expanded="false">
                                                    <span class="fa fa-ellipsis-v" title="Actions"/>
                                                </a>
                                                <ul class="dropdown-menu" role="menu">
                                                    <li><a name="action_set_primary" type="object">🌟 Marquer comme Principale</a></li>
                                                    <li><a name="action_set_secondary" type="object">📷 Marquer comme Secondaire</a></li>
                                                    <li role="separator" class="divider"></li>
                                                    <li><a name="action_delete_image" type="object">🗑️ Supprimer cette Image</a></li>
                                                </ul>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </t>
                    </templates>
                </kanban>
            </field>
        </record>

        <!-- Action mise à jour pour inclure la vue kanban -->
        <record id="action_pool_catalog_pdf_image" model="ir.actions.act_window">
            <field name="name">Images Extraites</field>
            <field name="res_model">pool.catalog.pdf.image</field>
            <field name="view_mode">kanban,list,form</field>
            <field name="view_ids" eval="[(5, 0, 0),
                                          (0, 0, {'view_mode': 'kanban', 'view_id': ref('view_pool_catalog_pdf_image_kanban')}),
                                          (0, 0, {'view_mode': 'list'}),
                                          (0, 0, {'view_mode': 'form'})]"/>
            <field name="context">{}</field>
            <field name="help" type="html">
                <p class="o_view_nocontent_smiling_face">
                    Aucune image extraite
                </p>
                <p>
                    Utilisez l'extraction d'images depuis un import PDF pour voir les images ici.
                </p>
            </field>
        </record>

        <!-- Menu pour accéder aux images -->
        <menuitem 
            id="menu_pool_catalog_pdf_image"
            name="Images Extraites"
            action="action_pool_catalog_pdf_image"
            sequence="99"/>

    </data>
</odoo>
