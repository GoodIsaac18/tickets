# =============================================================================
# GENERADOR DE ICONOS - Sistema de Tickets IT
# =============================================================================
# Genera iconos .ico para las aplicaciones Emisora y Receptora
# =============================================================================

from PIL import Image, ImageDraw, ImageFont
import os
from pathlib import Path

# Directorio donde se guardarán los iconos
ICONS_DIR = Path(__file__).parent / "icons"
ICONS_DIR.mkdir(exist_ok=True)

def crear_icono_circular(nombre: str, color_fondo: str, color_texto: str, texto: str, color_borde: str = None):
    """Crea un icono circular profesional."""
    # Tamaños múltiples para el .ico
    tamaños = [256, 128, 64, 48, 32, 16]
    imagenes = []
    
    for size in tamaños:
        # Crear imagen con transparencia
        img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        
        # Dibujar círculo de fondo con gradiente simulado
        margin = size // 16
        
        # Sombra sutil
        draw.ellipse([margin + 2, margin + 2, size - margin + 2, size - margin + 2], 
                     fill=(0, 0, 0, 50))
        
        # Círculo principal
        draw.ellipse([margin, margin, size - margin, size - margin], fill=color_fondo)
        
        # Borde si se especifica
        if color_borde:
            draw.ellipse([margin, margin, size - margin, size - margin], outline=color_borde, width=max(1, size // 32))
        
        # Texto centrado
        font_size = size // 3
        try:
            # Intentar usar una fuente del sistema
            font = ImageFont.truetype("arial.ttf", font_size)
        except:
            try:
                font = ImageFont.truetype("C:\\Windows\\Fonts\\arial.ttf", font_size)
            except:
                font = ImageFont.load_default()
        
        # Calcular posición del texto para centrar
        bbox = draw.textbbox((0, 0), texto, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        x = (size - text_width) // 2
        y = (size - text_height) // 2 - size // 16
        
        draw.text((x, y), texto, fill=color_texto, font=font)
        
        imagenes.append(img)
    
    # Guardar como .ico
    ruta_ico = ICONS_DIR / f"{nombre}.ico"
    imagenes[0].save(str(ruta_ico), format='ICO', sizes=[(s, s) for s in tamaños])
    
    # También guardar PNG para otros usos
    ruta_png = ICONS_DIR / f"{nombre}.png"
    imagenes[0].save(str(ruta_png), format='PNG')
    
    return str(ruta_ico)


def crear_icono_emisora():
    """Crea el icono para la app Emisora (trabajadores)."""
    # Azul profesional con texto "T" de Ticket
    return crear_icono_circular(
        nombre="emisora",
        color_fondo="#2563EB",  # Azul
        color_texto="#FFFFFF",  # Blanco
        texto="T",
        color_borde="#1D4ED8"
    )


def crear_icono_receptora():
    """Crea el icono para la app Receptora (IT)."""
    # Rojo/Magenta con texto "IT"
    return crear_icono_circular(
        nombre="receptora",
        color_fondo="#E94560",  # Rojo/Magenta
        color_texto="#FFFFFF",  # Blanco
        texto="IT",
        color_borde="#C73E54"
    )


def crear_icono_avanzado(nombre: str, tipo: str):
    """Crea un icono más elaborado con diseño moderno."""
    tamaños = [256, 128, 64, 48, 32, 16]
    imagenes = []
    
    for size in tamaños:
        img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        
        margin = size // 12
        
        if tipo == "emisora":
            # Icono de ticket/documento estilizado
            # Fondo azul con esquina doblada
            color_fondo = "#2563EB"
            color_claro = "#60A5FA"
            
            # Rectángulo principal con esquina doblada
            puntos = [
                (margin, margin + size // 6),
                (size - margin - size // 6, margin),
                (size - margin, margin + size // 6),
                (size - margin, size - margin),
                (margin, size - margin)
            ]
            draw.polygon(puntos, fill=color_fondo)
            
            # Esquina doblada
            draw.polygon([
                (size - margin - size // 6, margin),
                (size - margin, margin + size // 6),
                (size - margin - size // 6, margin + size // 6)
            ], fill=color_claro)
            
            # Líneas horizontales (texto simulado)
            line_y_start = margin + size // 3
            line_spacing = size // 8
            for i in range(3):
                y = line_y_start + i * line_spacing
                draw.rectangle([margin + size // 6, y, size - margin - size // 6, y + size // 20], fill="#FFFFFF")
            
        else:  # receptora
            # Icono de monitor/dashboard
            color_fondo = "#E94560"
            color_oscuro = "#16213E"
            color_claro = "#00D9FF"
            
            # Monitor
            monitor_top = margin + size // 10
            monitor_bottom = size - margin - size // 5
            draw.rounded_rectangle([margin, monitor_top, size - margin, monitor_bottom], 
                                   radius=size // 16, fill=color_oscuro, outline=color_fondo, width=max(1, size // 32))
            
            # Pantalla interior
            screen_margin = size // 10
            draw.rounded_rectangle([margin + screen_margin, monitor_top + screen_margin // 2, 
                                   size - margin - screen_margin, monitor_bottom - screen_margin // 2],
                                   radius=size // 32, fill=color_fondo)
            
            # Base del monitor
            base_width = size // 4
            base_x = (size - base_width) // 2
            draw.rectangle([base_x, monitor_bottom, base_x + base_width, monitor_bottom + size // 10], fill=color_oscuro)
            draw.rectangle([margin + size // 4, size - margin - size // 20, size - margin - size // 4, size - margin], fill=color_oscuro)
            
            # Indicador en pantalla
            dot_size = size // 12
            draw.ellipse([size // 2 - dot_size // 2, (monitor_top + monitor_bottom) // 2 - dot_size // 2,
                         size // 2 + dot_size // 2, (monitor_top + monitor_bottom) // 2 + dot_size // 2], fill=color_claro)
        
        imagenes.append(img)
    
    # Guardar
    ruta_ico = ICONS_DIR / f"{nombre}.ico"
    imagenes[0].save(str(ruta_ico), format='ICO', sizes=[(s, s) for s in tamaños])
    
    ruta_png = ICONS_DIR / f"{nombre}.png"
    imagenes[0].save(str(ruta_png), format='PNG')
    
    return str(ruta_ico)


def generar_todos_iconos():
    """Genera todos los iconos del sistema."""
    print("Generando iconos...")
    
    # Iconos simples (circulares con letra)
    ico_emisora = crear_icono_emisora()
    print(f"  ✓ Icono Emisora: {ico_emisora}")
    
    ico_receptora = crear_icono_receptora()
    print(f"  ✓ Icono Receptora: {ico_receptora}")
    
    # Iconos avanzados
    ico_emisora_adv = crear_icono_avanzado("emisora_adv", "emisora")
    print(f"  ✓ Icono Emisora (avanzado): {ico_emisora_adv}")
    
    ico_receptora_adv = crear_icono_avanzado("receptora_adv", "receptora")
    print(f"  ✓ Icono Receptora (avanzado): {ico_receptora_adv}")
    
    print("\n¡Iconos generados exitosamente!")
    print(f"Ubicación: {ICONS_DIR}")
    
    return {
        "emisora": ico_emisora,
        "receptora": ico_receptora,
        "emisora_adv": ico_emisora_adv,
        "receptora_adv": ico_receptora_adv
    }


if __name__ == "__main__":
    generar_todos_iconos()
