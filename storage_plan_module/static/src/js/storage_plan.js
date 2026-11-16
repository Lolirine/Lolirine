/**
 * Plan Interactif Garde-Meubles - JavaScript
 * Version 1.0.21 - Simplifiée et corrigée
 */
(function() {
    'use strict';

    $(document).ready(function() {
        console.log('Storage Plan JS loaded v1.0.66');
        initializeStoragePlan();
    });

    function initializeStoragePlan() {
        
        // ============================================
        // SYNCHRONISATION DES BOUTONS MODAL
        // ============================================
        function syncModalButtons() {
            var configAppointment = $('#config-btn-appointment');
            var configReserve = $('#config-btn-reserve');
            var modalAppointment = $('#btn-appointment');
            var modalReserve = $('#btn-reserve');
            
            if (configAppointment.length && modalAppointment.length) {
                var href = configAppointment.attr('href');
                var text = configAppointment.text().trim();
                modalAppointment.attr('href', href);
                if (text) modalAppointment.text(text);
            }
            
            if (configReserve.length && modalReserve.length) {
                var href = configReserve.attr('href');
                var text = configReserve.text().trim();
                modalReserve.attr('href', href);
                if (text) modalReserve.text(text);
            }
        }
        
        // Synchroniser au chargement
        syncModalButtons();
        
        // Observer les changements (mode édition)
        var configSection = document.querySelector('.modal-buttons-config-section');
        if (configSection) {
            var observer = new MutationObserver(function(mutations) {
                syncModalButtons();
            });
            observer.observe(configSection, { 
                childList: true, 
                subtree: true, 
                attributes: true,
                attributeFilter: ['href']
            });
        }
        
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
        $(document).on('click', '.storage-box, .plan-box', function(e) {
            e.preventDefault();
            e.stopPropagation();
            
            // Ne pas ouvrir en mode édition
            if (isEditMode()) {
                console.log('Edit mode, ignoring click');
                return false;
            }
            
            var boxId = parseInt(this.getAttribute('data-box-id'), 10);
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
            $('#detail-box-name').html('<strong>' + $('<span>').text(boxData.name).html() + '</strong>');
            $('#detail-floor').text(boxData.floor);
            $('#detail-surface').text(boxData.surface + ' m²');
            $('#detail-width').text(boxData.width + ' cm');
            $('#detail-depth').text(boxData.depth + ' cm');
            $('#detail-height').text(boxData.height + ' cm');
            $('#detail-volume').html('<strong>' + boxData.volume + ' m³</strong>');
            $('#detail-price').html('<strong>' + boxData.price_monthly + ' €/Mois</strong>');
            $('#detail-registration-fee').text(boxData.registration_fee + ' €');
            $('#detail-deposit').text(boxData.deposit_months + ' mois de loyer');
            
            // Badge du statut avec couleur dynamique (même couleur que le box)
            var $statusBadge = $('#detail-status');
            $statusBadge.text(boxData.status_label);
            $statusBadge.removeClass('badge-success badge-danger badge-warning badge-info');
            
            // Réinitialiser les styles inline
            $statusBadge.removeAttr('style');
            
            // Appliquer la couleur de statut directement (même couleur que le box)
            var statusColor = boxData.status_color || '#888';
            $statusBadge.css({
                'background-color': statusColor,
                'color': '#fff',
                'font-size': '18px',
                'padding': '10px 20px',
                'font-weight': 'bold',
                'text-shadow': '1px 1px 2px rgba(0,0,0,0.3)',
                'border-radius': '6px',
                'display': 'inline-block'
            });
            
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
        // DESSIN 3D DU BOX (panneaux OSB)
        //  - vue extérieure : box fermé, porte et numéro
        //  - clic : vue intérieure avec les dimensions utiles
        // ============================================
        var box3dState = { data: null, view: 'ext' };

        $(document).on('click', '#box-3d-canvas', function(e) {
            e.preventDefault();
            e.stopPropagation();
            if (!box3dState.data) { return; }
            box3dState.view = box3dState.view === 'ext' ? 'int' : 'ext';
            render3DBox();
        });

        function draw3DBox(boxData) {
            box3dState.data = boxData;
            box3dState.view = 'ext';
            render3DBox();
        }

        function render3DBox() {
            var canvas = document.getElementById('box-3d-canvas');
            var boxData = box3dState.data;
            if (!canvas || !boxData) return;

            // Netteté sur écrans haute densité
            var SIZE = 400;
            var dpr = Math.min(window.devicePixelRatio || 1, 3);
            if (canvas.width !== SIZE * dpr) {
                canvas.width = SIZE * dpr;
                canvas.height = SIZE * dpr;
            }
            canvas.style.cursor = 'pointer';
            canvas.title = box3dState.view === 'ext'
                ? "Cliquez pour voir l'intérieur et ses dimensions"
                : "Cliquez pour revenir à la vue extérieure";
            var ctx = canvas.getContext('2d');
            ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
            ctx.clearRect(0, 0, SIZE, SIZE);

            var W = Number(boxData.width) || 200;    // largeur (façade)
            var D = Number(boxData.depth) || 250;    // profondeur
            var H = Number(boxData.height) || 250;   // hauteur
            var interior = box3dState.view === 'int';

            // ---- Projection isométrique : x = largeur, z = profondeur, y = hauteur ----
            var C = Math.cos(Math.PI / 6), S = 0.5;
            var margeH = 62, margeHaut = 46, margeBas = 70;
            var scale = Math.min(
                (SIZE - 2 * margeH) / ((W + D) * C),
                (SIZE - margeHaut - margeBas) / (H + (W + D) * S)
            );
            var largeurEcran = (W + D) * C * scale;
            var ox = (SIZE - largeurEcran) / 2 + D * C * scale;
            var oy = margeHaut + H * scale;
            function P(x, y, z) {
                return { x: ox + (x - z) * C * scale, y: oy + (x + z) * S * scale - y * scale };
            }
            function poly(pts) {
                ctx.beginPath();
                pts.forEach(function(p, i) { if (i) { ctx.lineTo(p.x, p.y); } else { ctx.moveTo(p.x, p.y); } });
                ctx.closePath();
            }

            // ---- Texture OSB : copeaux orientés, tirage reproductible ----
            function rng(seed) {
                var t = seed >>> 0;
                return function() {
                    t += 0x6D2B79F5;
                    var r = Math.imul(t ^ (t >>> 15), 1 | t);
                    r ^= r + Math.imul(r ^ (r >>> 7), 61 | r);
                    return ((r ^ (r >>> 14)) >>> 0) / 4294967296;
                };
            }
            function osb(pts, base, seed) {
                var rand = rng(seed);
                var xs = pts.map(function(p) { return p.x; }), ys = pts.map(function(p) { return p.y; });
                var x0 = Math.min.apply(null, xs), x1 = Math.max.apply(null, xs);
                var y0 = Math.min.apply(null, ys), y1 = Math.max.apply(null, ys);
                ctx.save();
                poly(pts);
                ctx.fillStyle = 'rgb(' + base.join(',') + ')';
                ctx.fill();
                ctx.clip();
                var n = Math.round((x1 - x0) * (y1 - y0) / 16);
                for (var i = 0; i < n; i++) {
                    var v = (rand() - 0.5) * 70;
                    ctx.fillStyle = 'rgba(' + Math.round(Math.max(0, Math.min(255, base[0] + v))) + ','
                        + Math.round(Math.max(0, Math.min(255, base[1] + v * 0.9))) + ','
                        + Math.round(Math.max(0, Math.min(255, base[2] + v * 0.6))) + ',0.75)';
                    ctx.save();
                    ctx.translate(x0 + rand() * (x1 - x0), y0 + rand() * (y1 - y0));
                    ctx.rotate(rand() * Math.PI);
                    ctx.fillRect(-5 - rand() * 7, -1.2 - rand() * 1.6, 10 + rand() * 14, 2.4 + rand() * 3.2);
                    ctx.restore();
                }
                ctx.restore();
                poly(pts);
                ctx.strokeStyle = '#5b4426';
                ctx.lineWidth = 1.4;
                ctx.lineJoin = 'round';
                ctx.stroke();
            }
            function trait(a, b, couleur, epaisseur) {
                ctx.beginPath();
                ctx.moveTo(a.x, a.y);
                ctx.lineTo(b.x, b.y);
                ctx.strokeStyle = couleur;
                ctx.lineWidth = epaisseur;
                ctx.stroke();
            }
            // Joints entre panneaux (un panneau OSB = 125 cm de large)
            function joints(longueur, pointBas, pointHaut) {
                for (var m = 125; m < longueur - 15; m += 125) {
                    trait(pointBas(m), pointHaut(m), 'rgba(70,50,25,0.55)', 1);
                }
            }
            function etiquette(texte, p, angle, couleur) {
                ctx.save();
                ctx.translate(p.x, p.y);
                ctx.rotate(angle);
                ctx.font = 'bold 13px Arial, sans-serif';
                ctx.textAlign = 'center';
                ctx.textBaseline = 'middle';
                var l = ctx.measureText(texte).width + 10;
                ctx.fillStyle = 'rgba(255,255,255,0.92)';
                ctx.fillRect(-l / 2, -10, l, 20);
                ctx.fillStyle = couleur || '#1f2d3d';
                ctx.fillText(texte, 0, 1);
                ctx.restore();
            }
            // Cote : trait décalé, deux butées, valeur au milieu
            function cote(a, b, texte, decalX, decalY) {
                var p1 = { x: a.x + decalX, y: a.y + decalY }, p2 = { x: b.x + decalX, y: b.y + decalY };
                trait(a, p1, 'rgba(192,57,43,0.45)', 1);
                trait(b, p2, 'rgba(192,57,43,0.45)', 1);
                trait(p1, p2, '#c0392b', 1.6);
                [p1, p2].forEach(function(p) {
                    ctx.beginPath();
                    ctx.arc(p.x, p.y, 2.6, 0, Math.PI * 2);
                    ctx.fillStyle = '#c0392b';
                    ctx.fill();
                });
                var angle = Math.atan2(p2.y - p1.y, p2.x - p1.x);
                if (angle > Math.PI / 2 || angle < -Math.PI / 2) { angle += Math.PI; }
                etiquette(texte, { x: (p1.x + p2.x) / 2, y: (p1.y + p2.y) / 2 }, angle, '#c0392b');
            }
            function cm(v) { return (Math.round(v * 10) / 10).toString().replace('.', ',') + ' cm'; }

            // Ombre au sol
            poly([P(0, 0, D), P(W, 0, D), P(W, 0, 0), P(W + 22, 0, -8), P(W + 22, 0, D + 22), P(-8, 0, D + 22)]);
            ctx.fillStyle = 'rgba(0,0,0,0.07)';
            ctx.fill();

            var titre;
            if (!interior) {
                // ================= VUE EXTÉRIEURE =================
                var facade = [P(0, 0, D), P(W, 0, D), P(W, H, D), P(0, H, D)];
                var cote_d = [P(W, 0, D), P(W, 0, 0), P(W, H, 0), P(W, H, D)];
                var dessus = [P(0, H, 0), P(W, H, 0), P(W, H, D), P(0, H, D)];
                osb(dessus, [226, 190, 132], 11);
                osb(cote_d, [176, 136, 84], 23);
                osb(facade, [205, 165, 106], 37);
                joints(D, function(m) { return P(W, 0, D - m); }, function(m) { return P(W, H, D - m); });

                // Porte en façade
                var lp = Math.min(100, W - 30), hp = Math.min(205, H - 12);
                var xp = (W - lp) / 2;
                var porte = [P(xp, 0, D), P(xp + lp, 0, D), P(xp + lp, hp, D), P(xp, hp, D)];
                osb(porte, [214, 176, 118], 53);
                poly(porte);
                ctx.strokeStyle = '#3e2c17';
                ctx.lineWidth = 2.2;
                ctx.stroke();
                // charnières (à gauche)
                [0.18, 0.82].forEach(function(r) {
                    poly([P(xp - 3, hp * r - 7, D), P(xp + 9, hp * r - 7, D), P(xp + 9, hp * r + 7, D), P(xp - 3, hp * r + 7, D)]);
                    ctx.fillStyle = '#4a4f55';
                    ctx.fill();
                });
                // verrou et cadenas (à droite)
                poly([P(xp + lp - 20, hp * 0.5 - 4, D), P(xp + lp + 6, hp * 0.5 - 4, D), P(xp + lp + 6, hp * 0.5 + 4, D), P(xp + lp - 20, hp * 0.5 + 4, D)]);
                ctx.fillStyle = '#5c6268';
                ctx.fill();
                var cad = P(xp + lp - 8, hp * 0.5 - 8, D);
                ctx.beginPath();
                ctx.arc(cad.x, cad.y, 4 * scale + 1, Math.PI, 0);
                ctx.strokeStyle = '#8a6d1a';
                ctx.lineWidth = 2;
                ctx.stroke();
                poly([P(xp + lp - 13, hp * 0.5 - 20, D), P(xp + lp - 3, hp * 0.5 - 20, D), P(xp + lp - 3, hp * 0.5 - 8, D), P(xp + lp - 13, hp * 0.5 - 8, D)]);
                ctx.fillStyle = '#d4a017';
                ctx.fill();
                // plaque du numéro, posée dans le plan de la façade
                var nom = String(boxData.name || '');
                if (nom) {
                    var c0 = P(xp + lp / 2, hp * 0.78, D);
                    ctx.save();
                    ctx.translate(c0.x, c0.y);
                    ctx.transform(1, S / C, 0, 1, 0, 0);
                    ctx.font = 'bold ' + Math.max(11, Math.round(30 * scale)) + 'px Arial, sans-serif';
                    ctx.textAlign = 'center';
                    ctx.textBaseline = 'middle';
                    var ln = ctx.measureText(nom).width + 12;
                    var hn = Math.max(16, Math.round(40 * scale));
                    ctx.fillStyle = '#ffffff';
                    ctx.fillRect(-ln / 2, -hn / 2, ln, hn);
                    ctx.strokeStyle = '#1f2d3d';
                    ctx.lineWidth = 1.2;
                    ctx.strokeRect(-ln / 2, -hn / 2, ln, hn);
                    ctx.fillStyle = '#1f2d3d';
                    ctx.fillText(nom, 0, 1);
                    ctx.restore();
                }
                titre = 'Vue extérieure';
            } else {
                // ================= VUE INTÉRIEURE (façade, côté droit et dessus retirés) =================
                var sol = [P(0, 0, 0), P(W, 0, 0), P(W, 0, D), P(0, 0, D)];
                var mur_g = [P(0, 0, 0), P(0, 0, D), P(0, H, D), P(0, H, 0)];
                var mur_f = [P(0, 0, 0), P(W, 0, 0), P(W, H, 0), P(0, H, 0)];
                osb(mur_g, [198, 158, 100], 61);
                osb(mur_f, [220, 183, 124], 71);
                osb(sol, [188, 150, 96], 83);
                joints(D, function(m) { return P(0, 0, m); }, function(m) { return P(0, H, m); });
                joints(W, function(m) { return P(m, 0, 0); }, function(m) { return P(m, H, 0); });
                // tranche des panneaux coupés
                trait(P(0, 0, D), P(0, H, D), '#3e2c17', 3);
                trait(P(W, 0, 0), P(W, H, 0), '#3e2c17', 3);
                trait(P(0, H, D), P(0, H, 0), '#3e2c17', 2);
                trait(P(0, H, 0), P(W, H, 0), '#3e2c17', 2);

                // Silhouette de 1,75 m pour l'échelle
                if (H >= 180 && W >= 90 && D >= 90) {
                    var pied = P(W * 0.28, 0, D * 0.42), tete = P(W * 0.28, 175, D * 0.42);
                    var ht = pied.y - tete.y, lg = ht * 0.2;
                    ctx.fillStyle = 'rgba(52,73,94,0.5)';
                    ctx.beginPath();
                    ctx.arc(tete.x, tete.y + ht * 0.07, ht * 0.07, 0, Math.PI * 2);
                    ctx.fill();
                    ctx.beginPath();
                    ctx.moveTo(tete.x - lg / 2, tete.y + ht * 0.2);
                    ctx.quadraticCurveTo(tete.x, tete.y + ht * 0.13, tete.x + lg / 2, tete.y + ht * 0.2);
                    ctx.lineTo(tete.x + lg * 0.36, pied.y);
                    ctx.lineTo(tete.x - lg * 0.36, pied.y);
                    ctx.closePath();
                    ctx.fill();
                    ctx.font = '11px Arial, sans-serif';
                    ctx.textAlign = 'left';
                    ctx.textBaseline = 'middle';
                    ctx.fillStyle = 'rgba(31,45,61,0.85)';
                    ctx.fillText('1,75 m', tete.x + lg * 0.7, tete.y + ht * 0.45);
                }

                // Cotes intérieures
                cote(P(0, 0, D), P(W, 0, D), cm(W), -12, 20);          // largeur
                cote(P(W, 0, D), P(W, 0, 0), cm(D), 12, 20);           // profondeur
                cote(P(W, 0, 0), P(W, H, 0), cm(H), 24, 0);            // hauteur
                titre = 'Dimensions intérieures';
            }

            // Bandeau du haut et invite du bas
            ctx.font = 'bold 15px Arial, sans-serif';
            ctx.textAlign = 'center';
            ctx.textBaseline = 'middle';
            ctx.fillStyle = '#1f2d3d';
            ctx.fillText(titre, SIZE / 2, 18);
            var invite = interior ? '↺  Cliquez pour revenir à la vue extérieure'
                                  : "🔍  Cliquez sur le box pour voir l'intérieur";
            ctx.font = '13px Arial, sans-serif';
            var li = ctx.measureText(invite).width + 26;
            ctx.fillStyle = 'rgba(31,45,61,0.88)';
            ctx.beginPath();
            if (ctx.roundRect) { ctx.roundRect((SIZE - li) / 2, SIZE - 32, li, 24, 12); } else { ctx.rect((SIZE - li) / 2, SIZE - 32, li, 24); }
            ctx.fill();
            ctx.fillStyle = '#ffffff';
            ctx.fillText(invite, SIZE / 2, SIZE - 19);
        }
    }
})();
