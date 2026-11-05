# Registro de avances y QA

## Creación
- Estructura, dependencias y documentación inicial.

## Development
- Backend: conexión SQLite, acceso con usuario/contraseña y hash, CSRF.
- Backend: catálogo, guardado de imágenes, control de inventario, ventas transaccionales.
- Frontend: panel responsive, búsqueda, vista previa de imágenes, actualización dinámica y modal de venta.

## QA: observaciones y pruebas propuestas
- Acceso sin sesión debe ser rechazado.
- Rechazar precios negativos y stock negativo.
- Rechazar archivos que no sean imágenes válidas.
- Impedir ventas por encima de existencias.
- Al vender, confirmar que se descuente el inventario.
- Actualizar stock inmediatamente tras confirmar.

Las observaciones quedan reflejadas en pruebas automáticas en `tests/test_app.py`. La ejecución de pruebas en Windows se realiza con `pytest -v`; no se declara una ejecución local exitosa sin verificarlas.
