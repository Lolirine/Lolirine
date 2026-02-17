# -*- coding: utf-8 -*-

from . import models
from . import wizards

import logging
_logger = logging.getLogger(__name__)


def _post_init_hook(env):
    """Recompute is_dropship_order on existing orders after install/update"""
    _logger.info("=== lolirine_pool_dropship: post_init_hook START ===")
    env.cr.execute("""
        UPDATE sale_order so
        SET is_dropship_order = TRUE
        WHERE EXISTS (
            SELECT 1
            FROM sale_order_line sol
            JOIN product_product pp ON pp.id = sol.product_id
            JOIN product_template pt ON pt.id = pp.product_tmpl_id
            WHERE sol.order_id = so.id
              AND pt.is_dropship_product = TRUE
        )
        AND (so.is_dropship_order IS NULL OR so.is_dropship_order = FALSE)
    """)
    updated = env.cr.rowcount
    _logger.info("post_init_hook: %d sale orders marked as dropship", updated)
    _logger.info("=== lolirine_pool_dropship: post_init_hook END ===")
