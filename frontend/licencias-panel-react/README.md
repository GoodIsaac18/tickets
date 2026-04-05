# Panel React de Licencias

## Requisitos

- Node.js 18+
- Servicio de licencias Python corriendo en http://127.0.0.1:8787

## Ejecutar en desarrollo

1. Instalar dependencias:

   npm install

2. Definir la API (opcional, por defecto usa proxy):

   set VITE_API_BASE=

3. Iniciar panel:

   npm run dev

## Clave admin

El panel usa header `X-Admin-Key`.

Configura en servidor:

- Variable de entorno: `TICKETS_LICENSE_ADMIN_KEY`
- Si no se define, usa `cambiar-esta-clave` (cambiar en produccion)
