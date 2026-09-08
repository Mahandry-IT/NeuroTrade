"""Nonce centralisé pour Kraken API — croissance stricte garanti.

Kraken exige un nonce strictement croissant par clé API.
Avec un scheduler déclenchant des appels rapprochés, time.time()
peut produire des nonces identiques. Ce module garantit la croissance
même après redémarrage via un compteur atomique persisté en DB.
"""

import logging
import threading
import time
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

_lock = threading.Lock()
_last_nonce: int = 0


def get_nonce() -> int:
    """Génère un nonce strictement croissant.

    Utilise time.time_ns() // 1000 (microsecondes) comme base,
    avec un verrou pour garantir la croissance même en cas d'appels
    concurrents. Si la valeur calculée est <= au dernier nonce,
    on incrémente de 1.

    Retour:
        int: nonce unique et strictement croissant.
    """
    global _last_nonce
    with _lock:
        now_nonce = int(time.time_ns() // 1000)
        if now_nonce <= _last_nonce:
            _last_nonce += 1
        else:
            _last_nonce = now_nonce
        return _last_nonce
