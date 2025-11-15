# Consideraciones de Seguridad

## Autenticación

* **Implementación:** Se utiliza autenticación basada en JSON Web Tokens (JWT).
* **Expiración:** Los tokens de acceso (`access_token`) expiran a las 24 horas, forzando al usuario a volver a autenticarse.

## Contraseñas

* **Hashing:** Las contraseñas NO se almacenan en texto plano. Se utiliza el algoritmo `pbkdf2_sha256` (gestionado por `passlib`) para hashearlas.
* **Política:** Se requiere una contraseña de mínimo 8 caracteres, con al menos un número y una mayúscula. Esto se valida en el schema `UserCreate`.

## Rate Limiting

* **Implementación:** Se usa `slowapi` para limitar peticiones.
* **Justificación:** Se aplican límites estrictos a endpoints públicos y costosos (como `/register` y `/login`) para prevenir ataques de fuerza bruta y DDoS. Los endpoints de API externa (`/pokemon/search`) tienen límites moderados para proteger el servicio externo. Los endpoints privados (`/pokedex`) son más permisivos.

## CORS

* **Implementación:** Se usa el middleware de CORS de FastAPI.
* **Orígenes:** Solo se permiten orígenes explícitos (`localhost:3000`, `localhost:5173` y el dominio de producción `https://tu-dominio.com`), siguiendo una política de whitelist.

## Variables de Entorno

* **Información Sensible:** La `SECRET_KEY` (usada para firmar los JWT) se carga desde un archivo `.env`.
* **Protección:** El archivo `.env` está incluido en `.gitignore` y NO se sube al repositorio de Git.

