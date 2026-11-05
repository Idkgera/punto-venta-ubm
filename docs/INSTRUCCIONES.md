# Entrega y pruebas

## Requisitos cubiertos
- Inicio de sesión obligatorio, credenciales verificadas con hash.
- Registro de productos con nombre, descripción, marca, precio, stock e imagen.
- Tabla actualizada al guardar productos, sin recargar la página.
- Búsqueda de productos por nombre, marca o descripción.
- Confirmación de ventas mediante ventana modal (no redirección).
- Descuento automático y seguro de existencias; registro de ventas y detalle.
- Historial de ventas, fecha, usuario y total.
- SQLite con cuatro tablas relacionadas (ver DBML).
- Flask como framework web.
- Ramas de Git `main`, `development` y `qa` con historial de commits.

## Instrucciones de uso
1. Ejecuta `INSTALAR_Y_EJECUTAR.bat`.
2. Entra con `admin` / `Admin123!` y cambia la contraseña desde el menú de usuario.
3. Registra un producto con precio > 0 y stock >= 0; agrega una imagen opcional JPG/PNG/WEBP.
4. Revisa que el nuevo producto aparezca automáticamente en la tabla.
5. Pulsa **Vender**, selecciona cantidad, confirma en el modal y verifica la reducción del stock.
6. Abre **Ventas** para consultar el historial.

## Pruebas automatizadas
```bash
.venv\Scripts\python.exe -m pytest -v
```

## Recomendaciones
El servidor de ejecución es local (127.0.0.1). Sistema académico: para ponerlo en internet necesitas HTTPS, gestión profesional de secretos, copias de seguridad y un servidor apropiado. No almacenar datos de tarjetas.
