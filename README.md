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



## Configuración
Crear un archivo `.env` en la raíz del proyecto con las siguientes variables:
```ini
SECRET_KEY="tu-clave-secreta-aqui"
```
## Ejecucion
Para arrancar el proyecto tienes dos opciones, hacerlo desde la carpeta original (creandose tu base de datos en la carpeta original)
o hacerlo desde el main(creando la base de datos dentro de /app). 


Desde la carpeta original:
```ini
uvicorn app.main:app --reload
```
Desde el main:
```ini
python -m app.main
```
## Testing
Para ejecutar la suite completa de tests y ver el informe de cobertura de código, usa pytest:
```ini
pytest --cov=app --cov-report=term-missing
```
## Endpoints
La documentación completa de la API (generada automáticamente por FastAPI/Swagger) está disponible en la siguiente ruta una vez que el servidor está en marcha:
``http://localhost:8000/docs``

## Decisiones de seguridad
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

**¿Por qué es importante versionar?**

Si versionamos podemos realizar cambios sin romper tus aplicaciónes antigua
que dependen de ella. Si meto algo nuevo de repente y cambio el codigo original, los usuarios que hayan descargado la 
app ya no les funcionara, por lo que si realizamos una versión posterior se podrá actualizar a ella y las nueves descargas
funcionaran ya con ese cambio ya implementado.

**¿Qué cambios justifican una nueva versión?**

En mi opinión, para justificar una nueva versión se necesita mejorar la seguridad, privacidad...
Esos son los puntos clave para hacer la nueva versión. También lo justifica la adición de nuevas funciones que no tenia antes 
o la eliminación de otras que no utilicen los clientes.

**Estrategia de deprecación de versiones antiguas**

En primer lugar, debemos anunciar el establecimiento de una fecha de desaparición a la aplicación antigua, ofreciendo seguridad en la nueva versión.
Durante ese periodo de tiempo, debemos no añadir nuevas funciones ni mejorar la versión 1, solo aplicar parches de seguridad.
Cuando llegue la fecha de borrado se eliminaran los ruters.


## Mejoras futuras
En un futuro se podría realizar un sistema refresh token en lugar de utilizar tokens de 24h
También me gustaría la opción de poder conectarte con usuarios para luchar entre tu equipo y el suyo. Así sería algo más divertida la api
y supondría una rivalidad y diversión entre los grupos de amigos.

