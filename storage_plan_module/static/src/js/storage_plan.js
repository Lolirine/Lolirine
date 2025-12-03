/**
 * Plan Interactif Garde-Meubles - JavaScript
 * Version simplifiée avec jQuery pur
 */
(function() {
    'use strict';

    // Variable globale pour empêcher la réouverture de la modal
    var modalLocked = false;
    var lastModalCloseTime = 0;

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
                   $('#oe_manipulators').length > 0 ||
                   $('.o_we_website_top_actions').length > 0 ||
                   $('body').hasClass('o_we_command_open');
        }
        
        // Événement clic sur les boxes disponibles (désactivé en mode édition)
        $(document).on('click', '.storage-box[data-status="disponible"]', function(e) {
            // Ne pas ouvrir si on est en mode édition
            if (isEditMode()) {
                return;
            }
            
            // Ne pas réouvrir si la modal vient d'être fermée (1 seconde de délai)
            var now = Date.now();
            if (now - lastModalCloseTime < 1000) {
                console.log('Modal recently closed, preventing reopen');
                return;
            }
            
            // Ne pas ouvrir si la modal est verrouillée
            if (modalLocked) {
                console.log('Modal locked, preventing open');
                return;
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

        // Fermer automatiquement la modal après clic sur les boutons
        $(document).on('click', '#btn-appointment, #btn-reserve', function(e) {
            // Ne pas fermer si on est en mode édition
            if (isEditMode()) {
                return; // Laisser l'édition se faire
            }
            // Fermer la modal après ouverture du lien
            setTimeout(function() {
                closeModal();
            }, 200);
        });

        // Gestionnaire explicite pour le bouton de fermeture (ID spécifique)
        $(document).on('click', '#btn-close-modal', function(e) {
            e.preventDefault();
            closeModal();
        });

        // Gestionnaire pour tous les éléments avec data-dismiss="modal"
        $(document).on('click', '[data-dismiss="modal"]', function(e) {
            e.preventDefault();
            closeModal();
        });

        // Gestionnaire pour le bouton close (par classe)
        $(document).on('click', '.modal .close', function(e) {
            e.preventDefault();
            closeModal();
        });

        // Gestionnaire pour tous les liens target="_blank" dans la modal
        $(document).on('click', '.modal a[target="_blank"]', function(e) {
            // Ne pas fermer si on est en mode édition
            if (isEditMode()) {
                return; // Laisser l'édition se faire
            }
            // Sinon, fermer après ouverture du lien
            setTimeout(function() {
                closeModal();
            }, 200);
        });
        
        // Fermer la modal quand on clique sur "Enregistrer" dans l'éditeur
        $(document).on('click', '.o_we_website_top_actions .btn-primary, [data-action="save"], .o_we_save', function() {
            // Verrouiller la modal pendant 2 secondes après enregistrement
            modalLocked = true;
            setTimeout(function() {
                closeModal();
                // Déverrouiller après 2 secondes
                setTimeout(function() {
                    modalLocked = false;
                }, 2000);
            }, 500);
        });
        
        // Fermer la modal quand on quitte le mode édition
        $(document).on('click', '.o_we_website_top_actions .btn-secondary, [data-action="cancel"]', function() {
            modalLocked = true;
            setTimeout(function() {
                closeModal();
                setTimeout(function() {
                    modalLocked = false;
                }, 2000);
            }, 300);
        });

        // Fonction robuste pour fermer la modal
        function closeModal() {
            console.log('Closing modal...');
            
            // Enregistrer le timestamp de fermeture
            lastModalCloseTime = Date.now();
            
            // Méthode 1 : Bootstrap modal
            try {
                $('#boxDetailsModal').modal('hide');
            } catch(e) {}
            
            // Méthode 2 : Supprimer les classes Bootstrap
            $('#boxDetailsModal').removeClass('show').removeClass('in');
            $('#boxDetailsModal').attr('aria-hidden', 'true');
            $('#boxDetailsModal').css('display', 'none');
            $('.modal-backdrop').remove();
            $('body').removeClass('modal-open');
            $('body').css('padding-right', '');
            $('body').css('overflow', '');
            
            // Méthode 3 : Cacher directement
            $('#boxDetailsModal').hide();
            
            console.log('Modal closed at:', lastModalCloseTime);
        }

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
            {indices: [4, 5, 6, 7], color: '#D2691E', label: 'Face avant'}, // Avant - plus foncé
            {indices: [0, 1, 2, 3], color: '#8B4513', label: 'Face arrière'}, // Arrière - le plus foncé
            {indices: [4, 0, 3, 7], color: '#CD853F', label: 'Côté gauche'}, // Gauche - moyen
            {indices: [1, 5, 6, 2], color: '#DEB887', label: 'Côté droit'}, // Droit - clair
            {indices: [3, 2, 6, 7], color: '#F4A460', label: 'Dessus'}, // Dessus - très clair
            {indices: [4, 5, 1, 0], color: '#A0522D', label: 'Dessous'} // Dessous - foncé
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
