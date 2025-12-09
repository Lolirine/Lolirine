/**
 * Calculateur de Volume avec Visualisation 3D
 * Plan Interactif Garde-Meubles v1.0.48
 * 
 * Utilise Three.js pour la visualisation 3D et un algorithme de bin packing
 */

(function() {
    'use strict';
    
    // Attendre que le DOM soit prêt
    document.addEventListener('DOMContentLoaded', function() {
        var calculator = document.querySelector('.volume-calculator-section');
        if (!calculator) return;
        
        console.log('Volume Calculator loaded v1.0.48');
        
        var selectedItems = {};
        var totalVolume = 0;
        var scene, camera, renderer, controls;
        var furnitureObjects = [];
        
        // Initialiser le calculateur
        initCalculator();
        initThreeJS();
        
        function initCalculator() {
            // Event listeners pour les onglets
            var tabs = calculator.querySelectorAll('.category-tab');
            tabs.forEach(function(tab) {
                tab.addEventListener('click', function(e) {
                    e.preventDefault();
                    var categoryId = this.getAttribute('data-category-id');
                    
                    // Mettre à jour les onglets actifs
                    tabs.forEach(function(t) { t.classList.remove('active'); });
                    this.classList.add('active');
                    
                    // Afficher le bon panneau
                    var panels = calculator.querySelectorAll('.furniture-category-panel');
                    panels.forEach(function(p) { p.classList.remove('active'); });
                    var activePanel = calculator.querySelector('.furniture-category-panel[data-category-id="' + categoryId + '"]');
                    if (activePanel) activePanel.classList.add('active');
                });
            });
            
            // Event listeners pour les boutons +/-
            calculator.querySelectorAll('.furniture-btn-minus').forEach(function(btn) {
                btn.addEventListener('click', function(e) {
                    e.preventDefault();
                    var furnitureId = this.getAttribute('data-furniture-id');
                    var currentQty = selectedItems[furnitureId] || 0;
                    if (currentQty > 0) {
                        selectedItems[furnitureId] = currentQty - 1;
                        updateDisplay();
                        update3DVisualization();
                    }
                });
            });
            
            calculator.querySelectorAll('.furniture-btn-plus').forEach(function(btn) {
                btn.addEventListener('click', function(e) {
                    e.preventDefault();
                    var furnitureId = this.getAttribute('data-furniture-id');
                    var currentQty = selectedItems[furnitureId] || 0;
                    selectedItems[furnitureId] = currentQty + 1;
                    updateDisplay();
                    update3DVisualization();
                });
            });
            
            // Bouton reset
            var resetBtn = calculator.querySelector('.btn-reset-calculator');
            if (resetBtn) {
                resetBtn.addEventListener('click', function(e) {
                    e.preventDefault();
                    selectedItems = {};
                    updateDisplay();
                    update3DVisualization();
                });
            }
            
            // Bouton voir boxes
            var viewBoxesBtn = calculator.querySelector('.btn-view-boxes');
            if (viewBoxesBtn) {
                viewBoxesBtn.addEventListener('click', function(e) {
                    e.preventDefault();
                    var plan = document.querySelector('.storage-plan-container');
                    if (plan) {
                        plan.scrollIntoView({ behavior: 'smooth', block: 'start' });
                    }
                });
            }
        }
        
        function initThreeJS() {
            var canvas = document.getElementById('volume-3d-canvas');
            if (!canvas || typeof THREE === 'undefined') {
                console.log('Three.js not loaded or canvas not found');
                return;
            }
            
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
            renderer.shadowMap.type = THREE.PCFSoftShadowMap;
            
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
            
            // OrbitControls
            if (typeof THREE.OrbitControls !== 'undefined') {
                controls = new THREE.OrbitControls(camera, renderer.domElement);
                controls.enableDamping = true;
                controls.dampingFactor = 0.05;
                controls.minDistance = 3;
                controls.maxDistance = 15;
            }
            
            // Animation loop
            animate();
        }
        
        function createBoxWireframe(width, height, depth) {
            if (!scene) return;
            
            var existing = scene.getObjectByName('boxWireframe');
            if (existing) scene.remove(existing);
            
            var geometry = new THREE.BoxGeometry(width, height, depth);
            var edges = new THREE.EdgesGeometry(geometry);
            var material = new THREE.LineBasicMaterial({ color: 0x1565C0, linewidth: 2 });
            var wireframe = new THREE.LineSegments(edges, material);
            wireframe.name = 'boxWireframe';
            wireframe.position.y = height / 2;
            scene.add(wireframe);
        }
        
        function animate() {
            requestAnimationFrame(animate);
            if (controls) controls.update();
            if (renderer && scene && camera) {
                renderer.render(scene, camera);
            }
        }
        
        function updateDisplay() {
            var total = 0;
            
            calculator.querySelectorAll('.furniture-item').forEach(function(item) {
                var furnitureId = item.getAttribute('data-furniture-id');
                var volume = parseFloat(item.getAttribute('data-volume')) || 0;
                var qty = selectedItems[furnitureId] || 0;
                
                item.querySelector('.furniture-qty').textContent = qty;
                
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
            
            calculator.querySelectorAll('.box-volume-item').forEach(function(boxItem) {
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
                }
                
                // Mettre à jour le wireframe 3D
                if (scene) {
                    var side = Math.pow(bestBox.volume, 1/3);
                    createBoxWireframe(side * 1.2, side, side * 1.2);
                }
            }
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
            calculator.querySelectorAll('.furniture-item').forEach(function(item) {
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
                            id: furnitureId + '_' + i,
                            name: name,
                            width: width,
                            depth: depth,
                            height: height,
                            color: color
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
    });
})();
