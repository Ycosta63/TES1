"""
Implémentation de bruit 2D déterministe simple (style value noise / fBm)
pour générer des biomes et variations de terrain.

On évite toute dépendance externe pour rester "rétro" et portable.
"""

from __future__ import annotations

import math
from dataclasses import dataclass


def _hash2i(x: int, y: int, seed: int) -> int:
    """
    Petit hash 2D déterministe, inspiré de mix de Murmur/xxHash.
    Retourne un entier 32 bits.
    """
    h = seed & 0xFFFFFFFF
    h ^= (x * 0x27d4eb2d) & 0xFFFFFFFF
    h = (h ^ (h >> 15)) & 0xFFFFFFFF
    h ^= (y * 0x165667b1) & 0xFFFFFFFF
    h = (h ^ (h >> 13)) & 0xFFFFFFFF
    h = (h * 0x85ebca6b) & 0xFFFFFFFF
    h = (h ^ (h >> 16)) & 0xFFFFFFFF
    return h


def _hash2f(x: int, y: int, seed: int) -> float:
    """
    Hash 2D vers un float dans [0, 1].
    """
    return _hash2i(x, y, seed) / 0xFFFFFFFF


def _lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def _smoothstep(t: float) -> float:
    # Lissage type Perlin (3t^2 - 2t^3)
    return t * t * (3.0 - 2.0 * t)


@dataclass
class ValueNoise2D:
    """
    Bruit de valeur 2D avec interpolation bilinéaire + fBm.

    Ce n'est pas un "vrai" Perlin/Simplex, mais suffisant pour
    un style rétro et des biomes cohérents.
    """

    seed: int
    frequency: float = 0.05
    octaves: int = 4
    lacunarity: float = 2.0
    gain: float = 0.5

    def sample(self, x: float, y: float) -> float:
        """
        Renvoie un bruit pseudo-Perlin dans [-1, 1].
        """
        amp = 1.0
        freq = self.frequency
        total = 0.0
        norm = 0.0

        for _ in range(self.octaves):
            nx = x * freq
            ny = y * freq

            total += self._value_noise(nx, ny) * amp
            norm += amp

            amp *= self.gain
            freq *= self.lacunarity

        if norm == 0:
            return 0.0
        return total / norm

    def _value_noise(self, x: float, y: float) -> float:
        """
        Value noise de base sur une grille entière avec interpolation.
        """
        xi = math.floor(x)
        yi = math.floor(y)
        xf = x - xi
        yf = y - yi

        # Coeff de lissage
        tx = _smoothstep(xf)
        ty = _smoothstep(yf)

        # Quatre coins de la cellule
        v00 = _hash2f(xi, yi, self.seed)
        v10 = _hash2f(xi + 1, yi, self.seed)
        v01 = _hash2f(xi, yi + 1, self.seed)
        v11 = _hash2f(xi + 1, yi + 1, self.seed)

        # Interpolation bilinéaire
        a = _lerp(v00, v10, tx)
        b = _lerp(v01, v11, tx)
        value = _lerp(a, b, ty)

        # Remap [0,1] -> [-1,1]
        return value * 2.0 - 1.0


