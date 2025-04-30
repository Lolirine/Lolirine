odoo.define('box_storage_map.box_map', function (require) {
    const publicWidget = require('web.public.widget');

    publicWidget.registry.BoxMap = publicWidget.Widget.extend({
        selector: 'svg',
        events: {
            'click rect': '_onClickBox',
        },

        _onClickBox: function (event) {
            const boxId = event.currentTarget.dataset.boxId;
            window.location.href = `/web#id=${boxId}&model=box.stockage&view_type=form`;
        },
    });
});