"""Tiny translation layer: Spanish when the system language is Spanish,
English otherwise.

English strings are the keys, so a missing translation simply shows the
English text. To add a language, add a dictionary to ``CATALOGS``.
"""

from __future__ import annotations

import locale
import os
from typing import Dict, Optional

ES: Dict[str, str] = {
    # Jump list
    "Pinned": "Anclados",
    "Recent": "Recientes",
    "Files you open will show up here.": "Los archivos que abras aparecerán aquí.",
    "Pin to this list": "Anclar a esta lista",
    "Unpin from this list": "Desanclar de esta lista",
    "Pin a file…": "Anclar un archivo…",
    "Pin files to the jump list": "Anclar archivos a la lista de accesos",
    "Options": "Opciones",
    "Open": "Abrir",
    "Open file location": "Abrir ubicación del archivo",
    "Copy path": "Copiar ruta",
    "Move up": "Subir",
    "Move down": "Bajar",
    "Remove from this list": "Quitar de esta lista",
    # Tray menu
    "Show jump list": "Mostrar lista de accesos",
    "Options…": "Opciones…",
    "About": "Acerca de",
    "Exit": "Salir",
    # Options window
    "Close": "Cerrar",
    "Recent items to show": "Elementos recientes a mostrar",
    " items": " elementos",
    "Show pinned items": "Mostrar elementos anclados",
    "Show recent folders": "Mostrar carpetas recientes",
    "Recent folders": "Carpetas recientes",
    "Appearance": "Apariencia",
    "Follow system": "Según el sistema",
    "Light": "Claro",
    "Dark": "Oscuro",
    "Start in the tray when I log in": "Iniciar en la bandeja al iniciar sesión",
    "Use the system tray menu (compatibility)": "Usar el menú de bandeja del sistema (compatibilidad)",
    "Turn on if right-clicking the tray icon shows nothing on your desktop.\n"
    "The menu is then drawn by the panel instead of this app.":
        "Actívalo si al hacer clic derecho en el icono de la bandeja no aparece nada.\n"
        "El menú lo dibujará entonces el panel en lugar de esta aplicación.",
    "Hide everything currently in the Recent list.": "Ocultar todo lo que hay ahora en la lista Recientes.",
    "Clear recent": "Borrar recientes",
    "Cancel": "Cancelar",
    "Save": "Guardar",
    # About window
    "Credits": "Créditos",
    "Version {version}": "Versión {version}",
    "A Windows 11 style jump list for the Deepin dock and other Debian based "
    "desktops. Click the dock icon for one-click access to your recent and pinned files.":
        "Una lista de accesos al estilo de Windows 11 para el dock de Deepin y otros "
        "escritorios basados en Debian. Haz clic en el icono del dock para acceder con "
        "un clic a tus archivos recientes y anclados.",
    "Created by Eli Linares for {link}": "Creado por Eli Linares para {link}",
    "Created by Eli Linares": "Creado por Eli Linares",
    # Desktop entries
    "Jump List": "Lista de accesos",
    "Quick access to your recent and pinned files": "Acceso rápido a tus archivos recientes y anclados",
}

CATALOGS: Dict[str, Dict[str, str]] = {"es": ES}

_language: Optional[str] = None


def detect_language() -> str:
    """Return the two-letter UI language from the usual POSIX variables
    (LANGUAGE, LC_ALL, LC_MESSAGES, LANG), as gettext does. Deepin sets these
    from Control Center > Keyboard and Language."""
    for var in ("LANGUAGE", "LC_ALL", "LC_MESSAGES", "LANG"):
        value = os.environ.get(var, "")
        if not value:
            continue
        # LANGUAGE may be a priority list such as "es_MX:en".
        for part in value.split(":"):
            code = part.split(".")[0].split("@")[0].split("_")[0].lower()
            if code and code not in ("c", "posix"):
                return code
    try:
        loc = locale.getlocale()[0] or ""
    except ValueError:
        loc = ""
    return loc.split("_")[0].lower() or "en"


def language() -> str:
    global _language
    if _language is None:
        lang = detect_language()
        _language = lang if lang in CATALOGS else "en"
    return _language


def set_language(lang: Optional[str]) -> None:
    """Force a language (``None`` re-detects). Used by tests."""
    global _language
    _language = None if lang is None else (lang if lang in CATALOGS else "en")


def _(text: str, **kwargs) -> str:
    translated = CATALOGS.get(language(), {}).get(text, text)
    return translated.format(**kwargs) if kwargs else translated
