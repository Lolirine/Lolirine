/** @odoo-module **/

import { Component, useState, useRef, onMounted, onWillUnmount } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

/**
 * ImageCropSelector — Composant OWL 2 pour sélection interactive de zones d'image.
 *
 * Fonctionnalités :
 *  - Affichage inline redimensionnable + modal plein écran
 *  - Sélection manuelle par rectangle (drag & drop)
 *  - Sélection multiple (plusieurs zones sur une même capture)
 *  - Zoom / pan (molette + drag middle-click)
 *  - Auto-détection IA des zones produit (via Claude API)
 *  - Recadrage automatique (trim des bordures blanches)
 *
 * Props:
 *  - imageSrc: string (base64 data URL ou URL de l'image)
 *  - onRegionsSelected: function(regions[]) — callback avec les zones découpées
 *  - onAutoDetect: function(imageSrc) — callback optionnel pour auto-détection IA
 *  - maxSelections: number (0 = illimité, défaut: 10)
 *  - showAutoDetect: boolean (afficher le bouton auto-detect, défaut: true)
 */
export class ImageCropSelector extends Component {
    static template = "lolirine_pool_import.ImageCropSelector";
    static props = {
        imageSrc: { type: String },
        onRegionsSelected: { type: Function, optional: true },
        onAutoDetect: { type: Function, optional: true },
        maxSelections: { type: Number, optional: true },
        showAutoDetect: { type: Boolean, optional: true },
    };
    static defaultProps = {
        maxSelections: 10,
        showAutoDetect: true,
    };

    setup() {
        this.notification = useService("notification");

        // Refs
        this.canvasRef = useRef("canvas");
        this.containerRef = useRef("container");
        this.modalCanvasRef = useRef("modalCanvas");
        this.modalContainerRef = useRef("modalContainer");

        this.state = useState({
            // Régions sélectionnées [{x, y, w, h, label, croppedDataUrl}]
            regions: [],
            activeRegionIndex: -1,

            // Outil actif
            tool: "select",  // "select" | "pan"

            // Modal
            isModalOpen: false,

            // Zoom
            zoom: 1,
            panX: 0,
            panY: 0,

            // Dessin en cours
            isDrawing: false,
            drawStart: null,
            drawCurrent: null,

            // Image chargée
            imageLoaded: false,
            imageWidth: 0,
            imageHeight: 0,

            // Resize handle
            resizing: null,  // { regionIndex, handle } handle = 'nw','ne','sw','se','n','s','e','w'
            
            // Auto-detect loading
            autoDetecting: false,
        });

        // Image object
        this.img = null;
        this.animFrameId = null;

        // Dragging state (not reactive for performance)
        this._isPanning = false;
        this._panStart = null;
        this._dragRegionIndex = -1;
        this._dragOffset = null;

        onMounted(() => {
            this._loadImage();
            window.addEventListener("keydown", this._onKeyDown);
        });

        onWillUnmount(() => {
            if (this.animFrameId) cancelAnimationFrame(this.animFrameId);
            window.removeEventListener("keydown", this._onKeyDown);
        });
    }

    // ══════════════════════════════════════════════
    // Image Loading
    // ══════════════════════════════════════════════

    _loadImage() {
        this.img = new Image();
        this.img.onload = () => {
            this.state.imageLoaded = true;
            this.state.imageWidth = this.img.naturalWidth;
            this.state.imageHeight = this.img.naturalHeight;
            this._fitToContainer();
            this._render();
        };
        this.img.onerror = () => {
            this.state.imageLoaded = false;
        };
        this.img.src = this.props.imageSrc;
    }

    _fitToContainer(modal = false) {
        const container = modal
            ? this.modalContainerRef.el
            : this.containerRef.el;
        if (!container || !this.img) return;

        const cw = container.clientWidth;
        const ch = container.clientHeight || 500;
        const iw = this.img.naturalWidth;
        const ih = this.img.naturalHeight;

        const scaleX = cw / iw;
        const scaleY = ch / ih;
        this.state.zoom = Math.min(scaleX, scaleY, 1) * 0.95;
        this.state.panX = (cw - iw * this.state.zoom) / 2;
        this.state.panY = (ch - ih * this.state.zoom) / 2;
    }

    // ══════════════════════════════════════════════
    // Canvas Rendering
    // ══════════════════════════════════════════════

