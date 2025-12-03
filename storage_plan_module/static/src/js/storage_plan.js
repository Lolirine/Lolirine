/**
 * Plan Interactif Garde-Meubles - JavaScript
 * Version simplifiée avec jQuery pur
 */
(function() {
    'use strict';

    // Attendre que le DOM soit chargé
    $(document).ready(function() {
        console.log('Storage Plan JS loaded');
        initializeStoragePlan();
    });

    function initializeStoragePlan() {
        // Vérifier si on est en mode édition
        function isEditMode() {
            return $('body').hasClass('editor_enable') || 
                   window.location.search.indexOf('enable_editor') > -1 ||
                   $('#oe_manipulators').length > 0;
        }
        
        // Événement clic sur les boxes disponibles (désactivé en mode édition)
        $(document).on('click', '.storage-box[data-status="disponible"]', function(e) {
            if (isEditMode()) {
                return; // Ne rien faire en mode édition
            }
            
            e.preventDefault();
            var boxId = parseInt($(this).data('box-id'));
            console.log('Box clicked:', boxId);
            
            if (boxId) {
                loadBoxDetails(boxId);
            }
        });

        // Demande générale - vérifier si on doit rediriger ou non
        $(document).on('click', '#general-inquiry-btn', function(e) {
            // Si le lien est "#", empêcher la navigation par défaut
            var href = $(this).attr('href');
            if (href === '#') {
                e.preventDefault();
                alert('Contactez-nous au +32 50 XX XX XX ou par email à contact@lolirine.be');
            }
            // Sinon, laisser le lien fonctionner normalement (ex: /contactus)
        });

        console.log('Events initialized');
    }

    function loadBoxDetails(boxId) {
        console.log('Loading details for box:', boxId);
        
        $.ajax({
            url: '/storage/box/' + boxId + '/details',
            type: 'POST',
            contentType: 'application/json',
            data: JSON.stringify({
                jsonrpc: '2.0',
                method: 'call',
                params: {}
            }),
            success: function(response) {
                console.log('Response received:', response);
                
                if (response.error) {
                    alert('Erreur: ' + response.error.data.message);
                    return;
                }
                
                var result = response.result;
                if (result.error) {
                    alert(result.error);
                    return;
                }
                
                displayBoxDetails(result);
                // jQuery modal (Bootstrap 4 compatible)
                $('#boxDetailsModal').modal('show');
            },
            error: function(xhr, status, error) {
                console.error('AJAX Error:', status, error);
                alert('Erreur de connexion. Veuillez réessayer.');
            }
        });
    }

    function displayBoxDetails(boxData) {
        console.log('Displaying box details:', boxData);
        
        // Mettre à jour les informations textuelles
        $('#detail-box-name').text(boxData.name);
        $('#detail-width').text(boxData.width + ' cm');
        $('#detail-depth').text(boxData.depth + ' cm');
        $('#detail-height').text(boxData.height + ' cm');
        $('#detail-volume').html('<strong>' + boxData.volume + ' m³</strong>');
        $('#detail-price').html('<strong>' + boxData.price_monthly + ' €/Mois</strong>');
        $('#detail-registration-fee').text(boxData.registration_fee + ' €');
        $('#detail-deposit').text(boxData.deposit_months + ' mois de loyer');
        
        // Badge du statut
        var $statusBadge = $('#detail-status');
        $statusBadge.text(boxData.status_label);
        $statusBadge.removeClass('badge-success badge-danger badge-warning badge-info');
        
        switch (boxData.status) {
            case 'disponible':
                $statusBadge.addClass('badge-success');
                break;
            case 'occupe':
                $statusBadge.addClass('badge-danger');
                break;
            case 'maintenance':
                $statusBadge.addClass('badge-warning');
                break;
            default:
                $statusBadge.addClass('badge-info');
        }
        
        // Activer/désactiver les boutons visuellement
        var isAvailable = boxData.status === 'disponible';
        if (isAvailable) {
            $('#btn-appointment, #btn-reserve').removeClass('disabled').css('pointer-events', 'auto');
        } else {
            $('#btn-appointment, #btn-reserve').addClass('disabled').css('pointer-events', 'none');
        }
        
        // Dessiner la vue 3D
        draw3DBox(boxData);
    }

    function draw3DBox(boxData) {
        var canvas = document.getElementById('box-3d-canvas');
        if (!canvas) return;
        
        var ctx = canvas.getContext('2d');
        var canvasWidth = canvas.width;
        var canvasHeight = canvas.height;
        
        ctx.clearRect(0, 0, canvasWidth, canvasHeight);
        
        var scale = Math.min(canvasWidth, canvasHeight) / Math.max(boxData.width, boxData.depth, boxData.height) * 0.6;
        var centerX = canvasWidth / 2;
        var centerY = canvasHeight / 2;
        var w = boxData.width * scale;
        var d = boxData.depth * scale;
        var h = boxData.height * scale;
        var angleX = Math.PI / 6;
        var angleY = Math.PI / 4;
        
        function project(x, y, z) {
            var cosX = Math.cos(angleX);
            var sinX = Math.sin(angleX);
            var cosY = Math.cos(angleY);
            var sinY = Math.sin(angleY);
            var x1 = x * cosY + z * sinY;
            var y1 = x * sinX * sinY + y * cosX - z * sinX * cosY;
            return {x: centerX + x1, y: centerY - y1};
        }
        
        var vertices = [
            {x: -w/2, y: -h/2, z: -d/2}, {x: w/2, y: -h/2, z: -d/2},
            {x: w/2, y: h/2, z: -d/2}, {x: -w/2, y: h/2, z: -d/2},
            {x: -w/2, y: -h/2, z: d/2}, {x: w/2, y: -h/2, z: d/2},
            {x: w/2, y: h/2, z: d/2}, {x: -w/2, y: h/2, z: d/2}
        ];
        
        var projectedVertices = vertices.map(function(v) {
            return project(v.x, v.y, v.z);
        });
        
        var faces = [
            {indices: [4, 5, 6, 7], color: '#F4A460'},
            {indices: [0, 1, 2, 3], color: '#CD853F'},
            {indices: [0, 1, 5, 4], color: '#D2691E'},
            {indices: [3, 2, 6, 7], color: '#DEB887'},
            {indices: [0, 3, 7, 4], color: '#C19A6B'},
            {indices: [1, 2, 6, 5], color: '#B8860B'}
        ];
        
        faces.forEach(function(face) {
            ctx.beginPath();
            face.indices.forEach(function(idx, i) {
                var p = projectedVertices[idx];
                if (i === 0) ctx.moveTo(p.x, p.y);
                else ctx.lineTo(p.x, p.y);
            });
            ctx.closePath();
            ctx.fillStyle = face.color;
            ctx.fill();
            ctx.strokeStyle = '#8B4513';
            ctx.lineWidth = 2;
            ctx.stroke();
        });
        
        var edges = [[0, 1], [1, 2], [2, 3], [3, 0], [4, 5], [5, 6], [6, 7], [7, 4], [0, 4], [1, 5], [2, 6], [3, 7]];
        ctx.strokeStyle = '#8B0000';
        ctx.lineWidth = 3;
        edges.forEach(function(edge) {
            var p1 = projectedVertices[edge[0]];
            var p2 = projectedVertices[edge[1]];
            ctx.beginPath();
            ctx.moveTo(p1.x, p1.y);
            ctx.lineTo(p2.x, p2.y);
            ctx.stroke();
        });
        
        ctx.font = 'bold 14px Arial';
        ctx.fillStyle = '#333';
        ctx.textAlign = 'center';
        var widthLabelPos = project(0, -h/2 - 30, d/2);
        ctx.fillText(boxData.width + ' cm (Largeur)', widthLabelPos.x, widthLabelPos.y);
        var depthLabelPos = project(w/2 + 30, -h/2 - 20, 0);
        ctx.fillText(boxData.depth + ' cm (Profondeur)', depthLabelPos.x, depthLabelPos.y);
        var heightLabelPos = project(-w/2 - 40, 0, -d/2 - 20);
        ctx.save();
        ctx.translate(heightLabelPos.x, heightLabelPos.y);
        ctx.rotate(-Math.PI / 2);
        ctx.fillText(boxData.height + ' cm (Hauteur)', 0, 0);
        ctx.restore();
    }

})();
