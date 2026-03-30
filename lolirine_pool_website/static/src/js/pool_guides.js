(function () {
    function initGuideToggle() {
        var btn  = document.getElementById('s_pool_guides_toggle');
        var grid = document.getElementById('s_pool_guides_grid');
        if (!btn || !grid) return;

        btn.addEventListener('click', function () {
            var expanded = grid.classList.toggle('spg-expanded');
            btn.textContent = expanded ? 'VOIR MOINS DE GUIDES' : 'VOIR PLUS DE GUIDES';
        });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initGuideToggle);
    } else {
        initGuideToggle();
    }
})();