    _render() {
        this._renderCanvas(this.canvasRef);
        if (this.state.isModalOpen) {
            this._renderCanvas(this.modalCanvasRef);
        }
    }

    _renderCanvas(canvasRef) {
        const canvas = canvasRef.el;
        if (!canvas || !this.img || !this.state.imageLoaded) return;

        const ctx = canvas.getContext("2d");
        const container = canvas.parentElement;
        canvas.width = container.clientWidth;
        canvas.height = container.clientHeight || 500;

        ctx.clearRect(0, 0, canvas.width, canvas.height);

        // Fond damier (transparence)
        this._drawCheckerboard(ctx, canvas.width, canvas.height);

        ctx.save();
        ctx.translate(this.state.panX, this.state.panY);
        ctx.scale(this.state.zoom, this.state.zoom);

        // Image
        ctx.drawImage(this.img, 0, 0);

        // Overlay semi-transparent si on a des régions
        if (this.state.regions.length > 0 || this.state.isDrawing) {
            ctx.fillStyle = "rgba(0, 0, 0, 0.35)";
            ctx.fillRect(0, 0, this.img.naturalWidth, this.img.naturalHeight);
        }

        // Dessiner les régions sélectionnées (zones claires)
        this.state.regions.forEach((region, i) => {
            const isActive = i === this.state.activeRegionIndex;
            this._drawRegion(ctx, region, i, isActive);
        });

        // Dessiner la sélection en cours
        if (this.state.isDrawing && this.state.drawStart && this.state.drawCurrent) {
            const r = this._normalizeRect(this.state.drawStart, this.state.drawCurrent);
            this._drawRegionRect(ctx, r, -1, false, true);
        }

        ctx.restore();
    }

    _drawCheckerboard(ctx, w, h) {
        const size = 12;
        ctx.fillStyle = "#f0f0f0";
        ctx.fillRect(0, 0, w, h);
        ctx.fillStyle = "#e0e0e0";
        for (let y = 0; y < h; y += size) {
            for (let x = 0; x < w; x += size) {
                if ((Math.floor(x / size) + Math.floor(y / size)) % 2 === 0) {
                    ctx.fillRect(x, y, size, size);
                }
            }
        }
    }

    _drawRegion(ctx, region, index, isActive) {
        const { x, y, w, h } = region;

        // Zone claire (révéler l'image en dessous)
        ctx.save();
        ctx.beginPath();
        ctx.rect(x, y, w, h);
        ctx.clip();
        ctx.drawImage(this.img, 0, 0);
        ctx.restore();

        // Bordure
        ctx.strokeStyle = isActive ? "#00d4aa" : "#ffffff";
        ctx.lineWidth = 2 / this.state.zoom;
        ctx.setLineDash(isActive ? [] : [6 / this.state.zoom, 3 / this.state.zoom]);
        ctx.strokeRect(x, y, w, h);
        ctx.setLineDash([]);

        // Label
        const fontSize = Math.max(12, 14 / this.state.zoom);
        ctx.font = `bold ${fontSize}px sans-serif`;
        const label = region.label || `Zone ${index + 1}`;
        const textW = ctx.measureText(label).width;
        const pad = 4 / this.state.zoom;

        // Badge en haut à gauche
        const badgeColor = isActive ? "#00d4aa" : "rgba(255,255,255,0.9)";
        const textColor = isActive ? "#fff" : "#333";
        ctx.fillStyle = badgeColor;
        ctx.fillRect(x, y - fontSize - pad * 2, textW + pad * 4, fontSize + pad * 2);
        ctx.fillStyle = textColor;
        ctx.fillText(label, x + pad * 2, y - pad);

        // Handles de redimensionnement si actif
        if (isActive) {
            this._drawHandles(ctx, region);
        }
    }

    _drawRegionRect(ctx, rect, index, isActive, isDrawing) {
        const { x, y, w, h } = rect;

        ctx.save();
        ctx.beginPath();
        ctx.rect(x, y, w, h);
        ctx.clip();
        ctx.drawImage(this.img, 0, 0);
        ctx.restore();

        ctx.strokeStyle = isDrawing ? "#00aaff" : "#ffffff";
        ctx.lineWidth = 2 / this.state.zoom;
        ctx.setLineDash([4 / this.state.zoom, 4 / this.state.zoom]);
        ctx.strokeRect(x, y, w, h);
        ctx.setLineDash([]);

        // Dimensions
        if (w > 30 && h > 30) {
            const fontSize = Math.max(10, 11 / this.state.zoom);
            ctx.font = `${fontSize}px sans-serif`;
            ctx.fillStyle = "rgba(0,170,255,0.85)";
            const dimText = `${Math.round(w)} × ${Math.round(h)}`;
            ctx.fillText(dimText, x + 4 / this.state.zoom, y + h - 4 / this.state.zoom);
        }
    }

