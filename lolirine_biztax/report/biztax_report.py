# -*- coding: utf-8 -*-
"""
Biztax Report Models - Generate PDF annexes from Odoo accounting data
"""
from odoo import api, models, fields, _
from odoo.exceptions import UserError
from datetime import date


class BiztaxBalanceSheetReport(models.AbstractModel):
    """
    Report model for Balance Sheet (Bilan)
    Generates data from account.move.line for the declaration's fiscal year
    """
    _name = 'report.lolirine_biztax.report_balance_sheet'
    _description = 'Bilan - Rapport Biztax'

    @api.model
    def _get_report_values(self, docids, data=None):
        docs = self.env['biztax.declaration'].browse(docids)
        
        report_data = []
        for declaration in docs:
            company = declaration.company_id
            date_from = declaration.fiscal_year_start
            date_to = declaration.fiscal_year_end
            
            # Get balance sheet data organized by PCMN classes
            balance_data = self._compute_balance_sheet(company, date_to)
            
            report_data.append({
                'declaration': declaration,
                'company': company,
                'date_from': date_from,
                'date_to': date_to,
                'assets': balance_data['assets'],
                'liabilities': balance_data['liabilities'],
                'total_assets': balance_data['total_assets'],
                'total_liabilities': balance_data['total_liabilities'],
            })
        
        return {
            'doc_ids': docids,
            'doc_model': 'biztax.declaration',
            'docs': docs,
            'data': data,
            'report_data': report_data,
        }
    
    def _compute_balance_sheet(self, company, date_to):
        """
        Compute balance sheet from account balances
        Belgian PCMN structure:
        - Class 2: Actifs immobilisés
        - Class 3: Stocks
        - Class 4: Créances/Dettes
        - Class 5: Placements/Valeurs disponibles
        - Class 1: Capitaux propres/Provisions
        """
        AccountMoveLine = self.env['account.move.line']
        
        # Helper function to get account balance
        def get_balance(domain):
            lines = AccountMoveLine.search(domain + [
                ('company_id', '=', company.id),
                ('date', '<=', date_to),
                ('parent_state', '=', 'posted'),
            ])
            return sum(lines.mapped('balance'))
        
        assets = {
            'fixed_assets': {
                'name': 'ACTIFS IMMOBILISÉS',
                'items': [
                    {'code': '20', 'name': 'Frais d\'établissement', 
                     'amount': get_balance([('account_id.code', '=like', '20%')])},
                    {'code': '21', 'name': 'Immobilisations incorporelles', 
                     'amount': get_balance([('account_id.code', '=like', '21%')])},
                    {'code': '22-27', 'name': 'Immobilisations corporelles', 
                     'amount': get_balance([('account_id.code', '=like', '22%')]) +
                              get_balance([('account_id.code', '=like', '23%')]) +
                              get_balance([('account_id.code', '=like', '24%')]) +
                              get_balance([('account_id.code', '=like', '25%')]) +
                              get_balance([('account_id.code', '=like', '26%')]) +
                              get_balance([('account_id.code', '=like', '27%')])},
                    {'code': '28', 'name': 'Immobilisations financières', 
                     'amount': get_balance([('account_id.code', '=like', '28%')])},
                ],
            },
            'current_assets': {
                'name': 'ACTIFS CIRCULANTS',
                'items': [
                    {'code': '29', 'name': 'Créances à plus d\'un an', 
                     'amount': get_balance([('account_id.code', '=like', '29%')])},
                    {'code': '3', 'name': 'Stocks et commandes en cours', 
                     'amount': get_balance([('account_id.code', '=like', '3%')])},
                    {'code': '40-41', 'name': 'Créances à un an au plus', 
                     'amount': get_balance([('account_id.code', '=like', '40%')]) +
                              get_balance([('account_id.code', '=like', '41%')])},
                    {'code': '50-53', 'name': 'Placements de trésorerie', 
                     'amount': get_balance([('account_id.code', '=like', '50%')]) +
                              get_balance([('account_id.code', '=like', '51%')]) +
                              get_balance([('account_id.code', '=like', '52%')]) +
                              get_balance([('account_id.code', '=like', '53%')])},
                    {'code': '54-58', 'name': 'Valeurs disponibles', 
                     'amount': get_balance([('account_id.code', '=like', '54%')]) +
                              get_balance([('account_id.code', '=like', '55%')]) +
                              get_balance([('account_id.code', '=like', '56%')]) +
                              get_balance([('account_id.code', '=like', '57%')]) +
                              get_balance([('account_id.code', '=like', '58%')])},
                    {'code': '490-491', 'name': 'Comptes de régularisation', 
                     'amount': get_balance([('account_id.code', '=like', '490%')]) +
                              get_balance([('account_id.code', '=like', '491%')])},
                ],
            },
        }
        
        liabilities = {
            'equity': {
                'name': 'CAPITAUX PROPRES',
                'items': [
                    {'code': '10', 'name': 'Capital', 
                     'amount': -get_balance([('account_id.code', '=like', '10%')])},
                    {'code': '11', 'name': 'Primes d\'émission', 
                     'amount': -get_balance([('account_id.code', '=like', '11%')])},
                    {'code': '12', 'name': 'Plus-values de réévaluation', 
                     'amount': -get_balance([('account_id.code', '=like', '12%')])},
                    {'code': '13', 'name': 'Réserves', 
                     'amount': -get_balance([('account_id.code', '=like', '13%')])},
                    {'code': '14', 'name': 'Bénéfice/Perte reporté(e)', 
                     'amount': -get_balance([('account_id.code', '=like', '14%')])},
                    {'code': '15', 'name': 'Subsides en capital', 
                     'amount': -get_balance([('account_id.code', '=like', '15%')])},
                ],
            },
            'provisions': {
                'name': 'PROVISIONS ET IMPÔTS DIFFÉRÉS',
                'items': [
                    {'code': '16', 'name': 'Provisions pour risques et charges', 
                     'amount': -get_balance([('account_id.code', '=like', '16%')])},
                    {'code': '168', 'name': 'Impôts différés', 
                     'amount': -get_balance([('account_id.code', '=like', '168%')])},
                ],
            },
            'debts': {
                'name': 'DETTES',
                'items': [
                    {'code': '17', 'name': 'Dettes à plus d\'un an', 
                     'amount': -get_balance([('account_id.code', '=like', '17%')])},
                    {'code': '42-48', 'name': 'Dettes à un an au plus', 
                     'amount': -get_balance([('account_id.code', '=like', '42%')]) -
                              get_balance([('account_id.code', '=like', '43%')]) -
                              get_balance([('account_id.code', '=like', '44%')]) -
                              get_balance([('account_id.code', '=like', '45%')]) -
                              get_balance([('account_id.code', '=like', '46%')]) -
                              get_balance([('account_id.code', '=like', '47%')]) -
                              get_balance([('account_id.code', '=like', '48%')])},
                    {'code': '492-493', 'name': 'Comptes de régularisation', 
                     'amount': -get_balance([('account_id.code', '=like', '492%')]) -
                              get_balance([('account_id.code', '=like', '493%')])},
                ],
            },
        }
        
        # Calculate totals
        total_assets = sum(
            sum(item['amount'] for item in section['items'])
            for section in assets.values()
        )
        total_liabilities = sum(
            sum(item['amount'] for item in section['items'])
            for section in liabilities.values()
        )
        
        return {
            'assets': assets,
            'liabilities': liabilities,
            'total_assets': total_assets,
            'total_liabilities': total_liabilities,
        }


