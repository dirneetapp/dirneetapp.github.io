/**
 * Bar Sergio's - Realtime Firebase Firestore Carta Synchronizer
 * Sincronización en tiempo real entre la App Admin, App Cliente y la Web (GitHub Pages / dirneetapp.github.io)
 * La carta de la App Admin (colección Firestore 'menu') es la AUTORIDAD PREDOMINANTE.
 * Cualquier modificación, foto, orden o eliminación en la App Admin se refleja en tiempo real en la web.
 * Copyright 2026 Bar Sergio's
 */

(function () {
    'use strict';

    // Configuración oficial del proyecto Firebase de Bar Sergio's
    const FIREBASE_CONFIG = {
        apiKey: "AIzaSyCTjocpYrYYgKEKiRENkdqjA1cYVfg2pEo",
        authDomain: "bar-sergios-fidelizacion.firebaseapp.com",
        projectId: "bar-sergios-fidelizacion",
        storageBucket: "bar-sergios-fidelizacion.firebasestorage.app",
        messagingSenderId: "301179739189",
        appId: "1:301179739189:android:88c517a07bcbd742cae57c"
    };

    // Mapeo del archivo HTML a la categoría de Firestore
    function detectCurrentCategory() {
        const path = decodeURIComponent((window.location.pathname || '').toLowerCase());
        if (path.includes('desayunos')) return 'DESAYUNOS';
        if (path.includes('bocadillos')) return 'BOCADILLOS';
        if (path.includes('vermuts')) return 'VERMUTS';
        if (path.includes('tapas') && !path.includes('tapaarroz')) return 'TAPAS';
        if (path.includes('torradas')) return 'TORRADAS';
        if (path.includes('tablas')) return 'TABLAS';
        if (path.includes('platos') || path.includes('especiales')) return 'PLATOS_ESPECIALES';
        if (path.includes('arroz') || path.includes('tapaarroz')) return 'ARROZ';
        if (path.includes('croquetas')) return 'CROQUETAS';
        if (path.includes('postres')) return 'POSTRES';
        return null; // index.html o ruleta
    }

    // Normalizador de nombres para emparejar documentos con el DOM
    function normalizeName(str) {
        if (!str) return '';
        return str
            .toLowerCase()
            .normalize("NFD").replace(/[\u0300-\u036f]/g, "") // quita acentos
            .replace(/[¿?¡!.,;:()'"\-_/\\]/g, ' ')
            .replace(/\s+/g, ' ')
            .trim();
    }

    // Escapa caracteres HTML peligrosos
    function escapeHtml(str) {
        if (!str) return '';
        return String(str)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#039;');
    }

    // Convierte cadena Base64 de Firestore en Data URL válida para <img>
    function toDataUrl(base64Str) {
        if (!base64Str || typeof base64Str !== 'string') return null;
        const trimmed = base64Str.trim();
        if (!trimmed) return null;
        if (trimmed.startsWith('data:image')) return trimmed;
        return 'data:image/jpeg;base64,' + trimmed;
    }

    // Carga dinámica de los scripts de Firebase SDK si no están en el DOM
    function ensureFirebaseLoaded(callback) {
        if (window.firebase && window.firebase.firestore) {
            callback();
            return;
        }

        const appScript = document.createElement('script');
        appScript.src = "https://www.gstatic.com/firebasejs/10.8.0/firebase-app-compat.js";
        appScript.onload = function () {
            const firestoreScript = document.createElement('script');
            firestoreScript.src = "https://www.gstatic.com/firebasejs/10.8.0/firebase-firestore-compat.js";
            firestoreScript.onload = callback;
            document.head.appendChild(firestoreScript);
        };
        document.head.appendChild(appScript);
    }

    // Estilos visuales para elementos sincronizados
    function injectStyles() {
        if (document.getElementById('firebase-sync-styles')) return;
        const style = document.createElement('style');
        style.id = 'firebase-sync-styles';
        style.textContent = `
            .item-agotado-hoy {
                opacity: 0.52 !important;
                filter: grayscale(80%) !important;
                position: relative;
                transition: all 0.4s ease;
            }
            .badge-agotado-hoy {
                display: inline-flex !important;
                align-items: center;
                gap: 4px;
                background: linear-gradient(135deg, #ef4444 0%, #b91c1c 100%) !important;
                color: #ffffff !important;
                font-size: 0.72rem !important;
                font-weight: 800 !important;
                padding: 3px 8px !important;
                border-radius: 6px !important;
                margin-left: 8px !important;
                vertical-align: middle !important;
                text-transform: uppercase !important;
                box-shadow: 0 2px 6px rgba(239, 68, 68, 0.45) !important;
                letter-spacing: 0.5px;
            }
            .badge-destacado-live {
                display: inline-flex !important;
                align-items: center;
                gap: 3px;
                background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%) !important;
                color: #000000 !important;
                font-size: 0.7rem !important;
                font-weight: 800 !important;
                padding: 2px 8px !important;
                border-radius: 8px !important;
                margin-left: 6px !important;
                vertical-align: middle !important;
                box-shadow: 0 2px 5px rgba(245, 158, 11, 0.35) !important;
            }
            .badge-novedad-live {
                display: inline-flex !important;
                align-items: center;
                gap: 3px;
                background: linear-gradient(135deg, #10b981 0%, #059669 100%) !important;
                color: #ffffff !important;
                font-size: 0.7rem !important;
                font-weight: 800 !important;
                padding: 2px 8px !important;
                border-radius: 8px !important;
                margin-left: 6px !important;
                vertical-align: middle !important;
                box-shadow: 0 2px 5px rgba(16, 185, 129, 0.35) !important;
            }
            .price-pulse-live {
                animation: pricePulse 1.2s ease;
            }
            @keyframes pricePulse {
                0% { transform: scale(1); }
                50% { transform: scale(1.15); color: #8cff00; }
                100% { transform: scale(1); }
            }
            .live-sync-indicator {
                display: inline-flex;
                align-items: center;
                gap: 6px;
                font-size: 0.75rem;
                color: #8cff00;
                background: rgba(140, 255, 0, 0.08);
                border: 1px solid rgba(140, 255, 0, 0.25);
                padding: 4px 12px;
                border-radius: 20px;
                margin: 8px auto;
                font-family: inherit;
                font-weight: 600;
                backdrop-filter: blur(6px);
            }
            .live-sync-indicator .dot {
                width: 7px;
                height: 7px;
                border-radius: 50%;
                background: #8cff00;
                box-shadow: 0 0 8px #8cff00;
                animation: blinkLive 2s infinite ease-in-out;
            }
            @keyframes blinkLive {
                0%, 100% { opacity: 1; transform: scale(1); }
                50% { opacity: 0.4; transform: scale(0.85); }
            }
            .firebase-sync-toast {
                position: fixed;
                top: 24px;
                left: 50%;
                transform: translateX(-50%);
                background: rgba(18, 20, 26, 0.96);
                border: 1.5px solid #8cff00;
                color: #ffffff;
                padding: 10px 22px;
                border-radius: 30px;
                font-size: 0.88rem;
                font-weight: 700;
                box-shadow: 0 10px 30px rgba(0, 0, 0, 0.8), 0 0 16px rgba(140, 255, 0, 0.45);
                z-index: 99999;
                display: flex;
                align-items: center;
                gap: 10px;
                pointer-events: none;
                animation: slideDownToast 0.3s ease;
            }
            @keyframes slideDownToast {
                from { opacity: 0; transform: translate(-50%, -15px); }
                to { opacity: 1; transform: translate(-50%, 0); }
            }

            /* Miniatura de Foto o Icono Emoji en la Carta */
            .dish-thumb-box {
                width: 64px;
                height: 64px;
                border-radius: 14px;
                background: rgba(255, 255, 255, 0.05);
                margin-right: 14px;
                flex-shrink: 0;
                display: flex;
                align-items: center;
                justify-content: center;
                position: relative;
                overflow: hidden;
                transition: transform 0.2s ease, border-color 0.2s ease;
            }
            .dish-thumb-box.has-photo {
                border: 1.5px solid rgba(140, 255, 0, 0.65);
                cursor: zoom-in;
                box-shadow: 0 4px 12px rgba(0, 0, 0, 0.35);
            }
            .dish-thumb-box.has-photo:hover {
                transform: scale(1.05);
                border-color: #8cff00;
            }
            .dish-thumb-box.has-emoji {
                border: 1px solid rgba(212, 175, 55, 0.3);
                cursor: default;
                font-size: 1.85rem;
                user-select: none;
            }
            .dish-thumb-img {
                width: 100%;
                height: 100%;
                object-fit: cover;
                display: block;
            }
            .dish-thumb-zoom-badge {
                position: absolute;
                bottom: 3px;
                right: 3px;
                width: 18px;
                height: 18px;
                border-radius: 50%;
                background: rgba(0, 0, 0, 0.78);
                color: #8cff00;
                font-size: 10px;
                display: flex;
                align-items: center;
                justify-content: center;
                pointer-events: none;
            }

            /* Modal de Vista Ampliada de Foto + Descripción Debajo */
            .dish-photo-modal-overlay {
                position: fixed;
                inset: 0;
                background: rgba(0, 0, 0, 0.86);
                backdrop-filter: blur(8px);
                z-index: 10000;
                display: flex;
                align-items: center;
                justify-content: center;
                padding: 16px;
                opacity: 0;
                pointer-events: none;
                transition: opacity 0.25s ease;
            }
            .dish-photo-modal-overlay.open {
                opacity: 1;
                pointer-events: auto;
            }
            .dish-photo-modal-card {
                width: 100%;
                max-width: 440px;
                background: #181a20;
                border: 1.5px solid rgba(140, 255, 0, 0.65);
                border-radius: 24px;
                overflow: hidden;
                box-shadow: 0 24px 60px rgba(0, 0, 0, 0.85);
                transform: scale(0.94);
                transition: transform 0.25s ease;
            }
            .dish-photo-modal-overlay.open .dish-photo-modal-card {
                transform: scale(1);
            }
            .dish-photo-modal-img-wrap {
                width: 100%;
                height: 300px;
                background: #000;
                position: relative;
            }
            .dish-photo-modal-img {
                width: 100%;
                height: 100%;
                object-fit: cover;
                display: block;
            }
            .dish-photo-modal-close {
                position: absolute;
                top: 12px;
                right: 12px;
                width: 36px;
                height: 36px;
                border-radius: 50%;
                background: rgba(0, 0, 0, 0.72);
                border: 1px solid rgba(255, 255, 255, 0.25);
                color: #fff;
                font-size: 1.1rem;
                cursor: pointer;
                display: flex;
                align-items: center;
                justify-content: center;
            }
            .dish-photo-modal-body {
                padding: 20px;
            }
            .dish-photo-modal-header {
                display: flex;
                align-items: center;
                justify-content: space-between;
                gap: 12px;
            }
            .dish-photo-modal-title {
                font-size: 1.25rem;
                font-weight: 800;
                color: #ffffff;
                margin: 0;
                line-height: 1.3;
            }
            .dish-photo-modal-price {
                background: rgba(140, 255, 0, 0.16);
                border: 1px solid rgba(140, 255, 0, 0.6);
                color: #8cff00;
                font-size: 1rem;
                font-weight: 800;
                padding: 5px 12px;
                border-radius: 10px;
                white-space: nowrap;
            }
            .dish-photo-modal-desc-box {
                margin-top: 14px;
                background: #101216;
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 14px;
                padding: 14px;
            }
            .dish-photo-modal-desc-label {
                font-size: 0.65rem;
                font-weight: 800;
                color: #8cff00;
                letter-spacing: 1px;
                text-transform: uppercase;
                margin-bottom: 6px;
            }
            .dish-photo-modal-desc-text {
                font-size: 0.94rem;
                color: #e5e7eb;
                line-height: 1.5;
                margin: 0;
            }
        `;
        document.head.appendChild(style);
    }

    // Crea y gestiona el modal de foto ampliada con descripción debajo
    function ensureDishPhotoModal() {
        let modal = document.getElementById('dishPhotoDetailModal');
        if (modal) return modal;

        modal = document.createElement('div');
        modal.id = 'dishPhotoDetailModal';
        modal.className = 'dish-photo-modal-overlay';
        modal.innerHTML = `
            <div class="dish-photo-modal-card" onclick="event.stopPropagation()">
                <div class="dish-photo-modal-img-wrap">
                    <img id="dishPhotoModalImg" class="dish-photo-modal-img" alt="Foto del producto">
                    <button type="button" class="dish-photo-modal-close" id="dishPhotoModalClose" title="Cerrar">✕</button>
                </div>
                <div class="dish-photo-modal-body">
                    <div class="dish-photo-modal-header">
                        <h3 id="dishPhotoModalTitle" class="dish-photo-modal-title"></h3>
                        <span id="dishPhotoModalPrice" class="dish-photo-modal-price"></span>
                    </div>
                    <div class="dish-photo-modal-desc-box">
                        <div class="dish-photo-modal-desc-label">DESCRIPCIÓN DEL PRODUCTO</div>
                        <p id="dishPhotoModalDesc" class="dish-photo-modal-desc-text"></p>
                    </div>
                </div>
            </div>
        `;
        modal.addEventListener('click', function () {
            modal.classList.remove('open');
        });
        document.body.appendChild(modal);

        const closeBtn = document.getElementById('dishPhotoModalClose');
        if (closeBtn) {
            closeBtn.addEventListener('click', function () {
                modal.classList.remove('open');
            });
        }
        document.addEventListener('keydown', function (e) {
            if (e.key === 'Escape') modal.classList.remove('open');
        });
        return modal;
    }

    function openDishPhotoModal(dataUrl, name, priceFormatted, description) {
        const modal = ensureDishPhotoModal();
        const imgEl = document.getElementById('dishPhotoModalImg');
        const titleEl = document.getElementById('dishPhotoModalTitle');
        const priceEl = document.getElementById('dishPhotoModalPrice');
        const descEl = document.getElementById('dishPhotoModalDesc');

        if (imgEl) imgEl.src = dataUrl;
        if (titleEl) titleEl.textContent = name || '';
        if (priceEl) priceEl.textContent = priceFormatted || '';
        if (descEl) {
            descEl.textContent = (description && description.trim())
                ? description.trim()
                : "Especialidad de la carta de Bar Sergio's.";
        }
        modal.classList.add('open');
    }

    // Compatibilidad: sobreescribir showImageModal para redirigir al modal de foto
    window.showImageModal = function (src) {
        openDishPhotoModal(src, '', '', '');
    };

    // Actualiza o inserta la miniatura (Foto pulsable vs Icono Emoji no pulsable) en un .menu-item
    function syncDishThumbnail(itemEl, firestoreData) {
        const photoDataUrl = toDataUrl(firestoreData.imageBase64);
        const iconEmoji = (firestoreData.iconEmoji && firestoreData.iconEmoji.trim()) ? firestoreData.iconEmoji.trim() : '';

        // Ocultar imagen estática antigua si existiera para evitar duplicados
        const legacyImg = itemEl.querySelector('img.item-image');
        if (legacyImg) {
            legacyImg.style.display = 'none';
            legacyImg.onclick = null;
        }

        let thumbBox = itemEl.querySelector('.dish-thumb-box');

        const priceText = (typeof firestoreData.price === 'number')
            ? firestoreData.price.toFixed(2).replace('.', ',') + ' €'
            : '';

        if (photoDataUrl) {
            if (!thumbBox) {
                thumbBox = document.createElement('div');
                itemEl.insertBefore(thumbBox, itemEl.firstChild);
            }
            thumbBox.className = 'dish-thumb-box has-photo';
            thumbBox.title = 'Pulsa para ver la foto en grande';
            thumbBox.innerHTML = `
                <img class="dish-thumb-img" src="${photoDataUrl}" alt="${firestoreData.name || 'Producto'}">
                <span class="dish-thumb-zoom-badge">🔍</span>
            `;
            thumbBox.onclick = function (e) {
                e.stopPropagation();
                openDishPhotoModal(
                    photoDataUrl,
                    firestoreData.name || '',
                    priceText,
                    firestoreData.description || ''
                );
            };

            // Limpiar onclick antiguo de .item-details y redirigir al visor ampliado
            const detailsEl = itemEl.querySelector('.item-details');
            if (detailsEl) {
                detailsEl.removeAttribute('onclick');
                detailsEl.style.cursor = 'zoom-in';
                detailsEl.onclick = function (e) {
                    if (e.target && (e.target.closest('button') || e.target.closest('select') || e.target.closest('a'))) return;
                    e.stopPropagation();
                    openDishPhotoModal(
                        photoDataUrl,
                        firestoreData.name || '',
                        priceText,
                        firestoreData.description || ''
                    );
                };
            }
        } else if (iconEmoji) {
            if (!thumbBox) {
                thumbBox = document.createElement('div');
                itemEl.insertBefore(thumbBox, itemEl.firstChild);
            }
            thumbBox.className = 'dish-thumb-box has-emoji';
            thumbBox.removeAttribute('title');
            thumbBox.textContent = iconEmoji;
            thumbBox.onclick = null;

            const detailsEl = itemEl.querySelector('.item-details');
            if (detailsEl) {
                detailsEl.removeAttribute('onclick');
                detailsEl.onclick = null;
                detailsEl.style.cursor = 'default';
            }
        } else {
            if (thumbBox) thumbBox.remove();
            const detailsEl = itemEl.querySelector('.item-details');
            if (detailsEl) {
                detailsEl.removeAttribute('onclick');
                detailsEl.onclick = null;
                detailsEl.style.cursor = 'default';
            }
        }
    }

    // Toast visual para indicar que la página se refresca por cambios en la carta
    function showReloadToast() {
        let toast = document.getElementById('firebaseSyncToast');
        if (!toast) {
            toast = document.createElement('div');
            toast.id = 'firebaseSyncToast';
            toast.className = 'firebase-sync-toast';
            toast.innerHTML = '<span class="dot" style="width:8px;height:8px;background:#8cff00;border-radius:50%;display:inline-block;box-shadow:0 0 8px #8cff00;"></span> <span>⚡ Carta actualizada desde cocina. Actualizando...</span>';
            document.body.appendChild(toast);
        }
    }

    // Indicador visual discreto de carta conectada
    function showLiveSyncBadge() {
        const container = document.querySelector('.hero-content') || document.querySelector('.container') || document.body;
        if (!container || document.getElementById('liveSyncBadge')) return;
        const badge = document.createElement('div');
        badge.id = 'liveSyncBadge';
        badge.className = 'live-sync-indicator';
        badge.innerHTML = '<span class="dot"></span> <span>Carta Sincronizada en Vivo con Cocina</span>';
        badge.style.display = 'flex';
        badge.style.width = 'fit-content';
        badge.style.margin = '10px auto 4px auto';
        container.appendChild(badge);
    }

    // Lógica principal de sincronización
    function startRealtimeSync() {
        injectStyles();
        ensureDishPhotoModal();

        if (!window.firebase.apps.length) {
            window.firebase.initializeApp(FIREBASE_CONFIG);
        }

        const db = window.firebase.firestore();
        const currentCategory = detectCurrentCategory();

        showLiveSyncBadge();

        console.log("⚡ Bar Sergio's Realtime Sync iniciado. Categoría:", currentCategory || "GLOBAL");

        // Escuchar la colección 'menu' en tiempo real
        db.collection("menu").onSnapshot(function (snapshot) {
            console.log("📡 Cambio detectado en la carta desde Firebase Firestore (" + snapshot.docs.length + " platos recibidos)");

            // Huella digital de la carta para detectar modificaciones reales
            const currentFingerprint = snapshot.docs.map(function (d) {
                const data = d.data();
                return [
                    d.id,
                    data.updatedAt || 0,
                    data.price || 0,
                    data.isOutOfStock ? 1 : 0,
                    data.isAvailable !== false ? 1 : 0,
                    data.isPopular ? 1 : 0,
                    data.isNew ? 1 : 0,
                    data.name || '',
                    data.description || '',
                    data.category || '',
                    data.order !== undefined ? data.order : 0
                ].join(':');
            }).join('|');

            const isInitial = !window.__barSergiosInitialLoaded;
            const savedFingerprint = sessionStorage.getItem('barSergiosFingerprint');
            const hasChanged = (!isInitial && window.__barSergiosFingerprint && window.__barSergiosFingerprint !== currentFingerprint);

            window.__barSergiosFingerprint = currentFingerprint;
            sessionStorage.setItem('barSergiosFingerprint', currentFingerprint);
            window.__barSergiosInitialLoaded = true;

            if (!currentCategory) {
                // Página general / index
                if (hasChanged) {
                    showReloadToast();
                    setTimeout(function () { window.location.reload(); }, 600);
                }
                return;
            }

            const itemsList = document.querySelector('.items-list');
            if (!itemsList) return;

            // Extraer y ordenar los platos de la categoría actual autorizados por la App Admin
            const adminCategoryDocs = snapshot.docs
                .map(function (doc) {
                    const data = doc.data();
                    let orderNum = 0;
                    if (typeof data.order === 'number') {
                        orderNum = data.order;
                    } else if (data.order !== undefined && !isNaN(parseInt(data.order))) {
                        orderNum = parseInt(data.order);
                    } else {
                        orderNum = data.updatedAt || 0;
                    }

                    return {
                        id: doc.id,
                        name: data.name || '',
                        description: data.description || '',
                        price: (typeof data.price === 'number') ? data.price : parseFloat(data.price) || 0,
                        category: data.category || 'TAPAS',
                        iconEmoji: data.iconEmoji || '🍽️',
                        imageBase64: data.imageBase64 || '',
                        isPopular: data.isPopular === true,
                        isAvailable: data.isAvailable !== false,
                        isOutOfStock: data.isOutOfStock === true,
                        isNew: data.isNew === true,
                        allergens: Array.isArray(data.allergens) ? data.allergens : [],
                        spiceLevel: (typeof data.spiceLevel === 'number') ? data.spiceLevel : parseInt(data.spiceLevel) || 0,
                        order: orderNum,
                        updatedAt: data.updatedAt || 0
                    };
                })
                .filter(function (item) {
                    // Solo platos de la categoría actual y que estén activos en carta (isAvailable !== false)
                    return item.category === currentCategory && item.isAvailable;
                })
                .sort(function (a, b) {
                    const orderDiff = a.order - b.order;
                    if (orderDiff !== 0) return orderDiff;
                    return (a.updatedAt || 0) - (b.updatedAt || 0);
                });

            if (adminCategoryDocs.length === 0) {
                return;
            }

            // Identificar los elementos existentes en el DOM
            const existingDomItems = Array.from(itemsList.querySelectorAll('.menu-item'));
            const matchedDomElements = new Set();

            function findMatchingDomItem(adminItem) {
                const normAdmin = normalizeName(adminItem.name);
                const byId = document.getElementById('item_' + adminItem.id) || document.getElementById('live_item_' + adminItem.id);
                if (byId && !matchedDomElements.has(byId)) return byId;

                // Coincidencia exacta de nombre normalizado
                for (let i = 0; i < existingDomItems.length; i++) {
                    const el = existingDomItems[i];
                    if (matchedDomElements.has(el)) continue;
                    const nameEl = el.querySelector('.item-name .i18n') || el.querySelector('.item-name');
                    if (nameEl) {
                        const normDom = normalizeName(nameEl.textContent);
                        if (normDom === normAdmin) {
                            return el;
                        }
                    }
                }

                // Coincidencia parcial si no hay exacta
                for (let i = 0; i < existingDomItems.length; i++) {
                    const el = existingDomItems[i];
                    if (matchedDomElements.has(el)) continue;
                    const nameEl = el.querySelector('.item-name .i18n') || el.querySelector('.item-name');
                    if (nameEl) {
                        const normDom = normalizeName(nameEl.textContent);
                        if (normDom.length > 4 && normAdmin.length > 4 && (normDom.includes(normAdmin) || normAdmin.includes(normDom))) {
                            return el;
                        }
                    }
                }
                return null;
            }

            // Actualizar o crear cada plato autorizado por la App Admin
            adminCategoryDocs.forEach(function (adminItem) {
                let itemEl = findMatchingDomItem(adminItem);

                if (!itemEl) {
                    itemEl = document.createElement('article');
                    itemEl.className = 'menu-item';
                    itemEl.id = 'item_' + adminItem.id;
                    itemEl.innerHTML = `
                        <div class="item-details">
                            <h3 class="item-name"><span class="i18n" data-es="${escapeHtml(adminItem.name)}">${escapeHtml(adminItem.name)}</span></h3>
                            <p class="item-description"><span class="i18n" data-es="${escapeHtml(adminItem.description)}">${escapeHtml(adminItem.description)}</span></p>
                        </div>
                        <div class="item-right-col">
                            <div class="item-price">${adminItem.price.toFixed(2)} €</div>
                        </div>
                    `;
                    itemsList.appendChild(itemEl);
                } else {
                    itemEl.id = 'item_' + adminItem.id;
                }

                matchedDomElements.add(itemEl);
                itemEl.setAttribute('data-admin-synced', 'true');

                // 1. Nombre
                const nameEl = itemEl.querySelector('.item-name .i18n') || itemEl.querySelector('.item-name');
                if (nameEl && nameEl.textContent.trim() !== adminItem.name) {
                    nameEl.textContent = adminItem.name;
                    nameEl.setAttribute('data-es', adminItem.name);
                }

                // 2. Descripción
                const descEl = itemEl.querySelector('.item-description .i18n') || itemEl.querySelector('.item-description');
                if (descEl) {
                    descEl.textContent = adminItem.description;
                    descEl.setAttribute('data-es', adminItem.description);
                }

                // 3. Precio
                const priceEl = itemEl.querySelector('.item-price');
                if (priceEl) {
                    const priceFormatted = adminItem.price.toFixed(2) + " €";
                    if (!priceEl.textContent.includes(priceFormatted)) {
                        priceEl.textContent = priceFormatted;
                        priceEl.classList.remove('price-pulse-live');
                        void priceEl.offsetWidth;
                        priceEl.classList.add('price-pulse-live');
                    }
                }

                // 4. Badges (Agotado, Especialidad/Popular, Novedad)
                const titleHeader = itemEl.querySelector('.item-name');
                if (titleHeader) {
                    titleHeader.querySelectorAll('.badge-agotado-hoy, .badge-destacado-live, .badge-novedad-live').forEach(function (b) {
                        b.remove();
                    });

                    if (adminItem.isNew) {
                        const newBadge = document.createElement('span');
                        newBadge.className = 'badge-novedad-live';
                        newBadge.innerHTML = '✨ Novedad';
                        titleHeader.appendChild(newBadge);
                    }
                    if (adminItem.isPopular) {
                        const popBadge = document.createElement('span');
                        popBadge.className = 'badge-destacado-live';
                        popBadge.innerHTML = '⭐ Especialidad';
                        titleHeader.appendChild(popBadge);
                    }
                    if (adminItem.isOutOfStock) {
                        const stockBadge = document.createElement('span');
                        stockBadge.className = 'badge-agotado-hoy';
                        stockBadge.innerHTML = '⚡ Agotado hoy';
                        titleHeader.appendChild(stockBadge);
                    }
                }

                // 5. Estado agotado
                if (adminItem.isOutOfStock) {
                    itemEl.classList.add('item-agotado-hoy');
                } else {
                    itemEl.classList.remove('item-agotado-hoy');
                }

                // 6. Atributos para filtros de la web
                const allergensStr = adminItem.allergens.join(' ').toLowerCase();
                itemEl.setAttribute('data-gluten', allergensStr.includes('gluten') ? 'true' : 'false');
                itemEl.setAttribute('data-lacteos', (allergensStr.includes('lacteo') || allergensStr.includes('lácteo')) ? 'true' : 'false');
                itemEl.setAttribute('data-vegano', (allergensStr.includes('vegano') || adminItem.description.toLowerCase().includes('vegano')) ? 'true' : 'false');
                itemEl.setAttribute('data-spice', (adminItem.spiceLevel || 0).toString());
                itemEl.setAttribute('data-recomendado', adminItem.isPopular ? 'true' : 'false');

                // 7. Miniatura: Foto del Producto (ampliable) vs Icono Emoji (no ampliable)
                syncDishThumbnail(itemEl, adminItem);

                // Asegurar visible
                itemEl.style.display = '';
            });

            // 8. ELIMINAR del DOM cualquier plato que NO exista en la App Admin (platos borrados o desactivados)
            existingDomItems.forEach(function (el) {
                if (!matchedDomElements.has(el)) {
                    console.log("🗑️ Bar Sergio's Sync: Eliminando plato retirado en App Admin:", el.textContent.trim().slice(0, 35));
                    el.remove();
                }
            });

            // 9. ORDENACIÓN ESTRICTA: Reorganizar elementos en el DOM según el orden oficial de la App Admin
            adminCategoryDocs.forEach(function (adminItem) {
                const el = document.getElementById('item_' + adminItem.id);
                if (el && el.parentElement === itemsList) {
                    itemsList.appendChild(el);
                }
            });

            // 10. Re-aplicar idioma activo si existe setLang
            if (typeof window.setLang === 'function') {
                const curLang = localStorage.getItem('menuLang') || 'es';
                window.setLang(curLang);
            }

            // 11. Si hubo un cambio en caliente y se requiere refresco, avisar y refrescar suavemente
            if (hasChanged) {
                console.log("⚡ [Bar Sergio's] Cambio detectado en carta desde App Admin. Refrescando página en tiempo real...");
                showReloadToast();
                setTimeout(function () {
                    window.location.reload();
                }, 800);
            }
        }, function (error) {
            console.warn("Aviso Firebase Firestore Realtime (usando respaldo estático):", error.message);
        });
    }

    // Inicializar cuando el DOM esté listo
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', function () {
            ensureFirebaseLoaded(startRealtimeSync);
        });
    } else {
        ensureFirebaseLoaded(startRealtimeSync);
    }
})();
