odoo.define('storage_plan_module.editor', function (require) {
'use strict';

var options = require('web_editor.snippets.options');

// Option pour personnaliser les boutons du plan de stockage
options.registry.StoragePlanButtons = options.Class.extend({
    
    /**
     * @override
     */
    start: function () {
        this._super.apply(this, arguments);
    },
    
    // Changer le style du bouton
    selectClass: function (previewMode, value, $opt) {
        this.$target.removeClass('btn-primary btn-secondary btn-success btn-danger btn-warning btn-info btn-light btn-dark');
        if (value) {
            this.$target.addClass(value);
        }
    },
    
    // Changer la taille du bouton
    selectSize: function (previewMode, value, $opt) {
        this.$target.removeClass('btn-sm btn-lg');
        if (value) {
            this.$target.addClass(value);
        }
    },
    
    // Rendre le bouton pleine largeur ou non
    setFullWidth: function (previewMode, value, $opt) {
        this.$target.toggleClass('w-100', value === 'true');
    },

});

return {
    StoragePlanButtons: options.registry.StoragePlanButtons,
};

});
