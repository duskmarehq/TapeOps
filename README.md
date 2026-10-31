# Rubik y TapeOps

Sistema de optimización de ruteo logístico B2B de última milla.

- **Rubik** (`rubik-web/`): dashboard web del administrador. Carga pedidos, planifica rutas y monitorea la operación sobre un mapa.
- **TapeOps** (`tapeops_app/`): aplicación móvil del operario (Flutter). Muestra la ruta, confirma entregas y reporta incidencias.
- **Backend** (`backend/`): API REST en FastAPI. Resuelve el problema de ruteo con ventanas horarias y capacidad (VRPTW) con Google OR-Tools sobre tiempos de viaje reales de OSRM, y re-optimiza la ruta de un vehículo cuando el operario reporta una incidencia.


PostgreSQL es la única fuente de verdad. Firestore se usa solo para avisar a las interfaces que algo cambió; los datos de negocio nunca viven ahí.

---

## 1. Requisitos y paquetes necesarios

### 1.1 Herramientas del sistema

| Herramienta | Versión | Para qué se usa |
|---|---|---|
| Git | cualquiera | Clonar el repositorio |
| Docker Engine y Docker Compose (plugin `docker compose`) | recientes | PostgreSQL y OSRM |
| Python | 3.12 o superior | Backend |
| [uv](https://docs.astral.sh/uv/) | reciente | Gestor de paquetes y entorno virtual de Python |
| Flutter | 3.32 o superior (usa `RadioGroup`) | Aplicación móvil |
| Cliente de PostgreSQL (`psql`) | opcional | Consultar la base a mano |
| Firebase CLI y FlutterFire CLI | opcional, necesarias para el tiempo real | Configurar Firebase |
| Navegador moderno | Chrome, Firefox o similar | Dashboard |

Instalación en Ubuntu:

```bash
# uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# utilidades
sudo apt install -y git postgresql-client

# Docker: seguir https://docs.docker.com/engine/install/ubuntu/
# Flutter: seguir https://docs.flutter.dev/get-started/install

# Firebase CLI y FlutterFire CLI (solo para el tiempo real)
curl -sL https://firebase.tools | bash
dart pub global activate flutterfire_cli
```

Comprobación rápida:

```bash
docker compose version && uv --version && python3 --version && flutter --version
```

### 1.2 Paquetes del backend (Python)

Se instalan solos con `uv sync` a partir de `backend/pyproject.toml` y `backend/uv.lock`. Se listan como referencia.

| Paquete | Uso |
|---|---|
| `fastapi`, `uvicorn[standard]` | API REST y servidor |
| `sqlalchemy[asyncio]`, `asyncpg` | Acceso asíncrono a PostgreSQL |
| `alembic` | Migraciones del esquema |
| `pydantic[email]`, `pydantic-settings` | Validación y configuración |
| `pyjwt` | Tokens JWT |
| `passlib[bcrypt]`, `bcrypt<4.1` | Hash de contraseñas (la versión de `bcrypt` está fijada por compatibilidad con `passlib`) |
| `ortools` | Resolución del VRPTW |
| `httpx` | Cliente HTTP hacia OSRM |
| `firebase-admin` | Escritura de la señal en Firestore |
| `pytest`, `pytest-asyncio`, `ruff` | Desarrollo (grupo `dev`) |

### 1.3 Paquetes de la aplicación móvil (Flutter)

Se instalan con `flutter pub get`.

| Paquete | Uso |
|---|---|
| `http` | Cliente de la API |
| `provider` | Manejo de estado |
| `flutter_secure_storage` | Almacenamiento del token |
| `firebase_core`, `cloud_firestore` | Escucha de la señal en tiempo real |

### 1.4 Dashboard y servicios externos

El dashboard no tiene proceso de compilación ni dependencias de `npm`. Carga desde CDN:

- Leaflet 1.9.4 y teselas de OpenStreetMap.
- Firebase JS SDK 10.12.2 (módulos ES).
- Fuentes Inter y JetBrains Mono (Google Fonts).

Imágenes de Docker: `postgres:16-alpine` y `osrm/osrm-backend`.

### 1.5 Puertos usados

| Puerto | Servicio |
|---|---|
| 5432 | PostgreSQL |
| 5001 | OSRM |
| 8000 | API (FastAPI) |
| 5500 | Dashboard (servidor estático) |

---

## 2. Puesta en marcha

Todos los comandos parten de la raíz del repositorio.

### 2.1 Clonar

```bash
git clone URL_DEL_REPOSITORIO
cd CARPETA_DEL_REPOSITORIO
```

### 2.2 Infraestructura (PostgreSQL y OSRM)

```bash
cd infra
cp .env.example .env          # editar POSTGRES_USER, POSTGRES_PASSWORD y POSTGRES_DB
mkdir -p osrm/data
```

El esquema inicial de la base está en `infra/postgres-init/01-schema.sql` y se aplica solo la primera vez que arranca el contenedor con el volumen vacío.

**Datos de ruteo (se hace una sola vez).** Descargar el extracto de OpenStreetMap de Paraguay y preprocesarlo con OSRM:

```bash
cd osrm/data
wget https://download.geofabrik.de/south-america/paraguay-latest.osm.pbf

docker run --rm -v "$(pwd):/data" osrm/osrm-backend osrm-extract -p /opt/car.lua /data/paraguay-latest.osm.pbf
docker run --rm -v "$(pwd):/data" osrm/osrm-backend osrm-partition /data/paraguay-latest.osrm
docker run --rm -v "$(pwd):/data" osrm/osrm-backend osrm-customize /data/paraguay-latest.osrm
cd ../..
```

Los tres comandos deben correrse desde `infra/osrm/data`. Después, levantar los servicios:

```bash
docker compose up -d
docker compose ps            # rubik_postgres debe figurar como healthy
```

Verificación:

```bash
psql -h localhost -U TU_USUARIO -d TU_BASE -c "\dt"
curl "http://localhost:5001/route/v1/driving/-57.5,-25.3;-57.6,-25.4?overview=false"
```

La primera debe listar ocho tablas y la segunda devolver `"code":"Ok"`.

> Las coordenadas de todo el sistema deben caer dentro del extracto cargado (Paraguay). Un punto fuera de él hace fallar la matriz de tiempos al optimizar.

### 2.3 Backend

```bash
cd backend
cp .env.example .env
```

Completar `backend/.env`. Los datos de PostgreSQL deben coincidir con los de `infra/.env`:

```env
POSTGRES_USER=...
POSTGRES_PASSWORD=...
POSTGRES_DB=...
POSTGRES_HOST=localhost
POSTGRES_PORT=5432

JWT_SECRET_KEY=...                  # generar con: openssl rand -hex 32
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=60

OSRM_BASE_URL=http://localhost:5001

# Código necesario para registrar administradores.
# Si no se define, el registro de administradores queda deshabilitado.
ADMIN_INVITE_CODE=...

# Opcional: habilita el tiempo real (ver sección 2.5)
FIREBASE_CREDENTIALS_PATH=firebase-service-account.json
```

Instalar dependencias, aplicar las migraciones y arrancar:

```bash
uv sync
uv run python -m alembic upgrade head
uv run python -m uvicorn app.main:app --reload
```

> El esquema base viene de `01-schema.sql`; Alembic aplica por encima las migraciones posteriores (por ejemplo, `pedido.operario_id`). No hace falta ningún paso previo de sincronización.
>
> Se usa `uv run python -m ...` y no `uv run uvicorn` porque en algunos entornos `uv run` no resuelve los ejecutables instalados.
>
> `--reload` no vigila el archivo `.env`: si cambiás una variable, reiniciá el servidor.

Verificación:

```bash
curl http://localhost:8000/health        # {"status":"ok"}
```

La documentación interactiva de la API queda en <http://localhost:8000/docs>.

### 2.4 Dashboard (Rubik)

```bash
cd rubik-web
python3 -m http.server 5500
```

Abrir <http://localhost:5500>. También sirve la extensión Live Server de VS Code. Debe servirse por HTTP: los módulos ES no cargan desde `file://`.

La dirección de la API se configura en `rubik-web/js/config.js`.

Por defecto el backend acepta peticiones desde los puertos 5500 y 5501 de `localhost` y `127.0.0.1`. Si servís el dashboard en otro puerto, agregalo a `cors_origins` en `backend/app/core/config.py`.

### 2.5 Tiempo real con Firebase (opcional)

Sin Firebase todo funciona, pero el dashboard y la app no se actualizan solos: hay que recargar. Para activarlo:

1. Crear un proyecto en la [consola de Firebase](https://console.firebase.google.com) y crear una base de **Firestore** en modo producción.
2. **El código apunta a una base con el identificador `default` (sin paréntesis).** Si creás la base con el identificador `(default)`, hay que cambiar el valor en tres lugares: `backend/app/services/firebase_service.py` (`database_id`), `rubik-web/js/firebase-listener.js` (`getFirestore`) y `tapeops_app/lib/services/firestore_service.dart` (`databaseId`).
3. Publicar estas reglas de seguridad. Los clientes solo leen; el backend escribe con el Admin SDK, que ignora las reglas:

   ```
   rules_version = '2';
   service cloud.firestore {
     match /databases/{database}/documents {
       match /rutas_activas/{rutaId} {
         allow read: if true;
         allow write: if false;
       }
       match /{document=**} {
         allow read, write: if false;
       }
     }
   }
   ```

4. **Backend:** descargar la cuenta de servicio (Configuración del proyecto → Cuentas de servicio → Generar nueva clave privada), guardarla como `backend/firebase-service-account.json` y definir `FIREBASE_CREDENTIALS_PATH` en `backend/.env`.
5. **Dashboard:** registrar una app web, copiar `rubik-web/js/firebase-config.example.js` a `rubik-web/js/firebase-config.js` y completar los valores. El archivo debe conservar la palabra `export`.
6. **App móvil:** desde `tapeops_app`, correr `flutterfire configure` (web y Android). Esto genera `lib/firebase_options.dart`.

Reiniciar el backend. En el dashboard, el indicador de la barra superior pasa a verde con el texto "En vivo" cuando la conexión es real.

### 2.6 Aplicación móvil (TapeOps)

```bash
cd tapeops_app
flutter pub get
flutter run -d chrome          # o un emulador / dispositivo: flutter run
```

`lib/firebase_options.dart` no se versiona: hay que generarlo con `flutterfire configure` (sección 2.5) antes de compilar.

La dirección del backend se resuelve según la plataforma en `lib/core/config.dart`:

| Dónde corre la app | Dirección |
|---|---|
| Chrome (web) | `http://localhost:8000/api/v1` |
| Emulador de Android | `http://10.0.2.2:8000/api/v1` (`localhost` no llega a tu máquina) |
| Dispositivo físico | La IP de tu máquina en la red local |

Para un APK de release, agregar el permiso `INTERNET` en `android/app/src/main/AndroidManifest.xml`.

---

## 3. Primer uso

1. **Crear un administrador.** En el dashboard, "Crear cuenta de administrador", con el `ADMIN_INVITE_CODE` definido en `backend/.env`.
2. **Crear el depósito.** El sistema asume un único depósito, y el dashboard solo lo muestra, así que se carga por API. Reemplazá el email, la contraseña y las coordenadas:

   ```bash
   TOKEN_ADMIN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
     -H "Content-Type: application/json" \
     -d '{"email":"TU_EMAIL","password":"TU_PASSWORD"}' | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

   curl -X POST http://localhost:8000/api/v1/depositos \
     -H "Content-Type: application/json" \
     -H "Authorization: Bearer $TOKEN_ADMIN" \
     -d '{"nombre":"Depósito central","direccion":"Tu dirección","latitud":-25.30,"longitud":-57.50}'
   ```

   Para cambiarlo después se usa `PUT /api/v1/depositos/{id}`. Mantené un solo depósito.
3. **Cargar vehículos y clientes** desde el dashboard.
4. **Registrar un operario** desde la aplicación móvil ("Crear cuenta de operario"). Recargá el dashboard para que aparezca en los selectores.
5. **Cargar pedidos.** En el panel de pedidos, elegí el cliente, marcá el punto de entrega con un clic en el mapa y, si querés, un operario destino.
6. **Optimizar rutas.** Con "Optimizar rutas": fecha y uno o más pares vehículo–operario. Las rutas se dibujan sobre las calles.
7. **Ejecutar la ruta.** El operario inicia sesión en la app, ve sus paradas, confirma entregas y reporta incidencias. Ante una incidencia, el sistema re-optimiza las paradas pendientes de su vehículo y el dashboard avisa en vivo.

Prueba rápida del solver, sin infraestructura:

```bash
cd backend
uv run python -m scripts.test_solver
```

---

## 4. Estructura del repositorio

```
.
├── backend/
│   ├── app/
│   │   ├── api/v1/          endpoints (auth, pedidos, rutas, incidencias, entregas, ...)
│   │   ├── core/            configuración, base de datos, seguridad
│   │   ├── models/          modelos SQLAlchemy
│   │   ├── schemas/         esquemas Pydantic
│   │   └── services/        optimizador (OSRM y OR-Tools), trazado, Firebase
│   ├── alembic/             migraciones
│   ├── scripts/             pruebas manuales
│   └── pyproject.toml
├── rubik-web/               dashboard (HTML, CSS y JS sin compilación)
├── tapeops_app/             app Flutter del operario
└── infra/
    ├── docker-compose.yml   PostgreSQL y OSRM
    ├── postgres-init/       esquema SQL inicial
    └── osrm/data/           extracto de OpenStreetMap (no se versiona)
```

---

## 5. Archivos que no deben subirse al repositorio

Contienen credenciales o son muy pesados:

- `.env` (en `infra/` y en `backend/`)
- `backend/firebase-service-account.json`
- `rubik-web/js/firebase-config.js`
- `tapeops_app/lib/firebase_options.dart`
- `infra/osrm/data/` (el extracto y los archivos procesados pesan cientos de MB y se regeneran con los pasos de la sección 2.2)
- `backend/.venv/`, `__pycache__/`, `tapeops_app/build/`, `tapeops_app/.dart_tool/`

Los archivos `.env.example` y `firebase-config.example.js` sí se versionan.

---

## 6. Limitaciones conocidas

Es un producto mínimo viable. Quedan fuera o con alcance reducido:

- Un retraso dispara la re-optimización, pero no transmite la demora al solver, por lo que el plan resultante es el mismo.
- La re-optimización parte del depósito, no de la posición del vehículo, y solo recalcula el vehículo afectado.
- Una entrega fallida no se puede reprogramar, y un pedido ya asignado no se puede cancelar.
- Dos incidencias simultáneas sobre el mismo vehículo pueden pisarse.
- La colección `rutas_activas` de Firestore es legible por cualquiera que tenga la configuración web; solo contiene identificadores y una marca de tiempo.
- El código de invitación de administradores es un secreto compartido sin límite de intentos.
- Al recargar el dashboard no se redibujan las rutas existentes, y vehículos, clientes y depósito no se editan desde la interfaz.
- La app del operario muestra la ruta como lista; el mapa con el recorrido está pendiente.
- No hay recuperación de contraseña ni suite de pruebas automatizadas.
- La expresión regular de CORS que acepta cualquier puerto de `localhost` es solo para desarrollo.

---

## 7. Tecnologías

Python, FastAPI, SQLAlchemy, Alembic, PostgreSQL, Google OR-Tools, OSRM, OpenStreetMap, Leaflet, Flutter, Firebase.
