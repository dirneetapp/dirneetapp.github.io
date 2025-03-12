document.getElementById('menu-toggle').addEventListener('click', function() {
    var menu = document.getElementById('menu');
    menu.classList.toggle('active');
});

document.getElementById('form-producto').addEventListener('submit', function(event) {
    event.preventDefault();
    var categoria = document.getElementById('categoria').value;
    var nombre = document.getElementById('nombre').value;
    var descripcion = document.getElementById('descripcion').value;
    var precio = document.getElementById('precio').value;

    var producto = document.createElement('div');
    producto.className = 'producto';
    producto.innerHTML = `<h3>${nombre}</h3><p>${descripcion}</p><p class="precio">${precio}€</p>`;

    document.getElementById(categoria).appendChild(producto);
});

document.getElementById('borrar-producto').addEventListener('click', function() {
    var categoria = document.getElementById('categoria').value;
    var productos = document.getElementById(categoria).getElementsByClassName('producto');
    if (productos.length > 0) {
        productos[productos.length - 1].remove();
    }
});
