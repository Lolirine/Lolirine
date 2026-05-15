# -*- coding: utf-8 -*-
"""
image_processor
===============
Pipeline de post-traitement des candidats images :

1. Décodage + validation (PIL)
2. Background removal (rembg, optionnel)
3. Resize (max 1200×1200, conserve ratio)
4. Conversion WebP (qualité 90)
5. Génération thumbnail (300×300)
6. Calcul hash perceptuel (imagehash)

rembg charge un modèle ONNX ~170 MB au premier appel. Le modèle est
cachable et réutilisé entre les appels (singleton).
"""
import base64
import io
import logging

_logger = logging.getLogger(__name__)


# Singleton rembg session (chargement coûteux)
_REMBG_SESSION = None


def _get_rembg_session():
    """Charge la session rembg une seule fois."""
    global _REMBG_SESSION
    if _REMBG_SESSION is None:
        try:
            from rembg import new_session
            # u2netp = modèle léger (~4 MB), suffisant pour produits sur fond clair
            # u2net = modèle complet (~170 MB), meilleure qualité
            _REMBG_SESSION = new_session('u2netp')
            _logger.info("rembg session initialized (u2netp)")
        except ImportError:
            _logger.warning("rembg non installé, bg removal désactivé")
            _REMBG_SESSION = False
        except Exception as e:
            _logger.warning("rembg init failed: %s", e)
            _REMBG_SESSION = False
    return _REMBG_SESSION if _REMBG_SESSION else None


class ImageProcessor:
    """Pipeline de post-traitement."""

    def __init__(self, enable_bg_removal=True, enable_webp=True, max_size=1200):
        self.enable_bg_removal = enable_bg_removal
        self.enable_webp = enable_webp
        self.max_size = max_size

    def process(self, image_bytes):
        """
        Traite une image et retourne un dict :
        {
          'image_raw'      : base64 image brute
          'image_no_bg'    : base64 image sans fond (si rembg activé)
          'image_processed': base64 image finale (sans fond + resize + WebP)
          'image_thumb'    : base64 thumbnail 300×300
          'phash'          : hash perceptuel hex
          'width', 'height': dimensions finales
        }
        """
        from PIL import Image
        try:
            img = Image.open(io.BytesIO(image_bytes))
            img.load()
        except Exception as e:
            _logger.debug("PIL open failed: %s", e)
            return None

        # Conversion RGB pour cohérence (sauf si PNG transparent qu'on garde)
        original_mode = img.mode
        if img.mode not in ('RGB', 'RGBA', 'P'):
            img = img.convert('RGB')

        result = {
            'image_raw': base64.b64encode(image_bytes),
        }

        # 1. Background removal
        no_bg_img = None
        if self.enable_bg_removal:
            no_bg_img = self._remove_bg(image_bytes)
            if no_bg_img:
                buf = io.BytesIO()
                no_bg_img.save(buf, format='PNG')
                result['image_no_bg'] = base64.b64encode(buf.getvalue())

        # 2. Image finale = sans fond si dispo, sinon brute
        final_img = no_bg_img if no_bg_img else img

        # 3. Resize
        final_img = self._resize(final_img, self.max_size)
        result['width'] = final_img.width
        result['height'] = final_img.height

        # 4. Sauvegarde finale (WebP ou PNG)
        buf = io.BytesIO()
        if self.enable_webp and final_img.mode == 'RGBA':
            final_img.save(buf, format='WEBP', quality=90, method=6)
        elif self.enable_webp:
            final_img.save(buf, format='WEBP', quality=90, method=6)
        elif final_img.mode == 'RGBA':
            final_img.save(buf, format='PNG', optimize=True)
        else:
            final_img.save(buf, format='JPEG', quality=92, optimize=True)
        result['image_processed'] = base64.b64encode(buf.getvalue())

        # 5. Thumbnail
        thumb = final_img.copy()
        thumb.thumbnail((300, 300), Image.LANCZOS)
        buf = io.BytesIO()
        if thumb.mode == 'RGBA':
            thumb.save(buf, format='PNG', optimize=True)
        else:
            thumb.save(buf, format='JPEG', quality=85, optimize=True)
        result['image_thumb'] = base64.b64encode(buf.getvalue())

        # 6. Hash perceptuel
        result['phash'] = self._phash(final_img)

        return result

    def _remove_bg(self, image_bytes):
        """Applique rembg si dispo. Retourne PIL.Image ou None."""
        session = _get_rembg_session()
        if not session:
            return None
        try:
            from rembg import remove
            from PIL import Image
            out_bytes = remove(image_bytes, session=session)
            return Image.open(io.BytesIO(out_bytes))
        except Exception as e:
            _logger.debug("rembg failed: %s", e)
            return None

    def _resize(self, img, max_size):
        """Redimensionne en conservant le ratio."""
        from PIL import Image
        w, h = img.size
        if max(w, h) <= max_size:
            return img
        if w >= h:
            new_w = max_size
            new_h = int(h * max_size / w)
        else:
            new_h = max_size
            new_w = int(w * max_size / h)
        return img.resize((new_w, new_h), Image.LANCZOS)

    def _phash(self, img):
        """Hash perceptuel hex. None si imagehash absent."""
        try:
            import imagehash
            # Convertir RGBA en RGB sur fond blanc pour phash stable
            from PIL import Image
            if img.mode == 'RGBA':
                bg = Image.new('RGB', img.size, (255, 255, 255))
                bg.paste(img, mask=img.split()[3])
                img = bg
            return str(imagehash.phash(img, hash_size=16))
        except ImportError:
            return None
        except Exception as e:
            _logger.debug("phash failed: %s", e)
            return None
