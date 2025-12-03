/**
 * Plan Interactif Garde-Meubles - JavaScript
 * Version 1.0.21 - Simplifiée et corrigée
 */
(function() {
    'use strict';

    $(document).ready(function() {
        console.log('Storage Plan JS loaded v1.0.22');
        initializeStoragePlan();
    });

    function initializeStoragePlan() {
        
        // ============================================
        // DÉTECTION DU MODE ÉDITION
        // ============================================
        function isEditMode() {
            return $('body').hasClass('editor_enable') ||
                   window.location.search.indexOf('enable_editor') > -1 ||
                   $('.o_we_website_top_actions:visible').length > 0;
        }

        // ============================================
        // FERMER LA MODAL
        // ============================================
        function closeModal() {
            console.log('Closing modal');
            
            // Bootstrap
            try {
                $('#boxDetailsModal').modal('hide');
            } catch(e) {}
            
            // Nettoyage manuel
            $('#boxDetailsModal').removeClass('show in').hide();
            $('#boxDetailsModal').attr('aria-hidden', 'true');
            $('.modal-backdrop').remove();
            $('body').removeClass('modal-open');
            $('body').css({'padding-right': '', 'overflow': ''});
        }

        // ============================================
        // ÉVÉNEMENTS DE CLIC SUR LES BOXES
        // ============================================
        // Permettre le clic sur TOUS les boxes pour voir les informations
        $(document).on('click', '.storage-box', function(e) {
            e.preventDefault();
            e.stopPropagation();
            
            // Ne pas ouvrir en mode édition
            if (isEditMode()) {
                console.log('Edit mode, ignoring click');
                return false;
            }
            
            var boxId = parseInt($(this).data('box-id'));
            console.log('Box clicked:', boxId);
            
            if (boxId) {
                loadBoxDetails(boxId);
            }
            
            return false;
        });

        // ============================================
        // BOUTON DEMANDE GÉNÉRALE
        // ============================================
        $(document).on('click', '#general-inquiry-btn', function(e) {
            var href = $(this).attr('href');
            if (href === '#') {
                e.preventDefault();
                alert('Contactez-nous au +32 50 XX XX XX ou par email à contact@lolirine.be');
            }
        });

        // ============================================
        // BOUTONS D'ACTION DANS LA MODAL
        // ============================================
        $(document).on('click', '#btn-appointment, #btn-reserve', function(e) {
            if (isEditMode()) {
                return;
            }
            setTimeout(closeModal, 300);
        });

        // ============================================
        // BOUTON FERMER LA MODAL
        // ============================================
        $(document).on('click', '#btn-close-modal, .modal .close, [data-dismiss="modal"], .modal .btn-close', function(e) {
            e.preventDefault();
            closeModal();
        });

        // ============================================
        // LIENS EXTERNES DANS LA MODAL
        // ============================================
        $(document).on('click', '.modal a[target="_blank"]', function(e) {
            if (isEditMode()) {
                return;
            }
            setTimeout(closeModal, 300);
        });

        // ============================================
        // CLIC EN DEHORS DE LA MODAL
        // ============================================
        $(document).on('click', '#boxDetailsModal', function(e) {
            if ($(e.target).is('#boxDetailsModal')) {
                closeModal();
            }
        });

        // ============================================
        // TOUCHE ECHAP
        // ============================================
        $(document).on('keydown', function(e) {
            if (e.key === 'Escape' || e.keyCode === 27) {
                closeModal();
            }
        });
        
        // ============================================
        // FERMER SI MODE ÉDITION ACTIVÉ
        // ============================================
        if (typeof MutationObserver !== 'undefined') {
            var observer = new MutationObserver(function(mutations) {
                if (isEditMode() && $('#boxDetailsModal').is(':visible')) {
                    closeModal();
                }
            });
            observer.observe(document.body, { attributes: true, attributeFilter: ['class'] });
        }

        // ============================================
        // CHARGEMENT DES DÉTAILS D'UN BOX
        // ============================================
        function loadBoxDetails(boxId) {
            if (isEditMode()) {
                return;
            }
            
            $.ajax({
                url: '/storage/box/' + boxId + '/details',
                type: 'POST',
                contentType: 'application/json',
                data: JSON.stringify({jsonrpc: '2.0', method: 'call', params: {}}),
                success: function(response) {
                    if (isEditMode()) {
                        return;
                    }
                    if (response.result) {
                        displayBoxDetails(response.result);
                    } else if (response.error) {
                        console.error('Erreur:', response.error);
                    }
                },
                error: function(xhr, status, error) {
                    console.error('Erreur AJAX:', error);
                }
            });
        }

        // ============================================
        // AFFICHAGE DES DÉTAILS
        // ============================================
        function displayBoxDetails(boxData) {
            if (isEditMode()) {
                return;
            }
            
            console.log('Displaying box details:', boxData);
            
            // Remplir les données
            $('#detail-name').text('Box ' + boxData.name);
            $('#detail-floor').text(boxData.floor);
            $('#detail-surface').text(boxData.surface + ' m²');
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
            
            // Afficher la date de disponibilité si présente et si le box n'est pas disponible
            if (boxData.status !== 'disponible' && boxData.date_available) {
                $('#detail-date-available-label').show();
                $('#detail-date-available').text(boxData.date_available).show();
            } else {
                $('#detail-date-available-label').hide();
                $('#detail-date-available').hide();
            }
            
            // Activer/désactiver les boutons
            var isAvailable = boxData.status === 'disponible';
            if (isAvailable) {
                $('#btn-appointment, #btn-reserve').removeClass('disabled').css('pointer-events', 'auto');
            } else {
                $('#btn-appointment, #btn-reserve').addClass('disabled').css('pointer-events', 'none');
            }
            
            // Dessiner la vue 3D
            draw3DBox(boxData);
            
            // Afficher la modal
            try {
                $('#boxDetailsModal').modal('show');
            } catch(e) {
                $('#boxDetailsModal').addClass('show').css('display', 'block');
                $('body').addClass('modal-open');
                if (!$('.modal-backdrop').length) {
                    $('body').append('<div class="modal-backdrop fade show"></div>');
                }
            }
        }

        // ============================================
        // DESSIN 3D DU BOX
        // ============================================
        function draw3DBox(boxData) {
            var canvas = document.getElementById('box-3d-canvas');
            if (!canvas) return;
            
            var ctx = canvas.getContext('2d');
            var canvasWidth = canvas.width;
            var canvasHeight = canvas.height;
            
            ctx.clearRect(0, 0, canvasWidth, canvasHeight);
            
            var maxDim = Math.max(boxData.width, boxData.depth, boxData.height);
            var scale = Math.min(canvasWidth, canvasHeight) / maxDim * 0.5;
            
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
                {indices: [4, 5, 6, 7], color: '#D2691E'},
                {indices: [0, 1, 2, 3], color: '#8B4513'},
                {indices: [4, 0, 3, 7], color: '#CD853F'},
                {indices: [1, 5, 6, 2], color: '#DEB887'},
                {indices: [3, 2, 6, 7], color: '#F4A460'},
                {indices: [4, 5, 1, 0], color: '#A0522D'}
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
                ctx.strokeStyle = '#5D4E37';
                ctx.lineWidth = 1.5;
                ctx.stroke();
            });
            
            var edges = [[0, 1], [1, 2], [2, 3], [3, 0], [4, 5], [5, 6], [6, 7], [7, 4], [0, 4], [1, 5], [2, 6], [3, 7]];
            ctx.strokeStyle = '#3E2723';
            ctx.lineWidth = 2;
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
    }
})();
