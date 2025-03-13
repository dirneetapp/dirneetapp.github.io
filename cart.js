class Cart {
    constructor() {
        this.cart = JSON.parse(localStorage.getItem('cart')) || [];
        this.init();
    }

    init() {
        this.renderCart();
        this.addEventListeners();
    }

    addToCart(item) {
        const existing = this.cart.find(i => i.id === item.id);
        if (existing) {
            existing.quantity++;
        } else {
            this.cart.push({...item, quantity: 1});
        }
        this.saveCart();
        this.renderCart();
    }

    removeItem(id) {
        this.cart = this.cart.filter(item => item.id !== id);
        this.saveCart();
        this.renderCart();
    }

    updateQuantity(id, quantity) {
        const item = this.cart.find(i => i.id === id);
        if (item) {
            item.quantity = quantity;
            if (quantity <= 0) this.removeItem(id);
            this.saveCart();
            this.renderCart();
        }
    }

    saveCart() {
        localStorage.setItem('cart', JSON.stringify(this.cart));
    }

    renderCart() {
        const cartItems = document.getElementById('cart-items');
        const cartTotal = document.getElementById('cart-total');
        
        cartItems.innerHTML = '';
        let total = 0;

        this.cart.forEach(item => {
            total += item.price * item.quantity;
            
            const div = document.createElement('div');
            div.className = 'cart-item';
            div.innerHTML = `
                <div>
                    <h4>${item.name}</h4>
                    <p>${item.price.toFixed(2)}€</p>
                </div>
                <div class="item-controls">
                    <button onclick="cart.updateQuantity('${item.id}', ${item.quantity - 1})">-</button>
                    <span>${item.quantity}</span>
                    <button onclick="cart.updateQuantity('${item.id}', ${item.quantity + 1})">+</button>
                    <button onclick="cart.removeItem('${item.id}')">×</button>
                </div>
            `;
            cartItems.appendChild(div);
        });

        cartTotal.textContent = total.toFixed(2);
    }

    checkout() {
        const tableNumber = document.getElementById('table-number').value;
        if (!tableNumber) {
            alert('Por favor, indique el número de mesa');
            return;
        }
        
        const order = {
            table: tableNumber,
            items: this.cart,
            total: this.cart.reduce((sum, item) => sum + (item.price * item.quantity), 0)
        };

        alert(`Pedido enviado para la mesa ${tableNumber}\nTotal: ${order.total.toFixed(2)}€`);
        this.cart = [];
        this.saveCart();
        this.renderCart();
        document.getElementById('table-number').value = '';
    }

    addEventListeners() {
        document.querySelector('.cart-toggle').addEventListener('click', () => {
            document.querySelector('.cart-container').classList.toggle('active');
        });
    }
}

const cart = new Cart();