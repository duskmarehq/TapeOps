-- ============================================================
-- Esquema de base de datos — Rubik / TapeOps
-- PostgreSQL 15+
-- Fuente única de verdad del sistema. Firebase queda fuera
-- de este esquema: solo se usa como canal de señalización.
-- ============================================================

BEGIN;

-- ------------------------------------------------------------
-- Tipos enumerados
-- ------------------------------------------------------------

CREATE TYPE rol_usuario AS ENUM ('admin', 'operario');

CREATE TYPE estado_pedido AS ENUM (
    'pendiente',
    'asignado',
    'en_ruta',
    'entregado',
    'fallido'
);

CREATE TYPE estado_ruta AS ENUM (
    'planificada',
    'en_curso',
    'finalizada'
);

CREATE TYPE estado_stop AS ENUM (
    'pendiente',
    'completado',
    'fallido'
);

CREATE TYPE tipo_incidencia AS ENUM (
    'retraso',
    'ruta_bloqueada',
    'entrega_fallida'
);

-- ------------------------------------------------------------
-- usuario: administradores (Rubik) y operarios (TapeOps)
-- ------------------------------------------------------------

CREATE TABLE usuario (
    id              SERIAL PRIMARY KEY,
    email           VARCHAR(255) NOT NULL UNIQUE,
    password_hash   VARCHAR(255) NOT NULL,
    nombre          VARCHAR(255) NOT NULL,
    rol             rol_usuario NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ------------------------------------------------------------
-- deposito: único por negocio en el MVP, modelado como tabla
-- para no bloquear una extensión futura a multi-depósito
-- ------------------------------------------------------------

CREATE TABLE deposito (
    id          SERIAL PRIMARY KEY,
    nombre      VARCHAR(255) NOT NULL,
    direccion   VARCHAR(255),
    latitud     NUMERIC(9,6) NOT NULL,
    longitud    NUMERIC(9,6) NOT NULL
);

-- ------------------------------------------------------------
-- vehiculo
-- ------------------------------------------------------------

CREATE TABLE vehiculo (
    id              SERIAL PRIMARY KEY,
    patente         VARCHAR(20) NOT NULL UNIQUE,
    capacidad_kg    NUMERIC(8,2) NOT NULL CHECK (capacidad_kg > 0),
    deposito_id     INTEGER NOT NULL REFERENCES deposito(id),
    activo          BOOLEAN NOT NULL DEFAULT true
);

-- ------------------------------------------------------------
-- cliente: destinatario B2B del pedido
-- ------------------------------------------------------------

CREATE TABLE cliente (
    id              SERIAL PRIMARY KEY,
    razon_social    VARCHAR(255) NOT NULL,
    direccion       VARCHAR(255),
    latitud         NUMERIC(9,6) NOT NULL,
    longitud        NUMERIC(9,6) NOT NULL
);

-- ------------------------------------------------------------
-- pedido
-- ------------------------------------------------------------

CREATE TABLE pedido (
    id                  SERIAL PRIMARY KEY,
    cliente_id          INTEGER NOT NULL REFERENCES cliente(id),
    latitud             NUMERIC(9,6) NOT NULL,
    longitud            NUMERIC(9,6) NOT NULL,
    peso_kg             NUMERIC(8,2) NOT NULL CHECK (peso_kg > 0),
    ventana_inicio      TIME NOT NULL,
    ventana_fin         TIME NOT NULL,
    estado              estado_pedido NOT NULL DEFAULT 'pendiente',
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT ventana_valida CHECK (ventana_fin > ventana_inicio)
);

-- ------------------------------------------------------------
-- ruta: una asignación vehículo + operario para una fecha
-- ------------------------------------------------------------

CREATE TABLE ruta (
    id              SERIAL PRIMARY KEY,
    vehiculo_id     INTEGER NOT NULL REFERENCES vehiculo(id),
    operario_id     INTEGER NOT NULL REFERENCES usuario(id),
    fecha           DATE NOT NULL,
    estado          estado_ruta NOT NULL DEFAULT 'planificada',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ------------------------------------------------------------
-- stop: una parada de la ruta, generada 1:1 desde un pedido.
-- Ver nota en diagrama-er.html sobre la cardinalidad 1:1 si
-- se va a soportar reprogramación de pedidos fallidos.
-- ------------------------------------------------------------

CREATE TABLE stop (
    id                      SERIAL PRIMARY KEY,
    ruta_id                 INTEGER NOT NULL REFERENCES ruta(id) ON DELETE CASCADE,
    pedido_id               INTEGER NOT NULL UNIQUE REFERENCES pedido(id),
    orden                   INTEGER NOT NULL,
    hora_estimada_llegada   TIMESTAMPTZ,
    hora_real_llegada       TIMESTAMPTZ,
    estado                  estado_stop NOT NULL DEFAULT 'pendiente',
    CONSTRAINT orden_unico_por_ruta UNIQUE (ruta_id, orden)
);

-- ------------------------------------------------------------
-- incidencia: reportada por el operario sobre un stop
-- ------------------------------------------------------------

CREATE TABLE incidencia (
    id              SERIAL PRIMARY KEY,
    stop_id         INTEGER NOT NULL REFERENCES stop(id),
    reportado_por   INTEGER NOT NULL REFERENCES usuario(id),
    tipo            tipo_incidencia NOT NULL,
    descripcion     TEXT,
    resuelta        BOOLEAN NOT NULL DEFAULT false,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ------------------------------------------------------------
-- Índices de soporte para las consultas del motor de
-- optimización y de los endpoints de re-optimización
-- ------------------------------------------------------------

CREATE INDEX idx_pedido_estado ON pedido(estado);
CREATE INDEX idx_ruta_vehiculo ON ruta(vehiculo_id);
CREATE INDEX idx_ruta_fecha ON ruta(fecha);
CREATE INDEX idx_stop_ruta ON stop(ruta_id);
CREATE INDEX idx_incidencia_stop ON incidencia(stop_id);

-- Acelera la búsqueda de incidencias sin resolver, que es la
-- consulta que dispara el flujo de re-optimización
CREATE INDEX idx_incidencia_no_resuelta ON incidencia(stop_id)
    WHERE resuelta = false;

COMMIT;
