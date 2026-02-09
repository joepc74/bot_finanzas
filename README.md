# Bot de Finanzas

Un bot de finanzas diseñado para proporcionar información y análisis relacionados con finanzas.

## Descripción

Este proyecto incluye scripts de Python para ejecutar operaciones financieras automatizadas.

## Archivos del Proyecto

- `bot.py` - Script principal del bot

## Requisitos

- Python 3.x

## Instalación

1. Clona este repositorio
2. Instala las dependencias necesarias
3. Crea una basa de datos sqlite llamada bot.db, y crea una tabla con esta sentencia:
```
CREATE TABLE "tracks" (
    "id"	INTEGER NOT NULL,
    "chat_id"	TEXT NOT NULL,
    "ticker"	TEXT NOT NULL,
    "last_check"	INTEGER DEFAULT current_timestamp,
    PRIMARY KEY("id" AUTOINCREMENT)
);
```
4. Ejecuta el bot:

```bash
python botfinanazas.py
```

## Uso

El bot puede ejecutarse desde la línea de comandos usando los scripts Python incluidos.

## Licencia

Especifica la licencia de tu proyecto aquí.

## Autor

Desarrollador: Joe Colino

## Contribuciones

Las contribuciones son bienvenidas. Por favor, abre un problema o crea un pull request para sugerencias y mejoras.
