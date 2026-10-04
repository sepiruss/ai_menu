// Smart Digital Menu - Customer Frontend Application
// Phase 2 MVP Implementation with localStorage Cart

class MenuApp {
    constructor() {
        this.apiBase = 'http://localhost:8000/api/v1';
        this.sessionToken = null;
        this.restaurantId = null;
        this.branchId = null;
        this.tableId = null;
        this.categories = [];
        this.items = [];
        this.currentCategoryId = null;
        this.currentFilter = 'all';
        this.searchQuery = '';
        this.cart = this.loadCartFromStorage();
        
        this.init();
    }

    init() {
        // Check for URL params (QR code token)
        const urlParams = new URLSearchParams(window.location.search);
        const qrToken = urlParams.get('qr') || urlParams.get('token');
        
        if (qrToken) {
            this.resolveQR(qrToken);
        } else {
            this.showQRPage();
        }
        
        this.bindEvents();
        this.updateCartUI();
    }

    bindEvents() {
        // QR Page
        document.getElementById('enter-menu-btn')?.addEventListener('click', () => this.enterMenu());
        document.getElementById('scan-qr-btn')?.addEventListener('click', () => this.scanQR());
        
        // Menu Page
        document.getElementById('back-btn')?.addEventListener('click', () => this.showQRPage());
        document.getElementById('search-toggle')?.addEventListener('click', () => this.toggleSearch());
        document.getElementById('search-input')?.addEventListener('input', (e) => this.handleSearch(e.target.value));
        document.getElementById('close-search-modal')?.addEventListener('click', () => this.closeSearchModal());
        document.getElementById('search-modal-backdrop')?.addEventListener('click', () => this.closeSearchModal());
        
        // Filter chips
        document.querySelectorAll('.filter-chip').forEach(chip => {
            chip.addEventListener('click', () => this.setFilter(chip.dataset.filter));
        });
        
        // Category tabs (delegated)
        document.getElementById('category-tabs')?.addEventListener('click', (e) => {
            const tab = e.target.closest('[role="tab"]');
            if (tab) this.selectCategory(tab.dataset.categoryId);
        });
        
        // Modal
        document.getElementById('close-modal')?.addEventListener('click', () => this.closeItemModal());
        document.getElementById('modal-backdrop')?.addEventListener('click', () => this.closeItemModal());
        document.getElementById('add-to-cart-btn')?.addEventListener('click', () => this.addToCart());
        
        // Cart modal
        document.getElementById('cart-btn')?.addEventListener('click', () => this.openCartModal());
        document.getElementById('close-cart-modal')?.addEventListener('click', () => this.closeCartModal());
        document.getElementById('cart-modal-backdrop')?.addEventListener('click', () => this.closeCartModal());
        document.getElementById('checkout-btn')?.addEventListener('click', () => this.createOrder());
        document.getElementById('clear-cart-btn')?.addEventListener('click', () => this.clearCart());
        
        // Close modals on escape
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                this.closeItemModal();
                this.closeSearchModal();
                this.closeCartModal();
            }
        });
    }

    // Cart Storage
    loadCartFromStorage() {
        try {
            const stored = localStorage.getItem('menu_cart');
            if (stored) {
                const cart = JSON.parse(stored);
                // Verify cart belongs to current session
                if (cart.sessionToken === this.sessionToken) {
                    return cart;
                }
            }
        } catch (e) {
            console.warn('Failed to load cart:', e);
        }
        return { items: [], sessionToken: null };
    }

    saveCartToStorage() {
        this.cart.sessionToken = this.sessionToken;
        localStorage.setItem('menu_cart', JSON.stringify(this.cart));
        this.updateCartUI();
    }

    addToCartLocal(item, quantity = 1, selectedOptions = []) {
        const existingIndex = this.cart.items.findIndex(i => 
            i.menu_item_id === item.id && 
            JSON.stringify(i.selected_options) === JSON.stringify(selectedOptions)
        );
        
        if (existingIndex >= 0) {
            this.cart.items[existingIndex].quantity += quantity;
        } else {
            this.cart.items.push({
                menu_item_id: item.id,
                name: item.name,
                price_toman: item.price_toman,
                price_rial: item.price_rial,
                quantity: quantity,
                selected_options: selectedOptions,
                item_name_snapshot: item.name,
                options_price_adjustment_toman: 0,
                options_price_adjustment_rial: 0,
            });
        }
        this.saveCartToStorage();
        this.showToast(`${item.name} به سبد اضافه شد`, 'success');
    }

    updateCartItemQuantity(itemId, quantity) {
        const index = this.cart.items.findIndex(i => i.menu_item_id === itemId);
        if (index >= 0) {
            if (quantity <= 0) {
                this.cart.items.splice(index, 1);
            } else {
                this.cart.items[index].quantity = quantity;
            }
            this.saveCartToStorage();
        }
    }

    removeCartItem(itemId) {
        this.cart.items = this.cart.items.filter(i => i.menu_item_id !== itemId);
        this.saveCartToStorage();
    }

    clearCart() {
        this.cart.items = [];
        this.saveCartToStorage();
    }

    getCartSubtotal() {
        return this.cart.items.reduce((sum, item) => {
            const itemSubtotal = item.price_toman * item.quantity;
            return sum + itemSubtotal;
        }, 0);
    }

    // QR Code Resolution
    async resolveQR(token) {
        this.showLoading('در حال پردازش QR کد...');
        try {
            const response = await fetch(`${this.apiBase}/public/qr/${token}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ device_info: { userAgent: navigator.userAgent } })
            });
            
            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.message || 'QR کد نامعتبر است');
            }
            
            const data = await response.json();
            this.sessionToken = data.session_token;
            this.restaurantId = data.restaurant_id;
            this.branchId = data.branch_id;
            this.tableId = data.table_id;
            
            // Store in localStorage for persistence
            localStorage.setItem('menu_session', JSON.stringify({
                sessionToken: this.sessionToken,
                restaurantId: this.restaurantId,
                branchId: this.branchId,
                tableId: this.tableId
            }));
            
            // Clear old cart if different session
            if (this.cart.sessionToken !== this.sessionToken) {
                this.cart = { items: [], sessionToken: this.sessionToken };
            }
            
            await this.loadMenu();
        } catch (error) {
            this.hideLoading();
            this.showToast(error.message, 'error');
            this.showQRPage();
        }
    }

    async loadSessionFromStorage() {
        const stored = localStorage.getItem('menu_session');
        if (stored) {
            try {
                const data = JSON.parse(stored);
                this.sessionToken = data.sessionToken;
                this.restaurantId = data.restaurantId;
                this.branchId = data.branchId;
                this.tableId = data.tableId;
                return true;
            } catch (e) {
                localStorage.removeItem('menu_session');
            }
        }
        return false;
    }

    async enterMenu() {
        if (await this.loadSessionFromStorage()) {
            await this.loadMenu();
        } else {
            this.showToast('نشست منقضی شده، لطفاً مجدداً QR را اسکن کنید', 'error');
            this.showQRPage();
        }
    }

    scanQR() {
        this.showToast('برای اسکن مجدد، از برنامه دوربین استفاده کنید', 'info');
    }

    // Menu Loading
    async loadMenu() {
        this.showLoading('در حال بارگذاری منو...');
        try {
            const response = await this.apiRequest('GET', `/public/menu/${this.branchId}`);
            if (!response.ok) throw new Error('خطا در بارگذاری منو');
            
            const menu = await response.json();
            this.categories = menu.categories || [];
            this.renderCategories();
            this.selectCategory(this.categories[0]?.id || null);
            
            this.showMenuPage(menu);
        } catch (error) {
            this.hideLoading();
            this.showToast(error.message, 'error');
            this.showQRPage();
        }
    }

    // Rendering
    showQRPage() {
        document.getElementById('qr-page').classList.remove('hidden');
        document.getElementById('menu-page').classList.add('hidden');
        document.getElementById('search-modal').classList.add('hidden');
        document.getElementById('item-modal').classList.add('hidden');
        document.getElementById('cart-modal').classList.add('hidden');
    }

    showMenuPage(menu) {
        document.getElementById('qr-page').classList.add('hidden');
        document.getElementById('menu-page').classList.remove('hidden');
        
        // Update header info
        document.getElementById('menu-restaurant-name').textContent = menu.restaurant_name || 'رستوران';
        document.getElementById('menu-branch-name').textContent = menu.branch_name || 'شعبه';
        if (this.tableId) {
            document.getElementById('table-indicator').textContent = `میز ${this.tableId}`;
            document.getElementById('table-indicator').classList.remove('hidden');
        }
        
        this.hideLoading();
    }

    renderCategories() {
        const tabsContainer = document.getElementById('category-tabs');
        if (!tabsContainer) return;
        
        tabsContainer.innerHTML = '';
        
        // Get root categories
        const rootCategories = this.categories.filter(c => !c.parent_id);
        
        rootCategories.forEach((cat, index) => {
            const tab = document.createElement('button');
            tab.setAttribute('role', 'tab');
            tab.setAttribute('data-category-id', cat.id);
            tab.className = `px-4 py-2 rounded-full text-sm font-medium whitespace-nowrap transition-colors ${
                index === 0 ? 'bg-primary-500 text-white' : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            }`;
            tab.textContent = cat.name;
            tabsContainer.appendChild(tab);
        });
    }

    selectCategory(categoryId) {
        this.currentCategoryId = categoryId;
        
        // Update tabs
        document.querySelectorAll('#category-tabs [role="tab"]').forEach(tab => {
            const isActive = tab.dataset.categoryId == categoryId;
            tab.className = `px-4 py-2 rounded-full text-sm font-medium whitespace-nowrap transition-colors ${
                isActive ? 'bg-primary-500 text-white' : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            }`;
        });
        
        this.loadItems(categoryId);
    }

    async loadItems(categoryId) {
        const grid = document.getElementById('items-grid');
        const emptyState = document.getElementById('empty-state');
        
        if (!categoryId) {
            grid.innerHTML = '';
            emptyState.classList.remove('hidden');
            document.getElementById('empty-message').textContent = 'دسته‌بندی را انتخاب کنید';
            return;
        }
        
        grid.innerHTML = '<div class="col-span-full text-center py-8"><div class="w-8 h-8 border-3 border-primary-500 border-t-transparent rounded-full animate-spin mx-auto"></div></div>';
        emptyState.classList.add('hidden');
        
        try {
            const params = new URLSearchParams({
                category_id: categoryId,
                page: 1,
                page_size: 20
            });
            
            if (this.currentFilter === 'popular') params.append('is_popular', 'true');
            if (this.currentFilter === 'new') params.append('is_new', 'true');
            if (this.currentFilter === 'available') params.append('is_available', 'true');
            if (this.searchQuery) params.append('search', this.searchQuery);
            
            const response = await this.apiRequest('GET', `/public/menu/${this.branchId}/items?${params}`);
            if (!response.ok) throw new Error('خطا در بارگذاری آیتم‌ها');
            
            const data = await response.json();
            this.items = data.items || [];
            this.renderItems();
        } catch (error) {
            this.showToast(error.message, 'error');
            grid.innerHTML = '';
            emptyState.classList.remove('hidden');
            document.getElementById('empty-message').textContent = 'خطا در بارگذاری آیتم‌ها';
        }
    }

    renderItems() {
        const grid = document.getElementById('items-grid');
        const emptyState = document.getElementById('empty-state');
        
        if (!this.items.length) {
            grid.innerHTML = '';
            emptyState.classList.remove('hidden');
            document.getElementById('empty-message').textContent = 'هیچ آیتمی در این دسته‌بندی یافت نشد';
            return;
        }
        
        emptyState.classList.add('hidden');
        grid.innerHTML = this.items.map(item => this.createItemCard(item)).join('');
        
        // Add click listeners
        grid.querySelectorAll('.item-card').forEach(card => {
            card.addEventListener('click', () => this.openItemModal(parseInt(card.dataset.itemId)));
        });
    }

    createItemCard(item) {
        const isPopular = item.is_popular;
        const isNew = item.is_new;
        const imageUrl = item.image_url || 'https://via.placeholder.com/300x200?text=No+Image';
        
        return `
            <article class="item-card bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden hover:shadow-md transition-shadow cursor-pointer" data-item-id="${item.id}">
                <div class="relative h-40 bg-gray-100 overflow-hidden">
                    <img src="${imageUrl}" alt="${this.escapeHtml(item.name)}" class="w-full h-full object-cover">
                    ${isPopular ? '<span class="absolute top-2 right-2 bg-red-500 text-white text-xs px-2 py-0.5 rounded-full">محبوب</span>' : ''}
                    ${item.is_new ? '<span class="absolute top-2 right-2 bg-green-500 text-white text-xs px-2 py-0.5 rounded-full">جدید</span>' : ''}
                    ${!item.is_available ? '<span class="absolute top-2 right-2 bg-gray-500 text-white text-xs px-2 py-0.5 rounded-full">ناموجود</span>' : ''}
                </div>
                <div class="p-4">
                    <h3 class="font-semibold text-gray-800 mb-1 line-clamp-1">${this.escapeHtml(item.name)}</h3>
                    ${item.description ? `<p class="text-gray-600 text-sm mb-2 line-clamp-2">${this.escapeHtml(item.description)}</p>` : ''}
                    <div class="flex items-center justify-between">
                        <div>
                            <span class="text-lg font-bold text-primary-600">${this.formatPrice(item.price_toman)} تومان</span>
                            ${item.price_rial && item.price_rial > 0 ? `<span class="text-xs text-gray-500 line-through ml-2">${this.formatPrice(item.price_rial)} ریال</span>` : ''}
                        </div>
                        ${item.allergens_tags && item.allergens_tags.length > 0 ? `
                            <div class="flex flex-wrap gap-1 mt-2">
                                ${item.allergens_tags.slice(0, 3).map(tag => `<span class="text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded">${this.escapeHtml(tag)}</span>`).join('')}
                                ${item.allergens_tags.length > 3 ? `<span class="text-xs bg-gray-100 text-gray-500 px-2 py-0.5 rounded">+${item.allergens_tags.length - 3}</span>` : ''}
                            </div>
                        ` : ''}
                    </div>
                </div>
            </article>
        `;
    }

    // Item Modal
    openItemModal(itemId) {
        const item = this.items.find(i => i.id === itemId);
        if (!item) return;
        
        document.getElementById('modal-name').textContent = item.name;
        document.getElementById('modal-description').textContent = item.description || 'توضیحات موجود نیست';
        document.getElementById('modal-price-toman').textContent = this.formatPrice(item.price_toman) + ' تومان';
        document.getElementById('modal-price-rial').textContent = item.price_rial ? this.formatPrice(item.price_rial) + ' ریال' : '';
        document.getElementById('modal-price-rial').style.display = item.price_rial ? 'inline' : 'none';
        document.getElementById('modal-image').src = item.image_url || 'https://via.placeholder.com/400x300?text=No+Image';
        document.getElementById('modal-image').alt = item.name;
        
        // Badges
        const badgesContainer = document.getElementById('modal-badges');
        badgesContainer.innerHTML = '';
        if (item.is_popular) {
            badgesContainer.innerHTML += '<span class="bg-red-500 text-white text-xs px-2 py-0.5 rounded-full">محبوب</span>';
        }
        if (item.is_new) {
            badgesContainer.innerHTML += '<span class="bg-green-500 text-white text-xs px-2 py-0.5 rounded-full">جدید</span>';
        }
        if (!item.is_available) {
            badgesContainer.innerHTML += '<span class="bg-gray-500 text-white text-xs px-2 py-0.5 rounded-full">ناموجود</span>';
        }
        
        // Allergens
        const allergensContainer = document.getElementById('modal-allergens');
        if (item.allergens_tags && item.allergens_tags.length > 0) {
            allergensContainer.innerHTML = `
                <div class="flex flex-wrap gap-1">
                    ${item.allergens_tags.map(tag => `<span class="text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded">${this.escapeHtml(tag)}</span>`).join('')}
                </div>
            `;
        } else {
            allergensContainer.innerHTML = '';
        }
        
        // Options
        const optionsContainer = document.getElementById('modal-options');
        if (item.options && item.options.length > 0) {
            optionsContainer.innerHTML = item.options.map(opt => `
                <div class="flex items-center justify-between p-3 bg-gray-50 rounded-xl">
                    <div>
                        <p class="font-medium text-gray-800">${this.escapeHtml(opt.name)}</p>
                        ${opt.options_config && opt.options_config.description ? `<p class="text-sm text-gray-500">${this.escapeHtml(opt.options_config.description)}</p>` : ''}
                    </div>
                    <div class="flex items-center gap-2">
                        ${opt.price_adjustment_toman > 0 ? `<span class="text-sm font-medium text-primary-600">+${this.formatPrice(opt.price_adjustment_toman)} تومان</span>` : '<span class="text-sm text-gray-500">بدون هزینه اضافی</span>'}
                        ${opt.is_required ? '<span class="text-xs bg-red-100 text-red-700 px-2 py-0.5 rounded">الزامی</span>' : ''}
                    </div>
                </div>
            `).join('');
        } else {
            optionsContainer.innerHTML = '<p class="text-gray-500 text-sm">گزینه اضافی وجود ندارد</p>';
        }
        
        // Store current item for add to cart
        this.currentModalItem = item;
        
        document.getElementById('item-modal').classList.remove('hidden');
        document.body.style.overflow = 'hidden';
    }

    closeItemModal() {
        document.getElementById('item-modal').classList.add('hidden');
        document.body.style.overflow = '';
    }

    // Search
    toggleSearch() {
        const searchBar = document.getElementById('search-bar');
        if (searchBar.classList.contains('hidden')) {
            searchBar.classList.remove('hidden');
            document.getElementById('search-input').focus();
        } else {
            searchBar.classList.add('hidden');
            document.getElementById('search-input').value = '';
            this.handleSearch('');
        }
    }

    handleSearch(query) {
        this.searchQuery = query.trim();
        if (this.searchQuery.length >= 2) {
            this.performSearch(this.searchQuery);
        } else {
            this.closeSearchModal();
            this.loadItems(this.currentCategoryId);
        }
    }

    async performSearch(query) {
        document.getElementById('search-modal').classList.remove('hidden');
        document.getElementById('search-results').innerHTML = '<div class="text-center py-8"><div class="w-8 h-8 border-3 border-primary-500 border-t-transparent rounded-full animate-spin mx-auto"></div></div>';
        
        try {
            const response = await this.apiRequest('POST', `/public/menu/${this.branchId}/search`, {
                query,
                page: 1,
                page_size: 20
            });
            
            if (!response.ok) throw new Error('خطا در جستجو');
            
            const data = await response.json();
            this.renderSearchResults(data.items || []);
        } catch (error) {
            document.getElementById('search-results').innerHTML = `<p class="text-center text-gray-500 py-8">${error.message}</p>`;
        }
    }

    renderSearchResults(items) {
        const container = document.getElementById('search-results');
        if (!items.length) {
            container.innerHTML = '<p class="text-center text-gray-500 py-8">هیچ نتیجه‌ای یافت نشد</p>';
            return;
        }
        
        container.innerHTML = items.map(item => `
            <button class="search-result-item w-full text-right p-3 rounded-xl hover:bg-gray-50 transition-colors" data-item-id="${item.id}">
                <div class="flex items-center gap-3">
                    <img src="${item.image_url || 'https://via.placeholder.com/60x60?text=No+Image'}" alt="${this.escapeHtml(item.name)}" class="w-12 h-12 rounded-xl object-cover">
                    <div class="flex-1">
                        <p class="font-medium text-gray-800">${this.escapeHtml(item.name)}</p>
                        <p class="text-sm text-primary-600 font-semibold">${this.formatPrice(item.price_toman)} تومان</p>
                    </div>
                </div>
            </button>
        `).join('');
        
        container.querySelectorAll('.search-result-item').forEach(btn => {
            btn.addEventListener('click', () => {
                this.closeSearchModal();
                this.openItemModal(parseInt(btn.dataset.itemId));
            });
        });
    }

    closeSearchModal() {
        document.getElementById('search-modal').classList.add('hidden');
        document.getElementById('search-bar').classList.add('hidden');
        document.getElementById('search-input').value = '';
        this.searchQuery = '';
    }

    // Filter
    setFilter(filter) {
        this.currentFilter = filter;
        document.querySelectorAll('.filter-chip').forEach(chip => {
            const isActive = chip.dataset.filter === filter;
            chip.className = `filter-chip px-4 py-2 rounded-full text-sm font-medium whitespace-nowrap ${isActive ? 'bg-primary-500 text-white' : 'bg-gray-100 text-gray-700 hover:bg-gray-200'}`;
        });
        this.loadItems(this.currentCategoryId);
    }

    // Cart Methods
    addToCart() {
        if (!this.currentModalItem) return;
        
        const item = this.currentModalItem;
        // For now, add without options (options UI can be added later)
        this.addToCartLocal(item, 1, []);
        this.closeItemModal();
    }

    openCartModal() {
        this.renderCartModal();
        document.getElementById('cart-modal').classList.remove('hidden');
        document.body.style.overflow = 'hidden';
    }

    closeCartModal() {
        document.getElementById('cart-modal').classList.add('hidden');
        document.body.style.overflow = '';
    }

    renderCartModal() {
        const container = document.getElementById('cart-items');
        const subtotal = this.getCartSubtotal();
        
        if (!this.cart.items.length) {
            container.innerHTML = `
                <div class="text-center py-12">
                    <svg class="w-16 h-16 text-gray-300 mx-auto mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M16 11V7a2 2 0 00-2-2H5a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2v-14z"></path>
                    </svg>
                    <p class="text-gray-500 text-lg">سبد خرید خالی است</p>
                    <p class="text-gray-400 text-sm mt-2">آیتم‌هایی از منو اضافه کنید</p>
                </div>
            `;
        } else {
            container.innerHTML = this.cart.items.map(item => `
                <div class="flex items-center gap-3 p-3 bg-gray-50 rounded-xl" data-item-id="${item.menu_item_id}">
                    <div class="w-16 h-16 bg-gray-100 rounded-xl flex-shrink-0 overflow-hidden">
                        <div class="w-full h-full bg-gray-200 flex items-center justify-center">
                            <svg class="w-8 h-8 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.85 1.063M21 12c0 .557-.08 1.107-.229 1.62M18 12c0-.557.08-1.107.229-1.62M15 12c0 .557-.08 1.107-.229 1.62M12 12c0-.557.08-1.107.229-1.62M9 12c0 .557-.08 1.107-.229 1.62M6 12c0-.557.08-1.107.229-1.62M3 12c0 .557-.08 1.107-.229 1.62"></path>
                            </svg>
                        </div>
                    </div>
                    <div class="flex-1 min-w-0">
                        <h4 class="font-medium text-gray-800 truncate">${this.escapeHtml(this.cart.items.find(i => i.menu_item_id === this.cart.items.find(i => i.menu_item_id === item.menu_item_id)?.menu_item_id)?.name || 'آیتم')}</h4>
                        <p class="text-sm text-primary-600 font-semibold">${this.formatPrice(item.price_toman)} تومان</p>
                    </div>
                    <div class="flex items-center gap-2">
                        <button class="qty-btn w-8 h-8 rounded-lg bg-gray-100 text-gray-700 hover:bg-gray-200 flex items-center justify-center" data-action="decrease" data-item-id="${item.menu_item_id}">
                            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20 12H4"></path></svg>
                        </button>
                        <span class="w-10 text-center font-medium text-gray-800">${item.quantity}</span>
                        <button class="qty-btn w-8 h-8 rounded-lg bg-gray-100 text-gray-700 hover:bg-gray-200 flex items-center justify-center" data-action="increase" data-item-id="${item.menu_item_id}">
                            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"></path></svg>
                        </button>
                        <button class="ml-2 p-2 rounded-lg text-gray-400 hover:text-red-500 hover:bg-red-50" data-action="remove" data-item-id="${item.menu_item_id}">
                            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path></svg>
                        </button>
                    </div>
                </div>
            `).join('');
        }
        
        // Update subtotal
        document.getElementById('cart-subtotal').textContent = this.formatPrice(this.getCartSubtotal()) + ' تومان';
        
        // Bind quantity buttons
        document.querySelectorAll('.qty-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const itemId = parseInt(btn.dataset.itemId);
                const action = btn.dataset.action;
                const item = this.cart.items.find(i => i.menu_item_id === itemId);
                if (!item) return;
                
                if (action === 'increase') {
                    this.updateCartItemQuantity(itemId, item.quantity + 1);
                } else if (action === 'decrease') {
                    this.updateCartItemQuantity(itemId, item.quantity - 1);
                } else if (action === 'remove') {
                    this.removeCartItem(itemId);
                }
                this.renderCartModal();
            });
        });
    }

    updateCartUI() {
        const count = this.cart.items.reduce((sum, item) => sum + item.quantity, 0);
        const badge = document.getElementById('cart-badge');
        if (badge) {
            if (count > 0) {
                badge.textContent = count;
                badge.classList.remove('hidden');
            } else {
                badge.classList.add('hidden');
            }
        }
    }

    async createOrder() {
        if (!this.cart.items.length) {
            this.showToast('سبد خرید خالی است', 'warning');
            return;
        }
        
        this.showLoading('در حال ثبت سفارش...');
        try {
            const response = await this.apiRequest('POST', '/public/orders', {
                idempotency_key: `order-${Date.now()}`,
                customer_note: ''
            });
            
            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.message || 'خطا در ثبت سفارش');
            }
            
            const order = await response.json();
            this.showToast(`سفارش ${order.order_number} ثبت شد`, 'success');
            this.clearCart();
            this.closeCartModal();
            
            // Show order confirmation
            this.showOrderConfirmation(order);
        } catch (error) {
            this.hideLoading();
            this.showToast(error.message, 'error');
        }
    }

    showOrderConfirmation(order) {
        // Create a confirmation modal
        const modal = document.createElement('div');
        modal.id = 'order-confirmation-modal';
        modal.className = 'fixed inset-0 z-50 overflow-y-auto';
        modal.innerHTML = `
            <div class="flex min-h-full items-center justify-center p-4">
                <div class="fixed inset-0 bg-black/50 backdrop-blur-sm" id="order-modal-backdrop"></div>
                <div class="relative bg-white rounded-2xl shadow-xl max-w-md w-full">
                    <div class="p-6 text-center">
                        <div class="w-20 h-20 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
                            <svg class="w-10 h-10 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path>
                            </svg>
                        </div>
                        <h2 class="text-2xl font-bold text-gray-800 mb-2">سفارش ثبت شد</h2>
                        <p class="text-gray-600 mb-4">شماره سفارش: <span class="font-bold text-primary-600">${order.order_number}</span></p>
                        <p class="text-gray-600 mb-6">مبلغ کل: <span class="font-bold text-primary-600">${this.formatPrice(order.total_toman)} تومان</span></p>
                        <button id="close-order-modal" class="w-full py-3 px-6 bg-primary-500 text-white font-semibold rounded-xl hover:bg-primary-600 transition-colors shadow-lg">
                            بازگشت به منو
                        </button>
                    </div>
                </div>
            </div>
        `;
        document.body.appendChild(modal);
        document.body.style.overflow = 'hidden';
        
        document.getElementById('close-order-modal')?.addEventListener('click', () => {
            modal.remove();
            document.body.style.overflow = '';
        });
        document.getElementById('order-modal-backdrop')?.addEventListener('click', () => {
            modal.remove();
            document.body.style.overflow = '';
        });
    }

    // Toast
    showToast(message, type = 'info') {
        const container = document.getElementById('toast-container');
        const toast = document.createElement('div');
        const colors = {
            info: 'bg-blue-500',
            success: 'bg-green-500',
            error: 'bg-red-500',
            warning: 'bg-yellow-500'
        };
        
        toast.className = `px-4 py-3 rounded-xl shadow-lg text-white text-sm font-medium animate-slide-up ${colors[type] || colors.info}`;
        toast.textContent = message;
        
        container.appendChild(toast);
        
        setTimeout(() => {
            toast.classList.add('animate-fade-out');
            setTimeout(() => toast.remove(), 300);
        }, 4000);
    }

    // Loading
    showLoading(text = 'در حال بارگذاری...') {
        document.getElementById('loading-text').textContent = text;
        document.getElementById('loading-overlay').classList.remove('hidden');
    }

    hideLoading() {
        document.getElementById('loading-overlay').classList.add('hidden');
    }

    // API
    async apiRequest(method, endpoint, body = null) {
        const headers = {
            'Content-Type': 'application/json',
            'X-Session-Token': this.sessionToken || ''
        };
        
        const options = { method, headers };
        if (body) options.body = JSON.stringify(body);
        
        return fetch(`${this.apiBase}${endpoint}`, options);
    }

    // Utilities
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    formatPrice(price) {
        return new Intl.NumberFormat('fa-IR').format(price);
    }
}

// Initialize app when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.menuApp = new MenuApp();
});