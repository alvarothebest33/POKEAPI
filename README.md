# Pokédex API

## Descripción
Esto es una FastAPI para buscar pokemon, crearte tu propia pokedex, crearte 
tu equipo de batalla soñado y modificarlo cuando quieras. Además, podras descargar tus cartas pokemon y tus
tu PDF de cada equipo.
## Instalación
Pasos para instalarlo:
1. Clonar el repositorio.
2. Crear el entorno virtual: `uv venv`
3. Activar el entorno: `.\.venv\Scripts\activate`
4. Instalar dependencias: `uv pip install -r requirements.txt`

## Preguntas a responder en la práctica
**¿Por qué diferentes límites?**

*En endpoints publicos:*
Cada vez que hacemos un registro tenemos que realizar muchas cosas, como el hasing
 o añadir en la base de datos, lo que es un proceso costoso para el servidor.
De esta manera, si alguien quiere meter bots o hacer un uso indebido de la API,
no podrá hacerlo de forma masiva, ya que le pondremos limites muy estrictos

*En endpoints que llamen a la API externa:*
Consiguen proteger a la API externa de no ser bombardeada con nuestras peticiones de nuestra API.

*En endpoints autenticados*
El cambio es que al necesitar hacer loggin le damos más confianza al usuario ya que se ha tenido
que loggear. Le damos más beneficios / libertad.

**¿Cómo protege esto tu API?**
Te protege de que te tumben el servidor con muchas peticiones (DDoS) y
evita que alguien intente descargar tu base de datos.

**¿Qué pasa si un usuario excede el límite?**
Se detiene la petición y le envia un 429 "too many requests", no dejándole realizar más peticiones hasta que se cumpla el tiempo límite.




## Configuración
Crear un archivo `.env` en la raíz del proyecto con las siguientes variables:
```ini
SECRET_KEY="tu-clave-secreta-aqui"