    _drawHandles(ctx, region) {
        const { x, y, w, h } = region;
        const handleSize = 8 / this.state.zoom;
        const handles = this._getHandlePositions(region);

        handles.forEach(({ hx, hy }) => {
            ctx.fillStyle = "#00d4aa";
            ctx.strokeStyle = "#fff";
            ctx.lineWidth = 1.5 / this.state.zoom;
            ctx.fillRect(hx - handleSize / 2, hy - handleSize / 2, handleSize, handleSize);
            ctx.strokeRect(hx - handleSize / 2, hy - handleSize / 2, handleSize, handleSize);
        });
    }

    _getHandlePositions(region) {
        const { x, y, w, h } = region;
        return [
            { name: "nw", hx: x, hy: y },
            { name: "ne", hx: x + w, hy: y },
            { name: "sw", hx: x, hy: y + h },
            { name: "se", hx: x + w, hy: y + h },
            { name: "n", hx: x + w / 2, hy: y },
            { name: "s", hx: x + w / 2, hy: y + h },
            { name: "w", hx: x, hy: y + h / 2 },
            { name: "e", hx: x + w, hy: y + h / 2 },
        ];
    }

    // ══════════════════════════════════════════════
    // Mouse Events
    // ══════════════════════════════════════════════

    _getImageCoords(ev) {
        const canvas = ev.target;
        const rect = canvas.getBoundingClientRect();
        const cx = ev.clientX - rect.left;
        const cy = ev.clientY - rect.top;
        const ix = (cx - this.state.panX) / this.state.zoom;
        const iy = (cy - this.state.panY) / this.state.zoom;
        return { cx, cy, ix, iy };
    }

    _hitTestHandle(ix, iy) {
        const threshold = 10 / this.state.zoom;
        for (let i = 0; i < this.state.regions.length; i++) {
            const handles = this._getHandlePositions(this.state.regions[i]);
            for (const h of handles) {
                if (Math.abs(ix - h.hx) < threshold && Math.abs(iy - h.hy) < threshold) {
                    return { regionIndex: i, handle: h.name };
                }
            }
        }
        return null;
    }

    _hitTestRegion(ix, iy) {
        // Test in reverse order (topmost first)
        for (let i = this.state.regions.length - 1; i >= 0; i--) {
            const r = this.state.regions[i];
            if (ix >= r.x && ix <= r.x + r.w && iy >= r.y && iy <= r.y + r.h) {
                return i;
            }
        }
        return -1;
    }

    onCanvasMouseDown(ev) {
        ev.preventDefault();
        const { cx, cy, ix, iy } = this._getImageCoords(ev);

        // Middle click or space+click = pan
        if (ev.button === 1 || this.state.tool === "pan") {
            this._isPanning = true;
            this._panStart = { x: cx, y: cy, panX: this.state.panX, panY: this.state.panY };
            return;
        }

        if (ev.button !== 0) return;

        // Check handles first (resize)
        const handleHit = this._hitTestHandle(ix, iy);
        if (handleHit) {
            this.state.resizing = handleHit;
            this.state.activeRegionIndex = handleHit.regionIndex;
            this._render();
            return;
        }

        // Check if clicking an existing region (drag to move)
        const regionHit = this._hitTestRegion(ix, iy);
        if (regionHit >= 0 && !ev.shiftKey) {
            this.state.activeRegionIndex = regionHit;
            const r = this.state.regions[regionHit];
            this._dragRegionIndex = regionHit;
            this._dragOffset = { x: ix - r.x, y: iy - r.y };
            this._render();
            return;
        }

        // Start new selection
        if (this.props.maxSelections > 0 && this.state.regions.length >= this.props.maxSelections) {
            this.notification.add("Nombre maximum de sélections atteint", { type: "warning" });
            return;
        }

        this.state.isDrawing = true;
        this.state.drawStart = { x: ix, y: iy };
        this.state.drawCurrent = { x: ix, y: iy };
        this.state.activeRegionIndex = -1;
    }

