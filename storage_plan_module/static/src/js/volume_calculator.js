/**
 * Calculateur de Volume avec Visualisation 3D
 * Plan Interactif Garde-Meubles v1.0.66
 */

(function() {
    'use strict';
    
    var selectedItems = {};
    var totalVolume = 0;
    var scene, camera, renderer;
    var furnitureObjects = [];
    var calculator = null;
    var initialized = false;
    
    // Fonction d'initialisation principale
    function initVolumeCalculator() {
        calculator = document.querySelector('.volume-calculator-section');
        if (!calculator || initialized) return;
        
        console.log('Volume Calculator initializing v1.0.66');
        initialized = true;
        
        // Initialiser les événements
        initEvents();
        
        // Initialiser Three.js
        initThreeJS();
        
        console.log('Volume Calculator ready!');
    }
    
    function initEvents() {
        // Délégation d'événements pour les onglets
        calculator.addEventListener('click', function(e) {
            var target = e.target;
            
            // Vérifier si c'est un onglet ou un enfant d'onglet
            var tab = target.closest('.category-tab');
            if (tab) {
                e.preventDefault();
                e.stopPropagation();
                handleTabClick(tab);
                return;
            }
            
            // Vérifier si c'est un bouton moins
            if (target.classList.contains('furniture-btn-minus')) {
                e.preventDefault();
                e.stopPropagation();
                handleMinusClick(target);
                return;
            }
            
            // Vérifier si c'est un bouton plus
            if (target.classList.contains('furniture-btn-plus')) {
                e.preventDefault();
                e.stopPropagation();
                handlePlusClick(target);
                return;
            }
            
            // Bouton reset
            if (target.classList.contains('btn-reset-calculator') || target.closest('.btn-reset-calculator')) {
                e.preventDefault();
                e.stopPropagation();
                handleReset();
                return;
            }
            
            // Bouton voir boxes
            if (target.classList.contains('btn-view-boxes') || target.closest('.btn-view-boxes')) {
                e.preventDefault();
                e.stopPropagation();
                handleViewBoxes();
                return;
            }
        });
        
        console.log('Events initialized');
    }
    
    function handleTabClick(tab) {
        var categoryId = tab.getAttribute('data-category-id');
        console.log('Tab clicked:', categoryId);
        
        // Mettre à jour les onglets actifs
        var tabs = calculator.querySelectorAll('.category-tab');
        tabs.forEach(function(t) { 
            t.classList.remove('active'); 
        });
        tab.classList.add('active');
        
        // Afficher le bon panneau
        var panels = calculator.querySelectorAll('.furniture-category-panel');
        panels.forEach(function(p) { 
            p.classList.remove('active'); 
        });
        
        var activePanel = calculator.querySelector('.furniture-category-panel[data-category-id="' + categoryId + '"]');
        if (activePanel) {
            activePanel.classList.add('active');
            console.log('Panel activated:', categoryId);
        }
    }
    
    function handleMinusClick(btn) {
        var furnitureId = btn.getAttribute('data-furniture-id');
        console.log('Minus clicked:', furnitureId);
        
        var currentQty = selectedItems[furnitureId] || 0;
        if (currentQty > 0) {
            selectedItems[furnitureId] = currentQty - 1;
            updateDisplay();
            update3DVisualization();
        }
    }
    
    function handlePlusClick(btn) {
        var furnitureId = btn.getAttribute('data-furniture-id');
        console.log('Plus clicked:', furnitureId);
        
        var currentQty = selectedItems[furnitureId] || 0;
        selectedItems[furnitureId] = currentQty + 1;
        updateDisplay();
        update3DVisualization();
    }
    
    function handleReset() {
        console.log('Reset clicked');
        selectedItems = {};
        updateDisplay();
        update3DVisualization();
    }
    
    function handleViewBoxes() {
        console.log('View boxes clicked');
        var plan = document.querySelector('.storage-plan-container');
        if (plan) {
            plan.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
    }
    
    function updateDisplay() {
        var total = 0;
        
        var items = calculator.querySelectorAll('.furniture-item');
        items.forEach(function(item) {
            var furnitureId = item.getAttribute('data-furniture-id');
            var volume = parseFloat(item.getAttribute('data-volume')) || 0;
            var qty = selectedItems[furnitureId] || 0;
            
            var qtyDisplay = item.querySelector('.furniture-qty');
            if (qtyDisplay) {
                qtyDisplay.textContent = qty;
            }
            
            if (qty > 0) {
                item.classList.add('has-items');
            } else {
                item.classList.remove('has-items');
            }
            
            total += volume * qty;
        });
        
        totalVolume = total;
        
        var volumeDisplay = calculator.querySelector('.total-volume-value');
        if (volumeDisplay) {
            volumeDisplay.textContent = total.toFixed(2);
        }
        
        console.log('Total volume:', total);
        updateRecommendation();
    }
    
    function updateRecommendation() {
        var recommendationContent = calculator.querySelector('.recommendation-content');
        var recommendedBoxes = calculator.querySelector('.recommended-boxes');
        
        if (!recommendationContent) return;
        
        if (totalVolume <= 0) {
            recommendationContent.innerHTML = '<p class="text-muted">Ajoutez des objets pour obtenir une suggestion.</p>';
            if (recommendedBoxes) recommendedBoxes.innerHTML = '';
            return;
        }
        
        // Trouver les boxes adaptés (avec 20% de marge)
        var requiredVolume = totalVolume * 1.2;
        var suitableBoxes = [];
        
        var boxItems = calculator.querySelectorAll('.box-volume-item');
        boxItems.forEach(function(boxItem) {
            var boxVolume = parseFloat(boxItem.getAttribute('data-volume'));
            var boxName = boxItem.getAttribute('data-name');
            var boxSurface = parseFloat(boxItem.getAttribute('data-surface'));
            var boxPrice = parseFloat(boxItem.getAttribute('data-price'));
            var boxId = boxItem.getAttribute('data-id');
            
            if (boxVolume >= requiredVolume) {
                suitableBoxes.push({
                    id: boxId,
                    name: boxName,
                    volume: boxVolume,
                    surface: boxSurface,
                    price: boxPrice,
                    margin: ((boxVolume - requiredVolume) / requiredVolume * 100).toFixed(0)
                });
            }
        });
        
        // Trier par volume (plus petit d'abord)
        suitableBoxes.sort(function(a, b) { return a.volume - b.volume; });
        
        if (suitableBoxes.length === 0) {
            recommendationContent.innerHTML = 
                '<p class="text-warning"><i class="fa fa-exclamation-triangle"></i> ' +
                'Votre volume estimé (' + totalVolume.toFixed(2) + ' m³) dépasse nos boxes disponibles. ' +
                'Contactez-nous pour une solution personnalisée.</p>';
            if (recommendedBoxes) recommendedBoxes.innerHTML = '';
        } else {
            var bestBox = suitableBoxes[0];
            recommendationContent.innerHTML = 
                '<div class="best-recommendation">' +
                '<h5><i class="fa fa-star text-warning"></i> Box recommandé</h5>' +
                '<div class="recommended-box-card">' +
                '<div class="box-name">' + bestBox.name + '</div>' +
                '<div class="box-details">' +
                '<span class="box-vol">' + bestBox.volume.toFixed(1) + ' m³</span> · ' +
                '<span class="box-surface">' + bestBox.surface.toFixed(1) + ' m²</span>' +
                '</div>' +
                '<div class="box-price">' + bestBox.price.toFixed(0) + ' €/mois</div>' +
                '<div class="box-margin text-success">+' + bestBox.margin + '% de marge</div>' +
                '</div>' +
                '</div>';
            
            // Autres options
            if (suitableBoxes.length > 1 && recommendedBoxes) {
                var otherHtml = '<div class="other-boxes mt-3"><h6>Autres options :</h6><div class="other-boxes-list">';
                for (var i = 1; i < Math.min(suitableBoxes.length, 4); i++) {
                    var box = suitableBoxes[i];
                    otherHtml += '<div class="other-box-item">' +
                        '<span class="name">' + box.name + '</span> - ' +
                        '<span class="vol">' + box.volume.toFixed(1) + ' m³</span> - ' +
                        '<span class="price">' + box.price.toFixed(0) + ' €/mois</span>' +
                        '</div>';
                }
                otherHtml += '</div></div>';
                recommendedBoxes.innerHTML = otherHtml;
            } else if (recommendedBoxes) {
                recommendedBoxes.innerHTML = '';
            }
            
            // Mettre à jour le wireframe 3D
            if (scene) {
                var side = Math.pow(bestBox.volume, 1/3);
                createBoxWireframe(side * 1.2, side, side * 1.2);
            }
        }
    }
    
    function initThreeJS() {
        var canvas = document.getElementById('volume-3d-canvas');
        if (!canvas) {
            console.log('Canvas not found');
            return;
        }
        
        if (typeof THREE === 'undefined') {
            console.log('Three.js not loaded yet, retrying in 500ms');
            setTimeout(initThreeJS, 500);
            return;
        }
        
        console.log('Initializing Three.js');
        
        var container = canvas.parentElement;
        var width = container.clientWidth || 350;
        var height = 350;
        
        // Scene
        scene = new THREE.Scene();
        scene.background = new THREE.Color(0xf5f5f5);
        
        // Camera
        camera = new THREE.PerspectiveCamera(45, width / height, 0.1, 1000);
        camera.position.set(5, 4, 5);
        camera.lookAt(0, 0, 0);
        
        // Renderer
        renderer = new THREE.WebGLRenderer({ canvas: canvas, antialias: true });
        renderer.setSize(width, height);
        renderer.shadowMap.enabled = true;
        
        // Lights
        var ambientLight = new THREE.AmbientLight(0xffffff, 0.6);
        scene.add(ambientLight);
        
        var directionalLight = new THREE.DirectionalLight(0xffffff, 0.8);
        directionalLight.position.set(5, 10, 5);
        directionalLight.castShadow = true;
        scene.add(directionalLight);
        
        // Ground
        var groundGeometry = new THREE.PlaneGeometry(6, 6);
        var groundMaterial = new THREE.MeshStandardMaterial({ color: 0xe0e0e0, roughness: 0.8 });
        var ground = new THREE.Mesh(groundGeometry, groundMaterial);
        ground.rotation.x = -Math.PI / 2;
        ground.receiveShadow = true;
        scene.add(ground);
        
        // Grid
        var gridHelper = new THREE.GridHelper(6, 12, 0xcccccc, 0xeeeeee);
        scene.add(gridHelper);
        
        // Box wireframe
        createBoxWireframe(3, 2.5, 3);
        
        // Simple mouse controls
        var isDragging = false;
        var previousMousePosition = { x: 0, y: 0 };
        var spherical = { theta: Math.PI / 4, phi: Math.PI / 4, radius: 8 };
        
        canvas.addEventListener('mousedown', function(e) {
            isDragging = true;
            previousMousePosition = { x: e.clientX, y: e.clientY };
        });
        
        canvas.addEventListener('mousemove', function(e) {
            if (!isDragging) return;
            
            var deltaX = e.clientX - previousMousePosition.x;
            var deltaY = e.clientY - previousMousePosition.y;
            
            spherical.theta -= deltaX * 0.01;
            spherical.phi -= deltaY * 0.01;
            spherical.phi = Math.max(0.1, Math.min(Math.PI - 0.1, spherical.phi));
            
            updateCameraPosition();
            previousMousePosition = { x: e.clientX, y: e.clientY };
        });
        
        canvas.addEventListener('mouseup', function() {
            isDragging = false;
        });
        
        canvas.addEventListener('mouseleave', function() {
            isDragging = false;
        });
        
        canvas.addEventListener('wheel', function(e) {
            e.preventDefault();
            spherical.radius += e.deltaY * 0.01;
            spherical.radius = Math.max(3, Math.min(15, spherical.radius));
            updateCameraPosition();
        });
        
        function updateCameraPosition() {
            camera.position.x = spherical.radius * Math.sin(spherical.phi) * Math.cos(spherical.theta);
            camera.position.y = spherical.radius * Math.cos(spherical.phi);
            camera.position.z = spherical.radius * Math.sin(spherical.phi) * Math.sin(spherical.theta);
            camera.lookAt(0, 0, 0);
        }
        
        updateCameraPosition();
        
        // Animation loop
        function animate() {
            requestAnimationFrame(animate);
            if (renderer && scene && camera) {
                renderer.render(scene, camera);
            }
        }
        animate();
        
        console.log('Three.js initialized');
    }
    
    function createBoxWireframe(width, height, depth) {
        if (!scene) return;
        
        var existing = scene.getObjectByName('boxWireframe');
        if (existing) scene.remove(existing);
        
        var geometry = new THREE.BoxGeometry(width, height, depth);
        var edges = new THREE.EdgesGeometry(geometry);
        var material = new THREE.LineBasicMaterial({ color: 0x1565C0 });
        var wireframe = new THREE.LineSegments(edges, material);
        wireframe.name = 'boxWireframe';
        wireframe.position.y = height / 2;
        scene.add(wireframe);
    }
    
    function update3DVisualization() {
        if (!scene) return;
        
        // Supprimer les anciens objets
        furnitureObjects.forEach(function(obj) {
            scene.remove(obj);
        });
        furnitureObjects = [];
        
        // Collecter les objets à placer
        var itemsToPack = [];
        var items = calculator.querySelectorAll('.furniture-item');
        items.forEach(function(item) {
            var furnitureId = item.getAttribute('data-furniture-id');
            var qty = selectedItems[furnitureId] || 0;
            
            if (qty > 0) {
                var width = parseFloat(item.getAttribute('data-width')) / 100;
                var depth = parseFloat(item.getAttribute('data-depth')) / 100;
                var height = parseFloat(item.getAttribute('data-height')) / 100;
                var color = item.getAttribute('data-color') || '#3498db';
                var name = item.getAttribute('data-name');
                
                for (var i = 0; i < qty; i++) {
                    itemsToPack.push({
                        width: width,
                        depth: depth,
                        height: height,
                        color: color,
                        name: name
                    });
                }
            }
        });
        
        if (itemsToPack.length === 0) return;
        
        // Trier par volume (plus grand d'abord)
        itemsToPack.sort(function(a, b) {
            return (b.width * b.depth * b.height) - (a.width * a.depth * a.height);
        });
        
        // Algorithme de bin packing simple
        var packedItems = packItems3D(itemsToPack);
        
        // Créer les objets 3D
        packedItems.forEach(function(item) {
            var geometry = new THREE.BoxGeometry(item.width * 0.95, item.height * 0.95, item.depth * 0.95);
            var material = new THREE.MeshStandardMaterial({ 
                color: item.color,
                roughness: 0.7,
                metalness: 0.1
            });
            var mesh = new THREE.Mesh(geometry, material);
            mesh.position.set(
                item.x + item.width / 2 - 1.5,
                item.y + item.height / 2,
                item.z + item.depth / 2 - 1.5
            );
            mesh.castShadow = true;
            mesh.receiveShadow = true;
            
            // Ajouter les arêtes
            var edges = new THREE.EdgesGeometry(geometry);
            var lineMaterial = new THREE.LineBasicMaterial({ color: 0x000000 });
            var wireframe = new THREE.LineSegments(edges, lineMaterial);
            mesh.add(wireframe);
            
            scene.add(mesh);
            furnitureObjects.push(mesh);
        });
    }
    
    function packItems3D(items) {
        var packedItems = [];
        var boxWidth = 3;
        var boxDepth = 3;
        var boxHeight = 2.5;
        
        var currentX = 0;
        var currentY = 0;
        var currentZ = 0;
        var rowHeight = 0;
        var layerDepth = 0;
        
        items.forEach(function(item) {
            if (currentX + item.width > boxWidth) {
                currentX = 0;
                currentZ += layerDepth;
                layerDepth = 0;
            }
            
            if (currentZ + item.depth > boxDepth) {
                currentZ = 0;
                currentY += rowHeight;
                rowHeight = 0;
                layerDepth = 0;
            }
            
            if (currentY + item.height > boxHeight) {
                currentX = 0;
                currentY = 0;
                currentZ = 0;
            }
            
            packedItems.push({
                name: item.name,
                width: item.width,
                depth: item.depth,
                height: item.height,
                color: item.color,
                x: currentX,
                y: currentY,
                z: currentZ
            });
            
            currentX += item.width;
            rowHeight = Math.max(rowHeight, item.height);
            layerDepth = Math.max(layerDepth, item.depth);
        });
        
        return packedItems;
    }
    
    // Plusieurs méthodes pour s'assurer que le code s'exécute
    // Méthode 1: DOMContentLoaded
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initVolumeCalculator);
    } else {
        // DOM déjà chargé
        initVolumeCalculator();
    }
    
    // Méthode 2: window.onload comme fallback
    window.addEventListener('load', function() {
        if (!initialized) {
            initVolumeCalculator();
        }
    });
    
    // Méthode 3: Vérification périodique (pour Odoo qui charge dynamiquement)
    var checkInterval = setInterval(function() {
        if (document.querySelector('.volume-calculator-section') && !initialized) {
            initVolumeCalculator();
            clearInterval(checkInterval);
        }
    }, 200);
    
    // Arrêter la vérification après 10 secondes
    setTimeout(function() {
        clearInterval(checkInterval);
    }, 10000);
    
})();
