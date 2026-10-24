#!/usr/bin/env python3
# CyberLab TR :: Gizli Script
# Bu betik bir flag uretiyor. Calistir ya da mantigini coz.

_d = [112, 127, 114, 113, 72, 88, 3, 87, 70, 108, 80, 3, 73, 108, 80, 7, 95, 2, 64, 71, 2, 65, 108, 69, 0, 74, 7, 108, 3, 88, 70, 78]
_k = 51
_out = ''.join(chr(b ^ _k) for b in _d)
print(_out)
