# -*- coding: utf-8 -*-
# Migration script for km_expense module from Odoo 18 to Odoo 19
# 
# Changes in this version:
# - Updated self._context to self.env.context (deprecated in Odoo 19)
# - Version updated from 18.0.1.0.0 to 19.0.1.0.0

import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """
    Post-migration script for km_expense module.
    
    This migration handles the update from Odoo 18 to Odoo 19.
    No data migration is required - only code changes were made:
    - self._context replaced with self.env.context in km_trajet.py
    """
    if not version:
        return
    
    _logger.info("km_expense: Migration from %s to 19.0.1.0.0 completed", version)
    _logger.info("km_expense: Code updated - self._context replaced with self.env.context")