    onCanvasMouseMove(ev) {
        const { cx, cy, ix, iy } = this._getImageCoords(ev);

        // Panning
        if (this._isPanning && this._panStart) {
            this.state.panX = this._panStart.panX + (cx - this._panStart.x);
            this.state.panY = this._panStart.panY + (cy - this._panStart.y);
            this._render();
            return;
        }

        // Resizing
        if (this.state.resizing) {
            this._applyResize(ix, iy);
            this._render();
            return;
        }

        // Dragging a region
        if (this._dragRegionIndex >= 0 && this._dragOffset) {
            const r = this.state.regions[this._dragRegionIndex];
            r.x = Math.max(0, Math.min(ix - this._dragOffset.x, this.state.imageWidth - r.w));
            r.y = Math.max(0, Math.min(iy - this._dragOffset.y, this.state.imageHeight - r.h));
            this._render();
            return;
        }

        // Drawing new selection
        if (this.state.isDrawing) {
            this.state.drawCurrent = { x: ix, y: iy };
            this._render();
            return;
        }

        // Cursor feedback
        this._updateCursor(ev.target, ix, iy);
    }

    onCanvasMouseUp(ev) {
        // End panning
        if (this._isPanning) {
            this._isPanning = false;
            this._panStart = null;
            return;
        }

        // End resizing
        if (this.state.resizing) {
            this._cropRegionImage(this.state.resizing.regionIndex);
            this.state.resizing = null;
            this._notifyChange();
            return;
        }

        // End dragging
        if (this._dragRegionIndex >= 0) {
            this._cropRegionImage(this._dragRegionIndex);
            this._dragRegionIndex = -1;
            this._dragOffset = null;
            this._notifyChange();
            return;
        }

        // End drawing
        if (this.state.isDrawing && this.state.drawStart && this.state.drawCurrent) {
            const r = this._normalizeRect(this.state.drawStart, this.state.drawCurrent);

            // Minimum size check (at least 20x20 pixels)
            if (r.w > 20 && r.h > 20) {
                const newRegion = {
                    x: r.x, y: r.y, w: r.w, h: r.h,
                    label: `Image ${this.state.regions.length + 1}`,
                    croppedDataUrl: null,
                };
                this.state.regions.push(newRegion);
                this.state.activeRegionIndex = this.state.regions.length - 1;
                this._cropRegionImage(this.state.regions.length - 1);
                this._notifyChange();
            }

            this.state.isDrawing = false;
            this.state.drawStart = null;
            this.state.drawCurrent = null;
            this._render();
        }
    }

    onCanvasWheel(ev) {
        ev.preventDefault();
        const { cx, cy } = this._getImageCoords(ev);

        const factor = ev.deltaY < 0 ? 1.1 : 0.9;
        const newZoom = Math.max(0.1, Math.min(10, this.state.zoom * factor));

        // Zoom vers le curseur
        this.state.panX = cx - (cx - this.state.panX) * (newZoom / this.state.zoom);
        this.state.panY = cy - (cy - this.state.panY) * (newZoom / this.state.zoom);
        this.state.zoom = newZoom;

        this._render();
    }

    // ══════════════════════════════════════════════
    // Resize Logic
    // ══════════════════════════════════════════════

    _applyResize(ix, iy) {
        const { regionIndex, handle } = this.state.resizing;
        const r = this.state.regions[regionIndex];
        const minSize = 10;

        const origRight = r.x + r.w;
        const origBottom = r.y + r.h;

        if (handle.includes("w")) {
            const newX = Math.min(ix, origRight - minSize);
            r.w = origRight - newX;
            r.x = newX;
        }
        if (handle.includes("e")) {
            r.w = Math.max(minSize, ix - r.x);
        }
        if (handle.includes("n")) {
            const newY = Math.min(iy, origBottom - minSize);
            r.h = origBottom - newY;
            r.y = newY;
        }
        if (handle.includes("s")) {
            r.h = Math.max(minSize, iy - r.y);
        }

        // Clamp to image bounds
        r.x = Math.max(0, r.x);
        r.y = Math.max(0, r.y);
        r.w = Math.min(r.w, this.state.imageWidth - r.x);
        r.h = Math.min(r.h, this.state.imageHeight - r.y);
    }

