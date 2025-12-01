odoo.define('storage_plan_module.storage_plan', function (require) {
    'use strict';

    var publicWidget = require('web.public.widget');
    var ajax = require('web.ajax');

    publicWidget.registry.StoragePlan = publicWidget.Widget.extend({
        selector: '#storage-plans-container',
        events: {
            'click .storage-box[data-status="disponible"]': '_onBoxClick',
        },

        start: function () {
            this._super.apply(this, arguments);
            this._setupModalEvents();
            return this._super.apply(this, arguments);
        },

        _onBoxClick: function (ev) {
            ev.preventDefault();
            var $box = $(ev.currentTarget);
            var boxId = parseInt($box.data('box-id'));
            
            if (!boxId) return;
            
            this._loadBoxDetails(boxId);
        },

        _loadBoxDetails: function (boxId) {
            var self = this;
            
            ajax.jsonRpc('/storage/box/' + boxId + '/details', 'call', {})
                .then(function (result) {
                    if (result.error) {
                        alert(result.error);
                        return;
                    }
                    self._displayBoxDetails(result);
                    $('#boxDetailsModal').modal('show');
                });
        },

        _displayBoxDetails: function (boxData) {
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
            
            // Stocker l'ID du box pour les actions
            $('#selected-box-id').val(boxData.id);
            
            // Activer/désactiver les boutons selon le statut
            var isAvailable = boxData.status === 'disponible';
            $('#btn-appointment').prop('disabled', !isAvailable);
            $('#btn-reserve').prop('disabled', !isAvailable);
            
            // Dessiner la vue 3D
            this._draw3DBox(boxData);
        },

        _draw3DBox: function (boxData) {
            var canvas = document.getElementById('box-3d-canvas');
            if (!canvas) return;
            
            var ctx = canvas.getContext('2d');
            
            // Dimensions du canvas
            var canvasWidth = canvas.width;
            var canvasHeight = canvas.height;
            
            // Effacer le canvas
            ctx.clearRect(0, 0, canvasWidth, canvasHeight);
            
            // Échelle pour l'affichage
            var scale = Math.min(canvasWidth, canvasHeight) / Math.max(boxData.width, boxData.depth, boxData.height) * 0.6;
            
            // Centre du canvas
            var centerX = canvasWidth / 2;
            var centerY = canvasHeight / 2;
            
            // Dimensions mises à l'échelle
            var w = boxData.width * scale;
            var d = boxData.depth * scale;
            var h = boxData.height * scale;
            
            // Angles de rotation (isométrique)
            var angleX = Math.PI / 6; // 30 degrés
            var angleY = Math.PI / 4; // 45 degrés
            
            // Fonction de projection isométrique
            function project(x, y, z) {
                var cosX = Math.cos(angleX);
                var sinX = Math.sin(angleX);
                var cosY = Math.cos(angleY);
                var sinY = Math.sin(angleY);
                
                var x1 = x * cosY + z * sinY;
                var y1 = x * sinX * sinY + y * cosX - z * sinX * cosY;
                
                return {
                    x: centerX + x1,
                    y: centerY - y1
                };
            }
            
            // Sommets du cube (centré)
            var vertices = [
                {x: -w/2, y: -h/2, z: -d/2}, // 0: arrière bas gauche
                {x: w/2, y: -h/2, z: -d/2},  // 1: arrière bas droit
                {x: w/2, y: h/2, z: -d/2},   // 2: arrière haut droit
                {x: -w/2, y: h/2, z: -d/2},  // 3: arrière haut gauche
                {x: -w/2, y: -h/2, z: d/2},  // 4: avant bas gauche
                {x: w/2, y: -h/2, z: d/2},   // 5: avant bas droit
                {x: w/2, y: h/2, z: d/2},    // 6: avant haut droit
                {x: -w/2, y: h/2, z: d/2}    // 7: avant haut gauche
            ];
            
            // Projeter les sommets
            var projectedVertices = vertices.map(function(v) {
                return project(v.x, v.y, v.z);
            });
            
            // Faces du cube
            var faces = [
                {indices: [4, 5, 6, 7], color: '#F4A460'}, // Face avant (plus claire)
                {indices: [0, 1, 2, 3], color: '#CD853F'}, // Face arrière (plus sombre)
                {indices: [0, 1, 5, 4], color: '#D2691E'}, // Face bas
                {indices: [3, 2, 6, 7], color: '#DEB887'}, // Face haut (la plus claire)
                {indices: [0, 3, 7, 4], color: '#C19A6B'}, // Face gauche
                {indices: [1, 2, 6, 5], color: '#B8860B'}  // Face droite
            ];
            
            // Dessiner les faces
            faces.forEach(function(face) {
                ctx.beginPath();
                face.indices.forEach(function(idx, i) {
                    var p = projectedVertices[idx];
                    if (i === 0) {
                        ctx.moveTo(p.x, p.y);
                    } else {
                        ctx.lineTo(p.x, p.y);
                    }
                });
                ctx.closePath();
                ctx.fillStyle = face.color;
                ctx.fill();
                ctx.strokeStyle = '#8B4513';
                ctx.lineWidth = 2;
                ctx.stroke();
            });
            
            // Dessiner les arêtes rouges
            var edges = [
                [0, 1], [1, 2], [2, 3], [3, 0], // Face arrière
                [4, 5], [5, 6], [6, 7], [7, 4], // Face avant
                [0, 4], [1, 5], [2, 6], [3, 7]  // Arêtes de connexion
            ];
            
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
            
            // Ajouter les labels des dimensions
            ctx.font = 'bold 14px Arial';
            ctx.fillStyle = '#333';
            ctx.textAlign = 'center';
            
            // Label largeur
            var widthLabelPos = project(0, -h/2 - 30, d/2);
            ctx.fillText(boxData.width + ' cm (Largeur)', widthLabelPos.x, widthLabelPos.y);
            
            // Label profondeur
            var depthLabelPos = project(w/2 + 30, -h/2 - 20, 0);
            ctx.fillText(boxData.depth + ' cm (Profondeur)', depthLabelPos.x, depthLabelPos.y);
            
            // Label hauteur
            var heightLabelPos = project(-w/2 - 40, 0, -d/2 - 20);
            ctx.save();
            ctx.translate(heightLabelPos.x, heightLabelPos.y);
            ctx.rotate(-Math.PI / 2);
            ctx.fillText(boxData.height + ' cm (Hauteur)', 0, 0);
            ctx.restore();
        },

        _setupModalEvents: function () {
            var self = this;
            
            // Bouton prendre rendez-vous
            $('#btn-appointment').off('click').on('click', function () {
                self._showReservationForm('appointment');
            });
            
            // Bouton réserver maintenant
            $('#btn-reserve').off('click').on('click', function () {
                self._showReservationForm('reservation');
            });
            
            // Soumission du formulaire
            $('#submit-reservation').off('click').on('click', function () {
                self._submitReservation();
            });
            
            // Demande générale
            $('#general-inquiry-btn').off('click').on('click', function () {
                alert('Contactez-nous au +32 XXX XX XX XX ou par email à contact@lolirine.be');
            });
        },

        _showReservationForm: function (type) {
            var boxId = $('#selected-box-id').val();
            if (!boxId) return;
            
            $('#reservation-type').val(type);
            
            if (type === 'appointment') {
                $('#reservationFormModalTitle').text('Prendre rendez-vous');
                $('#appointment-date-group').show();
            } else {
                $('#reservationFormModalTitle').text('Réserver ce box maintenant');
                $('#appointment-date-group').hide();
            }
            
            // Réinitialiser le formulaire
            $('#reservation-form')[0].reset();
            $('#selected-box-id').val(boxId);
            
            // Fermer le modal de détails et ouvrir le formulaire
            $('#boxDetailsModal').modal('hide');
            setTimeout(function() {
                $('#reservationFormModal').modal('show');
            }, 500);
        },

        _submitReservation: function () {
            var self = this;
            var boxId = parseInt($('#selected-box-id').val());
            var type = $('#reservation-type').val();
            
            var formData = {
                box_id: boxId,
                customer_name: $('#customer-name').val(),
                customer_email: $('#customer-email').val(),
                customer_phone: $('#customer-phone').val(),
                notes: $('#customer-notes').val()
            };
            
            // Validation simple
            if (!formData.customer_name || !formData.customer_email || !formData.customer_phone) {
                alert('Veuillez remplir tous les champs obligatoires');
                return;
            }
            
            // Ajouter la date de rendez-vous si type appointment
            if (type === 'appointment') {
                var appointmentDate = $('#appointment-date').val();
                if (appointmentDate) {
                    formData.appointment_date = appointmentDate;
                }
            }
            
            // Désactiver le bouton pendant l'envoi
            var $btn = $('#submit-reservation');
            var originalText = $btn.text();
            $btn.prop('disabled', true).html('<span class="loading-spinner"></span> Envoi en cours...');
            
            // Envoyer la demande
            var route = type === 'appointment' ? '/storage/box/' + boxId + '/appointment' : '/storage/box/' + boxId + '/reserve';
            
            ajax.jsonRpc(route, 'call', formData)
                .then(function (result) {
                    if (result.error) {
                        alert('Erreur: ' + result.error);
                        $btn.prop('disabled', false).text(originalText);
                        return;
                    }
                    
                    if (result.success) {
                        alert('Merci! Votre demande a été enregistrée sous la référence ' + result.reservation_ref + 
                              '. Nous vous contacterons bientôt.');
                        $('#reservationFormModal').modal('hide');
                        
                        // Recharger la page pour mettre à jour les statuts
                        setTimeout(function() {
                            window.location.reload();
                        }, 2000);
                    }
                })
                .catch(function (error) {
                    console.error('Erreur lors de la réservation:', error);
                    alert('Une erreur est survenue. Veuillez réessayer.');
                    $btn.prop('disabled', false).text(originalText);
                });
        }
    });

    return publicWidget.registry.StoragePlan;
});
