# -*- coding: utf-8 -*-
import base64
import zipfile
import io
from datetime import datetime
from lxml import etree
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class BiztaxXbrlGenerator(models.AbstractModel):
    """
    XBRL Generator for Belgian Tax Declarations
    Generates XBRL instance documents conformant to be-tax taxonomy
    """
    _name = 'biztax.xbrl.generator'
    _description = 'Générateur XBRL Biztax'

    # Namespaces for be-tax taxonomy
    NAMESPACES = {
        'xbrli': 'http://www.xbrl.org/2003/instance',
        'link': 'http://www.xbrl.org/2003/linkbase',
        'xlink': 'http://www.w3.org/1999/xlink',
        'iso4217': 'http://www.xbrl.org/2003/iso4217',
        'xbrldi': 'http://xbrl.org/2006/xbrldi',
        'xbrldt': 'http://xbrl.org/2005/xbrldt',
    }
    
    # Taxonomy-specific namespaces (updated per version)
    TAXONOMY_NAMESPACES = {
        '2025-04-30': {
            'rcorp': 'http://www.minfin.fgov.be/be/tax/inc/rcorp/2025-04-30',
            'nrcorp': 'http://www.minfin.fgov.be/be/tax/inc/nrcorp/2025-04-30',
            'rle': 'http://www.minfin.fgov.be/be/tax/inc/rle/2025-04-30',
            'pfs-gcd': 'http://www.minfin.fgov.be/be/pfs/gcd/2025-04-01',
            'pfs-vl': 'http://www.minfin.fgov.be/be/pfs/vl/2025-04-01',
        },
        '2024-04-30': {
            'rcorp': 'http://www.minfin.fgov.be/be/tax/inc/rcorp/2024-04-30',
            'nrcorp': 'http://www.minfin.fgov.be/be/tax/inc/nrcorp/2024-04-30',
            'rle': 'http://www.minfin.fgov.be/be/tax/inc/rle/2024-04-30',
            'pfs-gcd': 'http://www.minfin.fgov.be/be/pfs/gcd/2024-04-01',
            'pfs-vl': 'http://www.minfin.fgov.be/be/pfs/vl/2024-04-01',
        },
    }

    def _get_namespaces(self, declaration):
        """Get all namespaces for the declaration"""
        version = declaration.taxonomy_version
        dec_type = declaration.declaration_type
        
        ns = self.NAMESPACES.copy()
        tax_ns = self.TAXONOMY_NAMESPACES.get(version, {})
        
        # Add the main declaration namespace
        ns['be-tax'] = tax_ns.get(dec_type, '')
        ns['pfs-gcd'] = tax_ns.get('pfs-gcd', '')
        ns['pfs-vl'] = tax_ns.get('pfs-vl', '')
        
        return ns

    def _get_schema_ref(self, declaration):
        """Get the schema reference for the taxonomy"""
        version = declaration.taxonomy_version
        dec_type = declaration.declaration_type
        
        schema_map = {
            'rcorp': f'be-tax-{version}/DTS/be-tax-inc-rcorp-{version}.xsd',
            'nrcorp': f'be-tax-{version}/DTS/be-tax-inc-nrcorp-{version}.xsd',
            'rle': f'be-tax-{version}/DTS/be-tax-inc-rle-{version}.xsd',
        }
        
        return schema_map.get(dec_type, schema_map['rcorp'])

    def generate_xbrl(self, declaration):
        """
        Generate XBRL instance document for the declaration
        
        :param declaration: biztax.declaration record
        :return: XML string
        """
        ns = self._get_namespaces(declaration)
        nsmap = {k: v for k, v in ns.items() if v}
        
        # Create root element
        root = etree.Element(
            '{%s}xbrl' % ns['xbrli'],
            nsmap=nsmap
        )
        
        # Add schema reference
        schema_ref = etree.SubElement(
            root,
            '{%s}schemaRef' % ns['link'],
            {
                '{%s}type' % ns['xlink']: 'simple',
                '{%s}href' % ns['xlink']: self._get_schema_ref(declaration),
            }
        )
        
        # Add contexts
        self._add_contexts(root, declaration, ns)
        
        # Add units
        self._add_units(root, ns)
        
        # Add facts (the actual tax data)
        self._add_facts(root, declaration, ns)
        
        # Generate XML string
        xml_string = etree.tostring(
            root,
            pretty_print=True,
            xml_declaration=True,
            encoding='UTF-8'
        )
        
        return xml_string.decode('utf-8')

    def _add_contexts(self, root, declaration, ns):
        """Add XBRL contexts to the document"""
        # Entity context (instant)
        context_instant = etree.SubElement(
            root,
            '{%s}context' % ns['xbrli'],
            id='ctx_instant'
        )
        
        entity = etree.SubElement(context_instant, '{%s}entity' % ns['xbrli'])
        identifier = etree.SubElement(
            entity,
            '{%s}identifier' % ns['xbrli'],
            scheme='http://www.fgov.be'
        )
        identifier.text = declaration.enterprise_number
        
        period_instant = etree.SubElement(context_instant, '{%s}period' % ns['xbrli'])
        instant = etree.SubElement(period_instant, '{%s}instant' % ns['xbrli'])
        instant.text = declaration.fiscal_year_end.isoformat()
        
        # Duration context (for the fiscal year)
        context_duration = etree.SubElement(
            root,
            '{%s}context' % ns['xbrli'],
            id='ctx_duration'
        )
        
        entity2 = etree.SubElement(context_duration, '{%s}entity' % ns['xbrli'])
        identifier2 = etree.SubElement(
            entity2,
            '{%s}identifier' % ns['xbrli'],
            scheme='http://www.fgov.be'
        )
        identifier2.text = declaration.enterprise_number
        
        period_duration = etree.SubElement(context_duration, '{%s}period' % ns['xbrli'])
        start_date = etree.SubElement(period_duration, '{%s}startDate' % ns['xbrli'])
        start_date.text = declaration.fiscal_year_start.isoformat()
        end_date = etree.SubElement(period_duration, '{%s}endDate' % ns['xbrli'])
        end_date.text = declaration.fiscal_year_end.isoformat()
        
        # Previous year context (for comparatives)
        context_prev = etree.SubElement(
            root,
            '{%s}context' % ns['xbrli'],
            id='ctx_prev_instant'
        )
        
        entity3 = etree.SubElement(context_prev, '{%s}entity' % ns['xbrli'])
        identifier3 = etree.SubElement(
            entity3,
            '{%s}identifier' % ns['xbrli'],
            scheme='http://www.fgov.be'
        )
        identifier3.text = declaration.enterprise_number
        
        period_prev = etree.SubElement(context_prev, '{%s}period' % ns['xbrli'])
        instant_prev = etree.SubElement(period_prev, '{%s}instant' % ns['xbrli'])
        instant_prev.text = declaration.fiscal_year_start.isoformat()

    def _add_units(self, root, ns):
        """Add XBRL units to the document"""
        # EUR unit
        unit_eur = etree.SubElement(
            root,
            '{%s}unit' % ns['xbrli'],
            id='EUR'
        )
        measure_eur = etree.SubElement(unit_eur, '{%s}measure' % ns['xbrli'])
        measure_eur.text = 'iso4217:EUR'
        
        # Pure unit (for percentages, counts)
        unit_pure = etree.SubElement(
            root,
            '{%s}unit' % ns['xbrli'],
            id='pure'
        )
        measure_pure = etree.SubElement(unit_pure, '{%s}measure' % ns['xbrli'])
        measure_pure.text = 'xbrli:pure'

    def _add_facts(self, root, declaration, ns):
        """Add XBRL facts (tax data) to the document"""
        be_tax_ns = ns.get('be-tax', '')
        
        # Helper function to add monetary fact
        def add_monetary_fact(element_name, value, context='ctx_duration', decimals='0'):
            if value is not None and value != 0:
                fact = etree.SubElement(
                    root,
                    '{%s}%s' % (be_tax_ns, element_name),
                    contextRef=context,
                    unitRef='EUR',
                    decimals=decimals
                )
                fact.text = str(int(round(value)))
        
        # Helper function to add string fact
        def add_string_fact(element_name, value, context='ctx_instant'):
            if value:
                fact = etree.SubElement(
                    root,
                    '{%s}%s' % (be_tax_ns, element_name),
                    contextRef=context
                )
                fact.text = str(value)
        
        # === IDENTIFICATION ===
        # Enterprise number
        add_string_fact('EnterpriseNumber', declaration.enterprise_number)
        
        # Assessment year
        add_string_fact('AssessmentYear', str(declaration.assessment_year))
        
        # Fiscal year dates
        add_string_fact('AccountingYearStartDate', declaration.fiscal_year_start.isoformat())
        add_string_fact('AccountingYearEndDate', declaration.fiscal_year_end.isoformat())
        
        # === CADRE F - PREMIÈRE OPÉRATION ===
        # Résultat comptable
        add_monetary_fact('AccountingProfit', declaration.accounting_profit)
        add_monetary_fact('AccountingLoss', declaration.accounting_loss)
        
        # Réserves
        add_monetary_fact('ReservesStartYear', declaration.reserves_start, 'ctx_prev_instant')
        add_monetary_fact('ReservesEndYear', declaration.reserves_end, 'ctx_instant')
        add_monetary_fact('ReservesMovement', declaration.reserves_movement)
        
        # Dividendes et tantièmes
        add_monetary_fact('DividendsDistributed', declaration.dividends_distributed)
        add_monetary_fact('Tantiemes', declaration.tantiemes)
        
        # Résultat première opération
        add_monetary_fact('FirstOperationResult', declaration.first_operation_result)
        
        # === CADRE I - DEUXIÈME OPÉRATION ===
        # DNA total
        add_monetary_fact('TotalDisallowedExpenses', declaration.total_dna)
        
        # Déductions totales
        add_monetary_fact('TotalDeductions', declaration.total_deductions)
        
        # === AJUSTEMENTS DÉTAILLÉS ===
        for adj in declaration.adjustment_ids:
            if adj.tax_code_id and adj.tax_code_id.xbrl_element:
                add_monetary_fact(adj.tax_code_id.xbrl_element, adj.amount)
        
        # === CADRE K - BASE IMPOSABLE ===
        add_monetary_fact('TaxableBase', declaration.taxable_base)
        
        # === CADRE L - IMPÔT ===
        # PME indicator
        if declaration.is_sme:
            add_string_fact('SMEIndicator', 'true')
        
        # Tax rates
        fact_rate = etree.SubElement(
            root,
            '{%s}CorporateTaxRate' % be_tax_ns,
            contextRef='ctx_duration',
            unitRef='pure',
            decimals='4'
        )
        fact_rate.text = str(declaration.tax_rate / 100)
        
        if declaration.is_sme:
            fact_rate_sme = etree.SubElement(
                root,
                '{%s}ReducedCorporateTaxRate' % be_tax_ns,
                contextRef='ctx_duration',
                unitRef='pure',
                decimals='4'
            )
            fact_rate_sme.text = str(declaration.tax_rate_reduced / 100)
        
        # Tax amount
        add_monetary_fact('CorporateTaxAmount', declaration.tax_amount)
        
        # === CADRE M - PRÉCOMPTES ET VA ===
        add_monetary_fact('PrepaymentsTotalAmount', declaration.prepayments)
        add_monetary_fact('PrepaymentsBenefit', declaration.prepayment_benefit)
        
        # === CADRE N - SOLDE ===
        add_monetary_fact('BalanceDue', declaration.balance_due)

    def generate_biztax_package(self, declaration):
        """
        Generate the complete .biztax package (ZIP file containing XBRL + PDFs)
        
        A .biztax file is a ZIP archive containing:
        - The XBRL instance document
        - PDF attachments (annexes)
        - A manifest file (optional but recommended)
        
        :param declaration: biztax.declaration record
        :return: bytes (ZIP file content)
        """
        # Generate XBRL if not already done
        if not declaration.xbrl_file:
            xbrl_content = self.generate_xbrl(declaration)
            xbrl_bytes = xbrl_content.encode('utf-8')
        else:
            xbrl_bytes = base64.b64decode(declaration.xbrl_file)
        
        # Create ZIP in memory
        zip_buffer = io.BytesIO()
        
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            # Add XBRL file
            xbrl_filename = f"declaration_{declaration.enterprise_number}_{declaration.assessment_year}.xbrl"
            zip_file.writestr(xbrl_filename, xbrl_bytes)
            
            # Add PDF attachments
            for attachment in declaration.attachment_ids:
                if attachment.file_data:
                    pdf_data = base64.b64decode(attachment.file_data)
                    pdf_filename = attachment.file_name or f"{attachment.annex_type}_{attachment.id}.pdf"
                    zip_file.writestr(f"attachments/{pdf_filename}", pdf_data)
            
            # Add manifest
            manifest = self._generate_manifest(declaration, xbrl_filename)
            zip_file.writestr('manifest.xml', manifest.encode('utf-8'))
        
        return zip_buffer.getvalue()

    def _generate_manifest(self, declaration, xbrl_filename):
        """Generate manifest XML for the biztax package"""
        manifest = f"""<?xml version="1.0" encoding="UTF-8"?>
<manifest>
    <declaration>
        <enterpriseNumber>{declaration.enterprise_number}</enterpriseNumber>
        <assessmentYear>{declaration.assessment_year}</assessmentYear>
        <declarationType>{declaration.declaration_type}</declarationType>
        <taxonomyVersion>{declaration.taxonomy_version}</taxonomyVersion>
        <xbrlFile>{xbrl_filename}</xbrlFile>
        <generatedAt>{datetime.now().isoformat()}</generatedAt>
        <generatedBy>Lolirine Biztax Module for Odoo</generatedBy>
    </declaration>
    <attachments>
"""
        for att in declaration.attachment_ids:
            manifest += f"""        <attachment>
            <type>{att.annex_type}</type>
            <name>{att.name}</name>
            <filename>attachments/{att.file_name or f'{att.annex_type}_{att.id}.pdf'}</filename>
        </attachment>
"""
        manifest += """    </attachments>
</manifest>
"""
        return manifest

    def validate_xbrl(self, declaration):
        """
        Validate XBRL instance against be-tax taxonomy
        
        Note: Full validation requires the actual taxonomy files.
        This method performs basic structural validation.
        For complete validation, use a dedicated XBRL processor.
        
        :param declaration: biztax.declaration record
        :return: list of validation errors
        """
        errors = []
        
        if not declaration.xbrl_file:
            errors.append(_("Aucun fichier XBRL généré."))
            return errors
        
        try:
            xbrl_content = base64.b64decode(declaration.xbrl_file)
            root = etree.fromstring(xbrl_content)
            
            # Basic structure validation
            ns = {'xbrli': 'http://www.xbrl.org/2003/instance'}
            
            # Check for required elements
            contexts = root.findall('.//xbrli:context', ns)
            if not contexts:
                errors.append(_("Aucun contexte XBRL trouvé."))
            
            units = root.findall('.//xbrli:unit', ns)
            if not units:
                errors.append(_("Aucune unité XBRL trouvée."))
            
            # Check for schema reference
            link_ns = {'link': 'http://www.xbrl.org/2003/linkbase'}
            schema_ref = root.find('.//link:schemaRef', link_ns)
            if schema_ref is None:
                errors.append(_("Référence au schéma taxonomie manquante."))
            
        except etree.XMLSyntaxError as e:
            errors.append(_("Erreur de syntaxe XML: %s") % str(e))
        except Exception as e:
            errors.append(_("Erreur de validation: %s") % str(e))
        
        return errors