class BiztaxProfitLossReport(models.AbstractModel):
    """
    Report model for Profit & Loss Statement (Compte de résultats)
    """
    _name = 'report.lolirine_biztax.report_profit_loss'
    _description = 'Compte de résultats - Rapport Biztax'

    @api.model
    def _get_report_values(self, docids, data=None):
        docs = self.env['biztax.declaration'].browse(docids)
        
        report_data = []
        for declaration in docs:
            company = declaration.company_id
            date_from = declaration.fiscal_year_start
            date_to = declaration.fiscal_year_end
            
            pl_data = self._compute_profit_loss(company, date_from, date_to)
            
            report_data.append({
                'declaration': declaration,
                'company': company,
                'date_from': date_from,
                'date_to': date_to,
                'revenues': pl_data['revenues'],
                'expenses': pl_data['expenses'],
                'total_revenues': pl_data['total_revenues'],
                'total_expenses': pl_data['total_expenses'],
                'result': pl_data['result'],
            })
        
        return {
            'doc_ids': docids,
            'doc_model': 'biztax.declaration',
            'docs': docs,
            'data': data,
            'report_data': report_data,
        }
    
    def _compute_profit_loss(self, company, date_from, date_to):
        """
        Compute P&L from account balances
        Belgian PCMN structure:
        - Class 6: Charges
        - Class 7: Produits
        """
        AccountMoveLine = self.env['account.move.line']
        
        def get_balance(domain):
            lines = AccountMoveLine.search(domain + [
                ('company_id', '=', company.id),
                ('date', '>=', date_from),
                ('date', '<=', date_to),
                ('parent_state', '=', 'posted'),
            ])
            return sum(lines.mapped('balance'))
        
        revenues = {
            'operating': {
                'name': 'PRODUITS D\'EXPLOITATION',
                'items': [
                    {'code': '70', 'name': 'Chiffre d\'affaires', 
                     'amount': -get_balance([('account_id.code', '=like', '70%')])},
                    {'code': '71', 'name': 'Variation des stocks (en-cours, produits finis)', 
                     'amount': -get_balance([('account_id.code', '=like', '71%')])},
                    {'code': '72', 'name': 'Production immobilisée', 
                     'amount': -get_balance([('account_id.code', '=like', '72%')])},
                    {'code': '74', 'name': 'Autres produits d\'exploitation', 
                     'amount': -get_balance([('account_id.code', '=like', '74%')])},
                ],
            },
            'financial': {
                'name': 'PRODUITS FINANCIERS',
                'items': [
                    {'code': '75', 'name': 'Produits financiers', 
                     'amount': -get_balance([('account_id.code', '=like', '75%')])},
                ],
            },
            'exceptional': {
                'name': 'PRODUITS EXCEPTIONNELS',
                'items': [
                    {'code': '76-77', 'name': 'Produits exceptionnels', 
                     'amount': -get_balance([('account_id.code', '=like', '76%')]) -
                              get_balance([('account_id.code', '=like', '77%')])},
                ],
            },
        }
        
        expenses = {
            'operating': {
                'name': 'CHARGES D\'EXPLOITATION',
                'items': [
                    {'code': '60', 'name': 'Approvisionnements et marchandises', 
                     'amount': get_balance([('account_id.code', '=like', '60%')])},
                    {'code': '61', 'name': 'Services et biens divers', 
                     'amount': get_balance([('account_id.code', '=like', '61%')])},
                    {'code': '62', 'name': 'Rémunérations, charges sociales', 
                     'amount': get_balance([('account_id.code', '=like', '62%')])},
                    {'code': '63', 'name': 'Amortissements et réductions de valeur', 
                     'amount': get_balance([('account_id.code', '=like', '63%')])},
                    {'code': '64', 'name': 'Autres charges d\'exploitation', 
                     'amount': get_balance([('account_id.code', '=like', '64%')])},
                ],
            },
            'financial': {
                'name': 'CHARGES FINANCIÈRES',
                'items': [
                    {'code': '65', 'name': 'Charges financières', 
                     'amount': get_balance([('account_id.code', '=like', '65%')])},
                ],
            },
            'exceptional': {
                'name': 'CHARGES EXCEPTIONNELLES',
                'items': [
                    {'code': '66-67', 'name': 'Charges exceptionnelles', 
                     'amount': get_balance([('account_id.code', '=like', '66%')]) +
                              get_balance([('account_id.code', '=like', '67%')])},
                ],
            },
            'taxes': {
                'name': 'IMPÔTS',
                'items': [
                    {'code': '67', 'name': 'Impôts sur le résultat', 
                     'amount': get_balance([('account_id.code', '=like', '67%')])},
                ],
            },
        }
        
        total_revenues = sum(
            sum(item['amount'] for item in section['items'])
            for section in revenues.values()
        )
        total_expenses = sum(
            sum(item['amount'] for item in section['items'])
            for section in expenses.values()
        )
        
        return {
            'revenues': revenues,
            'expenses': expenses,
            'total_revenues': total_revenues,
            'total_expenses': total_expenses,
            'result': total_revenues - total_expenses,
        }


