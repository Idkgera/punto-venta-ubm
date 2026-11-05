# Publicación del proyecto en GitHub
El ZIP contiene un repositorio Git local con las ramas `main`, `development` y `qa`, con commits de creación, backend, frontend y QA.

1. Inicia sesión en https://github.com y crea un repositorio **vacío**, sin README ni .gitignore, llamado `punto-venta-ubm`.
2. Abre una terminal en la carpeta del proyecto extraído (debe incluir la carpeta oculta `.git`).
3. Ejecuta (sustituye TU_USUARIO):

```bash
git remote add origin https://github.com/TU_USUARIO/punto-venta-ubm.git
git push -u origin main
git push -u origin development
git push -u origin qa
```

Para consultar historial: `git log --all --graph --oneline --decorate`. Para consultar ramas: `git branch -a`.

No se incluye ni se sube la base de datos personal ni las imágenes cargadas: se crean de forma local durante la ejecución.
