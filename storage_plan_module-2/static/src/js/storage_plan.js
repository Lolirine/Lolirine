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
        // Événement clic sur les boxes disponibles
        $(document).on('click', '.storage-box[data-status="disponible"]', function(e) {
            e.preventDefault();
            var boxId = parseInt($(this).data('box-id'));
            console.log('Box clicked:', boxId);
            
            if (boxId) {
                loadBoxDetails(boxId);
            }
        });

        // Bouton prendre rendez-vous
        $(document).on('click', '#btn-appointment', function() {
            showReservationForm('appointment');
        });

        // Bouton réserver maintenant
        $(document).on('click', '#btn-reserve', function() {
            showReservationForm('reservation');
        });

        // Bouton soumettre réservation
        $(document).on('click', '#submit-reservation', function() {
            submitReservation();
        });

        // Demande générale
        $(document).on('click', '#general-inquiry-btn', function() {
            alert('Contactez-nous au +32 50 XX XX XX ou par email à contact@lolirine.be');
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
        
        // Stocker l'ID du box
        $('#selected-box-id').val(boxData.id);
        
        // Activer/désactiver les boutons
        var isAvailable = boxData.status === 'disponible';
        $('#btn-appointment').prop('disabled', !isAvailable);
        $('#btn-reserve').prop('disabled', !isAvailable);
        
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

    function showReservationForm(type) {
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
        
        $('#reservation-form')[0].reset();
        $('#selected-box-id').val(boxId);
        
        $('#boxDetailsModal').modal('hide');
        setTimeout(function() {
            $('#reservationFormModal').modal('show');
        }, 500);
    }

    function submitReservation() {
        var boxId = parseInt($('#selected-box-id').val());
        var type = $('#reservation-type').val();
        
        var formData = {
            box_id: boxId,
            customer_name: $('#customer-name').val(),
            customer_email: $('#customer-email').val(),
            customer_phone: $('#customer-phone').val(),
            notes: $('#customer-notes').val()
        };
        
        if (!formData.customer_name || !formData.customer_email || !formData.customer_phone) {
            alert('Veuillez remplir tous les champs obligatoires');
            return;
        }
        
        if (type === 'appointment') {
            var appointmentDate = $('#appointment-date').val();
            if (appointmentDate) {
                formData.appointment_date = appointmentDate;
            }
        }
        
        var $btn = $('#submit-reservation');
        var originalText = $btn.text();
        $btn.prop('disabled', true).html('<span class="spinner-border spinner-border-sm"></span> Envoi en cours...');
        
        var route = type === 'appointment' ? '/storage/box/' + boxId + '/appointment' : '/storage/box/' + boxId + '/reserve';
        
        $.ajax({
            url: route,
            type: 'POST',
            contentType: 'application/json',
            data: JSON.stringify({
                jsonrpc: '2.0',
                method: 'call',
                params: formData
            }),
            success: function(response) {
                if (response.error) {
                    alert('Erreur: ' + response.error.data.message);
                    $btn.prop('disabled', false).text(originalText);
                    return;
                }
                
                var result = response.result;
                if (result.error) {
                    alert('Erreur: ' + result.error);
                    $btn.prop('disabled', false).text(originalText);
                    return;
                }
                
                if (result.success) {
                    alert('Merci! Votre demande a été enregistrée sous la référence ' + result.reservation_ref + 
                          '. Nous vous contacterons bientôt.');
                    $('#reservationFormModal').modal('hide');
                    setTimeout(function() {
                        window.location.reload();
                    }, 2000);
                }
            },
            error: function(xhr, status, error) {
                console.error('Erreur lors de la réservation:', error);
                alert('Une erreur est survenue. Veuillez réessayer.');
                $btn.prop('disabled', false).text(originalText);
            }
        });
    }

})();
