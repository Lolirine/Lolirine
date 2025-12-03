/**
 * Plan Interactif Garde-Meubles - JavaScript
 * Version avec gestion ultra-robuste de la modal en mode édition
 */
(function() {
    'use strict';

    // Variables globales pour le contrôle de la modal
    var modalBlocked = false;
    var lastModalCloseTime = 0;
    var MODAL_BLOCK_DURATION = 2000; // 2 secondes de blocage après fermeture

    // Attendre que le DOM soit chargé
    $(document).ready(function() {
        console.log('Storage Plan JS loaded v1.0.20');
        initializeStoragePlan();
    });

    function initializeStoragePlan() {
        
        // ============================================
        // DÉTECTION DU MODE ÉDITION - PRÉCISE
        // ============================================
        function isEditMode() {
            // Vérifier uniquement les conditions fiables du mode édition Odoo
            var editModeDetected = 
                // Classes sur body (les plus fiables)
                $('body').hasClass('editor_enable') ||
                $('body').hasClass('o_we_command_open') ||
                
                // URL avec paramètre d'édition
                window.location.search.indexOf('enable_editor') > -1 ||
                
                // Éléments spécifiques de l'éditeur actif
                $('#oe_manipulators').length > 0 ||
                $('.o_we_website_top_actions:visible').length > 0 ||
                $('.oe_overlay:visible').length > 0;
            
            return editModeDetected;
        }
        
        // Log au démarrage pour debug
        console.log('Edit mode at startup:', isEditMode());

        // ============================================
        // VÉRIFICATION AVANT OUVERTURE DE LA MODAL
        // ============================================
        function canOpenModal() {
            var editMode = isEditMode();
            console.log('canOpenModal check - editMode:', editMode, 'modalBlocked:', modalBlocked);
            
            // Blocage manuel actif
            if (modalBlocked) {
                console.log('Modal blocked manually');
                return false;
            }
            
            // Mode édition actif
            if (isEditMode()) {
                console.log('Edit mode detected, modal blocked');
                return false;
            }
            
            // Fermeture récente (moins de 5 secondes)
            var now = Date.now();
            if (now - lastModalCloseTime < MODAL_BLOCK_DURATION) {
                console.log('Modal closed recently, blocking for', MODAL_BLOCK_DURATION - (now - lastModalCloseTime), 'ms more');
                return false;
            }
            
            // Modal déjà visible
            if ($('#boxDetailsModal').is(':visible') || $('#boxDetailsModal').hasClass('show')) {
                console.log('Modal already visible');
                return false;
            }
            
            return true;
        }

        // ============================================
        // BLOQUER LA MODAL
        // ============================================
        function blockModal(duration) {
            duration = duration || MODAL_BLOCK_DURATION;
            modalBlocked = true;
            console.log('Modal blocked for', duration, 'ms');
            setTimeout(function() {
                modalBlocked = false;
                console.log('Modal unblocked');
            }, duration);
        }

        // ============================================
        // FERMER LA MODAL - MÉTHODE ULTIME
        // ============================================
        function closeModal() {
            console.log('Closing modal...');
            
            // Enregistrer le timestamp
            lastModalCloseTime = Date.now();
            
            // Bloquer la modal
            blockModal();
            
            // Méthode 1: Bootstrap
            try {
                $('#boxDetailsModal').modal('hide');
            } catch(e) {
                console.log('Bootstrap modal hide failed:', e);
            }
            
            // Méthode 2: Classes CSS
            $('#boxDetailsModal').removeClass('show in fade');
            $('#boxDetailsModal').attr('aria-hidden', 'true');
            $('#boxDetailsModal').css({
                'display': 'none',
                'opacity': '0',
                'visibility': 'hidden'
            });
            
            // Méthode 3: Backdrop
            $('.modal-backdrop').remove();
            
            // Méthode 4: Body
            $('body').removeClass('modal-open');
            $('body').css({
                'padding-right': '',
                'overflow': ''
            });
            
            // Méthode 5: Hide jQuery
            $('#boxDetailsModal').hide();
            
            console.log('Modal closed, blocked until', new Date(lastModalCloseTime + MODAL_BLOCK_DURATION));
        }

        // ============================================
        // SURVEILLANCE DU MODE ÉDITION
        // ============================================
        // Fermer la modal si on entre en mode édition pendant qu'elle est ouverte
        setInterval(function() {
            if (isEditMode() && ($('#boxDetailsModal').is(':visible') || $('#boxDetailsModal').hasClass('show'))) {
                console.log('Edit mode detected while modal open, closing...');
                closeModal();
            }
        }, 500);

        // Observer les changements sur body pour détecter l'entrée en mode édition
        if (typeof MutationObserver !== 'undefined') {
            var observer = new MutationObserver(function(mutations) {
                mutations.forEach(function(mutation) {
                    if (mutation.attributeName === 'class') {
                        var bodyClasses = $('body').attr('class') || '';
                        if (bodyClasses.indexOf('editor_enable') > -1) {
                            console.log('Entered edit mode via class change');
                            closeModal();
                        }
                    }
                });
            });
            
            observer.observe(document.body, {
                attributes: true,
                attributeFilter: ['class']
            });
        }

        // ============================================
        // ÉVÉNEMENTS DE CLIC SUR LES BOXES
        // ============================================
        $(document).on('click', '.storage-box[data-status="disponible"]', function(e) {
            // Vérification complète
            if (!canOpenModal()) {
                e.preventDefault();
                e.stopPropagation();
                return false;
            }
            
            e.preventDefault();
            var boxId = parseInt($(this).data('box-id'));
            console.log('Box clicked:', boxId);
            
            if (boxId) {
                loadBoxDetails(boxId);
            }
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
                return; // Laisser l'édition se faire
            }
            setTimeout(function() {
                closeModal();
            }, 200);
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
            setTimeout(function() {
                closeModal();
            }, 200);
        });

        // ============================================
        // ÉVÉNEMENTS DE L'ÉDITEUR ODOO
        // ============================================
        // Quand on clique sur Enregistrer
        $(document).on('click', '[data-action="save"], .o_we_website_top_actions .btn-primary', function() {
            console.log('Save button clicked');
            closeModal();
            blockModal(3000); // Bloquer 3 secondes
        });
        
        // Quand on clique sur Annuler
        $(document).on('click', '[data-action="cancel"], .o_we_website_top_actions .btn-secondary', function() {
            console.log('Cancel button clicked');
            closeModal();
            blockModal(3000); // Bloquer 3 secondes
        });

        // ============================================
        // CLIC EN DEHORS DE LA MODAL
        // ============================================
        $(document).on('click', '.modal-backdrop, #boxDetailsModal', function(e) {
            if ($(e.target).is('.modal-backdrop') || $(e.target).is('#boxDetailsModal')) {
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
        // CHARGEMENT DES DÉTAILS D'UN BOX
        // ============================================
        function loadBoxDetails(boxId) {
            // Double vérification avant d'ouvrir
            if (!canOpenModal()) {
                console.log('Cannot open modal, aborting loadBoxDetails');
                return;
            }
            
            $.ajax({
                url: '/storage/box/' + boxId + '/details',
                type: 'POST',
                contentType: 'application/json',
                data: JSON.stringify({jsonrpc: '2.0', method: 'call', params: {}}),
                success: function(response) {
                    // Vérifier encore une fois avant d'afficher
                    if (!canOpenModal()) {
                        console.log('Cannot open modal after AJAX, aborting');
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
            // Dernière vérification
            if (!canOpenModal()) {
                console.log('Cannot open modal in displayBoxDetails');
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
                // Fallback si Bootstrap ne fonctionne pas
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
            
            // Utiliser les vraies proportions pour le scale
            var maxDim = Math.max(boxData.width, boxData.depth, boxData.height);
            var scale = Math.min(canvasWidth, canvasHeight) / maxDim * 0.5;
            
            var centerX = canvasWidth / 2;
            var centerY = canvasHeight / 2;
            
            // Dimensions proportionnelles
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
            
            // Faces avec des couleurs différentes pour la profondeur
            var faces = [
                {indices: [4, 5, 6, 7], color: '#D2691E', label: 'Face avant'},
                {indices: [0, 1, 2, 3], color: '#8B4513', label: 'Face arrière'},
                {indices: [4, 0, 3, 7], color: '#CD853F', label: 'Côté gauche'},
                {indices: [1, 5, 6, 2], color: '#DEB887', label: 'Côté droit'},
                {indices: [3, 2, 6, 7], color: '#F4A460', label: 'Dessus'},
                {indices: [4, 5, 1, 0], color: '#A0522D', label: 'Dessous'}
            ];
            
            // Dessiner les faces
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
            
            // Dessiner les arêtes principales
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
            
            // Labels des dimensions
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