    _updateCursor(canvas, ix, iy) {
        const handleHit = this._hitTestHandle(ix, iy);
        if (handleHit) {
            const cursors = {
                nw: "nw-resize", ne: "ne-resize", sw: "sw-resize", se: "se-resize",
                n: "n-resize", s: "s-resize", w: "w-resize", e: "e-resize",
            };
            canvas.style.cursor = cursors[handleHit.handle] || "default";
            return;
        }
        if (this._hitTestRegion(ix, iy) >= 0) {
            canvas.style.cursor = "move";
            return;
        }
        canvas.style.cursor = this.state.tool === "pan" ? "grab" : "crosshair";
    }

    // ══════════════════════════════════════════════
    // Region Cropping
    // ══════════════════════════════════════════════

    _cropRegionImage(index) {
        const region = this.state.regions[index];
        if (!region || !this.img) return;

        const tempCanvas = document.createElement("canvas");
        tempCanvas.width = Math.round(region.w);
        tempCanvas.height = Math.round(region.h);
        const tCtx = tempCanvas.getContext("2d");

        // Fond blanc
        tCtx.fillStyle = "#ffffff";
        tCtx.fillRect(0, 0, tempCanvas.width, tempCanvas.height);

        // Dessiner la portion d'image
        tCtx.drawImage(
            this.img,
            region.x, region.y, region.w, region.h,
            0, 0, tempCanvas.width, tempCanvas.height
        );

        // Auto-trim des bordures blanches restantes
        const trimmed = this._autoTrim(tCtx, tempCanvas.width, tempCanvas.height);
        if (trimmed) {
            const trimCanvas = document.createElement("canvas");
            const pad = 5;
            trimCanvas.width = trimmed.w + pad * 2;
            trimCanvas.height = trimmed.h + pad * 2;
            const trimCtx = trimCanvas.getContext("2d");
            trimCtx.fillStyle = "#ffffff";
            trimCtx.fillRect(0, 0, trimCanvas.width, trimCanvas.height);
            trimCtx.drawImage(
                tempCanvas,
                trimmed.x, trimmed.y, trimmed.w, trimmed.h,
                pad, pad, trimmed.w, trimmed.h
            );
            region.croppedDataUrl = trimCanvas.toDataURL("image/png");
        } else {
            region.croppedDataUrl = tempCanvas.toDataURL("image/png");
        }
    }

    _autoTrim(ctx, w, h) {
        const imageData = ctx.getImageData(0, 0, w, h);
        const data = imageData.data;
        const threshold = 245; // Pixels plus clairs que ça = "blanc"

        let top = h, bottom = 0, left = w, right = 0;

        for (let y = 0; y < h; y++) {
            for (let x = 0; x < w; x++) {
                const idx = (y * w + x) * 4;
                const r = data[idx], g = data[idx + 1], b = data[idx + 2];
                if (r < threshold || g < threshold || b < threshold) {
                    if (y < top) top = y;
                    if (y > bottom) bottom = y;
                    if (x < left) left = x;
                    if (x > right) right = x;
                }
            }
        }

        if (top >= bottom || left >= right) return null;

        const tw = right - left + 1;
        const th = bottom - top + 1;
        // Don't trim if it would remove more than 80%
        if (tw * th < w * h * 0.2) return null;

        return { x: left, y: top, w: tw, h: th };
    }

    // ══════════════════════════════════════════════
    // Toolbar Actions
    // ══════════════════════════════════════════════

    onToolSelect() {
        this.state.tool = "select";
    }

    onToolPan() {
        this.state.tool = "pan";
    }

    onZoomIn() {
        this.state.zoom = Math.min(10, this.state.zoom * 1.25);
        this._render();
    }

    onZoomOut() {
        this.state.zoom = Math.max(0.1, this.state.zoom / 1.25);
        this._render();
    }

    onZoomFit() {
        this._fitToContainer(this.state.isModalOpen);
        this._render();
    }

    onDeleteRegion() {
        if (this.state.activeRegionIndex >= 0) {
            this.state.regions.splice(this.state.activeRegionIndex, 1);
            this.state.activeRegionIndex = -1;
            this._render();
            this._notifyChange();
        }
    }

    onClearAll() {
        this.state.regions = [];
        this.state.activeRegionIndex = -1;
        this._render();
        this._notifyChange();
    }

    // ══════════════════════════════════════════════
    // Modal
    // ══════════════════════════════════════════════

    onOpenModal() {
        this.state.isModalOpen = true;
        // Render in next tick after modal DOM is created
        setTimeout(() => {
            this._fitToContainer(true);
            this._render();
        }, 100);
    }

