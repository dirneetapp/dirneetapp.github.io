/**
 * Bar Sergio's - Realtime Firebase Firestore Carta Synchronizer
 * Sincronización en tiempo real entre la App Admin, App Cliente y la Web (GitHub Pages / dirneetapp.github.io)
 * Incluye soporte en vivo para Icono Emoji vs. Foto del Producto con visor ampliado y descripción debajo.
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
        const path = window.location.pathname.toLowerCase();
        if (path.includes('desayunos')) return 'DESAYUNOS';
        if (path.includes('bocadillos')) return 'BOCADILLOS';
        if (path.includes('vermuts')) return 'VERMUTS';
        if (path.includes('tapas')) return 'TAPAS';
        if (path.includes('torradas')) return 'TORRADAS';
        if (path.includes('tablas')) return 'TABLAS';
        if (path.includes('platos') || path.includes('especiales')) return 'PLATOS_ESPECIALES';
        if (path.includes('arroz')) return 'ARROZ';
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

    // Estilos visuales para elementos sincronizados (miniaturas, modal de foto con descripción, agotados)
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

    // Actualiza o inserta la miniatura (Foto pulsable vs Icono Emoji no pulsable) en un .menu-item
    function syncDishThumbnail(itemEl, firestoreData) {
        const photoDataUrl = toDataUrl(firestoreData.imageBase64);
        const iconEmoji = (firestoreData.iconEmoji && firestoreData.iconEmoji.trim()) ? firestoreData.iconEmoji.trim() : '';

        // Ocultar imagen estática antigua si existiera para evitar duplicados
        const legacyImg = itemEl.querySelector('img.item-image');
        if (legacyImg) {
            legacyImg.style.display = 'none';
        }

        let thumbBox = itemEl.querySelector('.dish-thumb-box');

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
                const priceText = (typeof firestoreData.price === 'number')
                    ? firestoreData.price.toFixed(2).replace('.', ',') + ' €'
                    : '';
                openDishPhotoModal(
                    photoDataUrl,
                    firestoreData.name || '',
                    priceText,
                    firestoreData.description || ''
                );
            };
        } else if (iconEmoji) {
            if (!thumbBox) {
                thumbBox = document.createElement('div');
                itemEl.insertBefore(thumbBox, itemEl.firstChild);
            }
            thumbBox.className = 'dish-thumb-box has-emoji';
            thumbBox.removeAttribute('title');
            thumbBox.textContent = iconEmoji;
            // El icono emoji NO es pulsable
            thumbBox.onclick = null;
        } else if (thumbBox) {
            thumbBox.remove();
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

            const itemsMap = new Map();
            snapshot.docs.forEach(function (doc) {
                const data = doc.data();
                const normName = normalizeName(data.name);
                itemsMap.set(normName, data);
            });

            // 1. Actualizar elementos existentes en la página
            const domItems = document.querySelectorAll('.menu-item');
            const matchedNormalizedNames = new Set();

            domItems.forEach(function (itemEl) {
                const nameEl = itemEl.querySelector('.item-name .i18n') || itemEl.querySelector('.item-name');
                if (!nameEl) return;

                const rawName = nameEl.textContent.trim();
                const normName = normalizeName(rawName);

                // Buscar por coincidencia exacta o inclusiva
                let firestoreData = itemsMap.get(normName);
                if (!firestoreData) {
                    for (const [k, v] of itemsMap.entries()) {
                        if (k === normName || normName.includes(k) || k.includes(normName)) {
                            firestoreData = v;
                            matchedNormalizedNames.add(k);
                            break;
                        }
                    }
                } else {
                    matchedNormalizedNames.add(normName);
                }

                if (!firestoreData) return;

                // --- ACTUALIZAR FOTO DEL PRODUCTO (PULSABLE) O ICONO EMOJI (NO PULSABLE) ---
                syncDishThumbnail(itemEl, firestoreData);

                // --- ACTUALIZAR PRECIO ---
                const priceEl = itemEl.querySelector('.item-price');
                if (priceEl && typeof firestoreData.price === 'number') {
                    const newPriceFormatted = firestoreData.price.toFixed(2) + " €";
                    if (!priceEl.textContent.includes(newPriceFormatted)) {
                        priceEl.textContent = newPriceFormatted;
                        priceEl.classList.remove('price-pulse-live');
                        void priceEl.offsetWidth; // reiniciar animación
                        priceEl.classList.add('price-pulse-live');
                    }
                }

                // --- ACTUALIZAR AGOTADO HOY ---
                const isOutOfStock = firestoreData.isOutOfStock === true;
                const existingAgotadoBadge = itemEl.querySelector('.badge-agotado-hoy');
                const cartBtn = itemEl.querySelector('.btn-add-cart') || itemEl.querySelector('.cart-add-row');

                if (isOutOfStock) {
                    itemEl.classList.add('item-agotado-hoy');
                    if (cartBtn) cartBtn.style.display = 'none';

                    if (!existingAgotadoBadge) {
                        const titleEl = itemEl.querySelector('.item-name');
                        if (titleEl) {
                            const badge = document.createElement('span');
                            badge.className = 'badge-agotado-hoy';
                            badge.innerHTML = '⚡ Agotado hoy';
                            titleEl.appendChild(badge);
                        }
                    }
                } else {
                    itemEl.classList.remove('item-agotado-hoy');
                    if (existingAgotadoBadge) existingAgotadoBadge.remove();
                    if (cartBtn) cartBtn.style.display = '';
                }

                // --- ACTUALIZAR DISPONIBILIDAD EN CARTA ---
                if (firestoreData.isAvailable === false) {
                    itemEl.style.display = 'none';
                } else if (itemEl.style.display === 'none' && !isOutOfStock) {
                    itemEl.style.display = '';
                }

                // --- ACTUALIZAR DESTACADO / ESPECIALIDAD ---
                const isPopular = firestoreData.isPopular === true;
                let existingPopularBadge = itemEl.querySelector('.badge-destacado-live');
                if (isPopular) {
                    if (!existingPopularBadge && !itemEl.querySelector("[title='Especialidad']")) {
                        const titleEl = itemEl.querySelector('.item-name');
                        if (titleEl) {
                            const badge = document.createElement('span');
                            badge.className = 'badge-destacado-live';
                            badge.innerHTML = '⭐ Especialidad';
                            titleEl.appendChild(badge);
                        }
                    }
                } else if (existingPopularBadge) {
                    existingPopularBadge.remove();
                }

                // --- ACTUALIZAR DESCRIPCIÓN ---
                if (firestoreData.description && firestoreData.description.trim()) {
                    const descEl = itemEl.querySelector('.item-description .i18n') || itemEl.querySelector('.item-description');
                    if (descEl && descEl.textContent.trim() !== firestoreData.description.trim()) {
                        descEl.textContent = firestoreData.description.trim();
                    }
                }
            });

            // 2. Si hay platos nuevos creados en la App Admin que pertenecen a esta categoría y no existen en el HTML
            if (currentCategory) {
                const itemsList = document.querySelector('.items-list');
                if (itemsList) {
                    snapshot.docs.forEach(function (doc) {
                        const data = doc.data();
                        if (data.category === currentCategory && data.isAvailable !== false) {
                            const normName = normalizeName(data.name);
                            if (!matchedNormalizedNames.has(normName)) {
                                let existingLiveArticle = document.getElementById('live_item_' + doc.id);
                                if (!existingLiveArticle) {
                                    console.log("➕ Añadiendo plato nuevo en directo:", data.name);
                                    const newArticle = document.createElement('article');
                                    newArticle.className = 'menu-item item-nuevo';
                                    newArticle.id = 'live_item_' + doc.id;
                                    newArticle.innerHTML = `
                                        <div class="item-details">
                                            <h3 class="item-name">
                                                <span>${data.name}</span>
                                                <span style="background: linear-gradient(135deg, #8cff00 0%, #10b981 100%); color: #000; font-size:0.7rem; padding: 2px 8px; border-radius: 10px; margin-left: 5px; vertical-align: middle; font-weight: bold;">✨ Nuevo</span>
                                                ${data.isOutOfStock ? '<span class="badge-agotado-hoy">⚡ Agotado hoy</span>' : ''}
                                            </h3>
                                            <p class="item-description"><span>${data.description || ''}</span></p>
                                        </div>
                                        <div class="item-right-col">
                                            <div class="item-price">${(data.price || 0).toFixed(2)} €</div>
                                        </div>
                                    `;
                                    if (data.isOutOfStock) {
                                        newArticle.classList.add('item-agotado-hoy');
                                    }
                                    syncDishThumbnail(newArticle, data);
                                    itemsList.appendChild(newArticle);
                                } else {
                                    syncDishThumbnail(existingLiveArticle, data);
                                }
                            }
                        }
                    });
                }
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