class BiztaxDNADetailReport(models.AbstractModel):
    """
    Report model for DNA (Dépenses Non Admises) detail
    """
    _name = 'report.lolirine_biztax.report_dna_detail'
    _description = 'Détail DNA - Rapport Biztax'

    @api.model
    def _get_report_values(self, docids, data=None):
        docs = self.env['biztax.declaration'].browse(docids)
        
        report_data = []
        for declaration in docs:
            # Filter DNA adjustments
            dna_adjustments = declaration.adjustment_ids.filtered(
                lambda a: a.category and 'dna' in a.category.lower()
            )
            
            # Group by subcategory
            dna_by_category = {}
            for adj in dna_adjustments:
                cat = adj.category or 'other'
                if cat not in dna_by_category:
                    dna_by_category[cat] = {
                        'name': dict(adj._fields['category'].selection).get(cat, cat),
                        'items': [],
                        'total': 0,
                    }
                dna_by_category[cat]['items'].append(adj)
                dna_by_category[cat]['total'] += adj.amount
            
            report_data.append({
                'declaration': declaration,
                'dna_by_category': dna_by_category,
                'total_dna': sum(c['total'] for c in dna_by_category.values()),
            })
        
        return {
            'doc_ids': docids,
            'doc_model': 'biztax.declaration',
            'docs': docs,
            'data': data,
            'report_data': report_data,
        }


class BiztaxFiscalSummaryReport(models.AbstractModel):
    """
    Report model for complete fiscal summary
    """
    _name = 'report.lolirine_biztax.report_fiscal_summary'
    _description = 'Résumé fiscal - Rapport Biztax'

    @api.model
    def _get_report_values(self, docids, data=None):
        docs = self.env['biztax.declaration'].browse(docids)
        
        return {
            'doc_ids': docids,
            'doc_model': 'biztax.declaration',
            'docs': docs,
            'data': data,
        }