    onCloseModal() {
        this.state.isModalOpen = false;
        this._fitToContainer(false);
        this._render();
    }

    // ══════════════════════════════════════════════
    // Auto-Detect
    // ══════════════════════════════════════════════

    async onAutoDetect() {
        if (!this.props.onAutoDetect) return;

        this.state.autoDetecting = true;
        try {
            const detectedRegions = await this.props.onAutoDetect(this.props.imageSrc);
            if (detectedRegions && detectedRegions.length > 0) {
                // Convert percent-based coordinates to pixel coordinates
                for (const dr of detectedRegions) {
                    const region = {
                        x: (dr.x_percent / 100) * this.state.imageWidth,
                        y: (dr.y_percent / 100) * this.state.imageHeight,
                        w: (dr.width_percent / 100) * this.state.imageWidth,
                        h: (dr.height_percent / 100) * this.state.imageHeight,
                        label: dr.label || `Produit ${this.state.regions.length + 1}`,
                        croppedDataUrl: null,
                    };
                    this.state.regions.push(region);
                    this._cropRegionImage(this.state.regions.length - 1);
                }
                this.state.activeRegionIndex = 0;
                this._render();
                this._notifyChange();

                this.notification.add(
                    `${detectedRegions.length} zone(s) produit détectée(s)`,
                    { type: "success" }
                );
            } else {
                this.notification.add(
                    "Aucune zone produit détectée. Sélectionnez manuellement.",
                    { type: "warning" }
                );
            }
        } catch (err) {
            console.error("Auto-detect error:", err);
            this.notification.add(
                "Erreur lors de la détection automatique",
                { type: "danger" }
            );
        } finally {
            this.state.autoDetecting = false;
        }
    }

    // ══════════════════════════════════════════════
    // Extract / Confirm
    // ══════════════════════════════════════════════

    onConfirmSelection() {
        const regions = this.state.regions.filter(r => r.croppedDataUrl);
        if (regions.length === 0) {
            this.notification.add("Sélectionnez au moins une zone", { type: "warning" });
            return;
        }
        if (this.props.onRegionsSelected) {
            this.props.onRegionsSelected(regions.map(r => ({
                x: Math.round(r.x),
                y: Math.round(r.y),
                w: Math.round(r.w),
                h: Math.round(r.h),
                label: r.label,
                dataUrl: r.croppedDataUrl,
                base64: r.croppedDataUrl.split(",")[1],
            })));
        }
    }

    // ══════════════════════════════════════════════
    // Keyboard
    // ══════════════════════════════════════════════

    _onKeyDown = (ev) => {
        if (ev.key === "Delete" || ev.key === "Backspace") {
            if (this.state.activeRegionIndex >= 0) {
                this.onDeleteRegion();
            }
        }
        if (ev.key === "Escape") {
            if (this.state.isModalOpen) {
                this.onCloseModal();
            } else if (this.state.isDrawing) {
                this.state.isDrawing = false;
                this.state.drawStart = null;
                this.state.drawCurrent = null;
                this._render();
            }
        }
        if (ev.key === " ") {
            ev.preventDefault();
            this.state.tool = this.state.tool === "pan" ? "select" : "pan";
        }
    };

    // ══════════════════════════════════════════════
    // Helpers
    // ══════════════════════════════════════════════

    _normalizeRect(start, end) {
        const x = Math.min(start.x, end.x);
        const y = Math.min(start.y, end.y);
        const w = Math.abs(end.x - start.x);
        const h = Math.abs(end.y - start.y);
        return { x, y, w, h };
    }

    _notifyChange() {
        // Trigger re-render of previews
        this._render();
    }

    // ══════════════════════════════════════════════
    // Region list actions
    // ══════════════════════════════════════════════

    onSelectRegion(index) {
        this.state.activeRegionIndex = index;
        this._render();
    }

    onRemoveRegion(index) {
        this.state.regions.splice(index, 1);
        if (this.state.activeRegionIndex >= this.state.regions.length) {
            this.state.activeRegionIndex = this.state.regions.length - 1;
        }
        this._render();
        this._notifyChange();
    }

    onRegionLabelChange(index, ev) {
        this.state.regions[index].label = ev.target.value;
        this._render();
    }

    get zoomPercent() {
        return Math.round(this.state.zoom * 100);
    }

    get hasRegions() {
        return this.state.regions.length > 0;
    }
}
