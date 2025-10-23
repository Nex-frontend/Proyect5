from django.test import SimpleTestCase
from fovisste import views

class ShortLineTests(SimpleTestCase):
    def test_normalize_short_line_moves_ptje(self):
        # Construir una línea corta de longitud 94 donde los índices 92 y 93
        # contienen los caracteres "AB" que deben terminar en posiciones 155-156
        base = 'X' * 92  # índices 0..91
        tail = 'AB'      # índices 92,93
        line94 = base + tail  # longitud 94

        normalized = views.normalize_short_line(line94, required_min_len=94, required_line_len=157)
        # Comprobar longitud
        self.assertEqual(len(normalized), 157)
        # índices objetivo 155 y 156 deben contener 'A' y 'B'
        self.assertEqual(normalized[155], 'A')
        self.assertEqual(normalized[156], 'B')
        # la región intermedia (índices 94..154) debe ser espacios
        middle = normalized[94:155]
        self.assertTrue(all(ch == ' ' for ch in middle))

