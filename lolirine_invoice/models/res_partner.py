<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <data noupdate="1">
        
        <!-- Cron auto-relance quotidien à 8h00 -->
        <record id="ir_cron_auto_reminder" model="ir.cron">
            <field name="name">Lolirine - Auto-relance factures impayées</field>
            <field name="model_id" ref="model_lolirine_invoice_reminder"/>
            <field name="state">code</field>
            <field name="code">model._cron_auto_reminder()</field>
            <field name="interval_number">1</field>
            <field name="interval_type">days</field>
            <field name="active">True</field>
            <field name="priority">10</field>
        </record>
        
        <!-- Cron vérification factures payées à 9h00 -->
        <record id="ir_cron_check_paid" model="ir.cron">
            <field name="name">Lolirine - Vérifier factures payées</field>
            <field name="model_id" ref="model_lolirine_invoice_reminder"/>
            <field name="state">code</field>
            <field name="code">model._cron_check_paid()</field>
            <field name="interval_number">1</field>
            <field name="interval_type">days</field>
            <field name="active">True</field>
            <field name="priority">15</field>
        </record>
        
        <!-- Recapitulatif mensuel des relances (envoye a Lolirine, jamais aux clients),
             le 1er du mois vers 8h (heure de Bruxelles) -->
        <record id="ir_cron_reminder_monthly_summary" model="ir.cron">
            <field name="name">Lolirine - Récapitulatif mensuel des relances</field>
            <field name="model_id" ref="model_lolirine_invoice_reminder"/>
            <field name="state">code</field>
            <field name="code">model._cron_monthly_summary()</field>
            <field name="interval_number">1</field>
            <field name="interval_type">months</field>
            <field name="nextcall" eval="(DateTime.now().replace(day=1) + relativedelta(months=1)).strftime('%Y-%m-%d 06:00:00')"/>
            <field name="active">True</field>
            <field name="priority">20</field>
        </record>
        
    </data>
</odoo>
