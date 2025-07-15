
**2. `report/report_contrat_bail.xml`**
```xml
<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <record id="action_report_contrat_bail" model="ir.actions.report">
        <field name="name">Contrat de Bail</field>
        <field name="model">sale.subscription</field>
        <field name="report_type">qweb-pdf</field>
        <field name="report_name">contrat_bail_abonnement.report_contrat_bail_template</field>
        <field name="report_file">contrat_bail_abonnement.report_contrat_bail_template</field>
        <field name="print_report_name">'Contrat - %s' % (object.name)</field>
        <field name="binding_model_id" ref="sale_subscription.model_sale_subscription"/>
        <field name="binding_type">report</field>
    </record>
</odoo>
