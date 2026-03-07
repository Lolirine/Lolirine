(function () {
    'use strict';

    document.addEventListener('DOMContentLoaded', function () {
        try {
            initVariantImageSwitcher();
        } catch (e) {
            console.debug('Pool variant images: init skipped', e);
        }
    });

    function initVariantImageSwitcher() {
        var productDetail = document.getElementById('product_detail')
            || document.querySelector('.oe_website_sale .o_wsale_product_page')
            || document.querySelector('.oe_website_sale');

        if (!productDetail) return;

        var tmplId = findTemplateId(productDetail);
        if (!tmplId) return;

        var mainImg = getMainImage(productDetail);
        var originalSrc = mainImg ? mainImg.src : '';

        fetchVariantImages(tmplId, function (data) {
            if (!data || !data.attribute_values) return;

            productDetail.addEventListener('change', function (e) {
                if (e.target.matches('.js_variant_change, input[type="radio"], select')) {
                    setTimeout(function () { updateImage(productDetail, data, originalSrc); }, 100);
                }
            });

            productDetail.addEventListener('click', function (e) {
                var target = e.target.closest('.css_attribute_color input, .o_variant_pills .btn, input[type="radio"]');
                if (target) {
                    setTimeout(function () { updateImage(productDetail, data, originalSrc); }, 100);
                }
            });

            addThumbnails(productDetail, data);
        });
    }

    function findTemplateId(container) {
        var el = container.querySelector('[data-product-template-id]');
        if (el) return parseInt(el.dataset.productTemplateId, 10);

        el = container.querySelector('input[name="product_template_id"]');
        if (el && el.value) return parseInt(el.value, 10);

        if (document.body.dataset.productTemplateId)
            return parseInt(document.body.dataset.productTemplateId, 10);

        var forms = container.querySelectorAll('form');
        for (var i = 0; i < forms.length; i++) {
            el = forms[i].querySelector('input[name="product_template_id"]');
            if (el && el.value) return parseInt(el.value, 10);
        }
        return 0;
    }

    function getMainImage(container) {
        return container.querySelector('.product_detail_img')
            || container.querySelector('#o-carousel-product .carousel-item.active img')
            || container.querySelector('.o_wsale_product_main_image img')
            || container.querySelector('.oe_product_image img');
    }

    function fetchVariantImages(tmplId, callback) {
        var xhr = new XMLHttpRequest();
        xhr.open('POST', '/pool/variant_images/' + tmplId, true);
        xhr.setRequestHeader('Content-Type', 'application/json');
        xhr.onreadystatechange = function () {
            if (xhr.readyState === 4 && xhr.status === 200) {
                try {
                    var response = JSON.parse(xhr.responseText);
                    callback(response.result || response);
                } catch (e) {
                    console.debug('Pool variant images: parse error', e);
                }
            }
        };
        xhr.send(JSON.stringify({ jsonrpc: '2.0', method: 'call', params: {} }));
    }

    function updateImage(container, data, originalSrc) {
        var selectedIds = getSelectedPtavIds(container);
        var imageUrl = '';

        var priorityWords = ['couleur', 'meuble', 'color', 'finition', 'cuve'];
        for (var i = 0; i < selectedIds.length; i++) {
            var info = data.attribute_values[String(selectedIds[i])];
            if (info && info.has_image) {
                var attrLower = (info.attribute_name || '').toLowerCase();
                for (var j = 0; j < priorityWords.length; j++) {
                    if (attrLower.indexOf(priorityWords[j]) >= 0) {
                        imageUrl = info.image_url;
                        break;
                    }
                }
                if (imageUrl) break;
            }
        }

        if (!imageUrl) {
            for (var i = 0; i < selectedIds.length; i++) {
                var info = data.attribute_values[String(selectedIds[i])];
                if (info && info.has_image && info.image_url) {
                    imageUrl = info.image_url;
                    break;
                }
            }
        }

        var img = getMainImage(container);
        if (!img) return;

        var targetUrl = imageUrl || originalSrc;
        if (img.src === targetUrl) return;

        img.style.transition = 'opacity 0.25s ease';
        img.style.opacity = '0.3';

        var preloader = new Image();
        preloader.onload = function () { img.src = targetUrl; img.style.opacity = '1'; };
        preloader.onerror = function () { img.style.opacity = '1'; };
        preloader.src = targetUrl;
    }

    function getSelectedPtavIds(container) {
        var ids = [];
        var checked = container.querySelectorAll('input.js_variant_change:checked, input[type="radio"]:checked');
        for (var i = 0; i < checked.length; i++) {
            var v = parseInt(checked[i].value, 10);
            if (v) ids.push(v);
        }
        var selects = container.querySelectorAll('select.js_variant_change');
        for (var i = 0; i < selects.length; i++) {
            var v = parseInt(selects[i].value, 10);
            if (v) ids.push(v);
        }
        var pills = container.querySelectorAll('.o_variant_pills .btn.active');
        for (var i = 0; i < pills.length; i++) {
            var v = parseInt(pills[i].dataset.value_id || pills[i].dataset.attributeValueId || 0, 10);
            if (v) ids.push(v);
        }
        return ids;
    }

    function addThumbnails(container, data) {
        for (var ptavId in data.attribute_values) {
            var info = data.attribute_values[ptavId];
            if (!info.has_image) continue;

            var input = container.querySelector('input[value="' + ptavId + '"], [data-value_id="' + ptavId + '"]');
            if (!input) continue;

            var label = input.closest('label') || (input.parentElement ? input.parentElement.querySelector('label') : null);
            if (label && !label.querySelector('.pool-variant-thumb')) {
                var thumb = document.createElement('img');
                thumb.className = 'pool-variant-thumb';
                thumb.src = '/pool/variant_image_128/' + ptavId;
                thumb.alt = info.value_name;
                label.insertBefore(thumb, label.firstChild);
            
        }
    }
})();
