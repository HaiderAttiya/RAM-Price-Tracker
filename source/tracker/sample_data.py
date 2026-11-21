"""
Catalogue used by ``python manage.py seed_data``.

"""

CATALOGUE = [
    # ---- DDR5 ------------------------------------------------------------
    ("Corsair", "Vengeance DDR5", "DDR5", 32, 2, 6000, 30, "1.35", 189),
    ("Corsair", "Vengeance RGB", "DDR5", 32, 2, 6400, 32, "1.40", 209),
    ("Corsair", "Vengeance RGB", "DDR5", 64, 2, 6000, 30, "1.40", 379),
    ("Corsair", "Dominator Titanium", "DDR5", 32, 2, 7200, 34, "1.40", 289),
    ("Corsair", "Vengeance DDR5", "DDR5", 16, 2, 5200, 40, "1.25", 119),
    ("G.Skill", "Trident Z5 RGB", "DDR5", 32, 2, 6000, 30, "1.40", 199),
    ("G.Skill", "Trident Z5 RGB", "DDR5", 64, 2, 6400, 32, "1.40", 389),
    ("G.Skill", "Trident Z5 Neo RGB", "DDR5", 32, 2, 6000, 30, "1.35", 209),
    ("G.Skill", "Ripjaws S5", "DDR5", 32, 2, 5600, 36, "1.25", 169),
    ("G.Skill", "Ripjaws S5", "DDR5", 16, 2, 6000, 36, "1.35", 109),
    ("G.Skill", "Trident Z5 RGB", "DDR5", 48, 2, 8000, 38, "1.40", 339),
    ("Kingston", "Fury Beast", "DDR5", 32, 2, 5600, 40, "1.25", 159),
    ("Kingston", "Fury Beast", "DDR5", 32, 2, 6000, 36, "1.35", 179),
    ("Kingston", "Fury Renegade", "DDR5", 32, 2, 6400, 32, "1.40", 219),
    ("Kingston", "Fury Beast", "DDR5", 64, 2, 5600, 40, "1.25", 309),
    ("Crucial", "Pro", "DDR5", 32, 2, 5600, 46, "1.10", 149),
    ("Crucial", "Pro", "DDR5", 32, 2, 6000, 36, "1.35", 175),
    ("Crucial", "Pro", "DDR5", 64, 2, 5600, 46, "1.10", 289),
    ("TeamGroup", "T-Force Delta RGB", "DDR5", 32, 2, 6400, 40, "1.35", 189),
    ("TeamGroup", "T-Force Vulcan", "DDR5", 32, 2, 6000, 38, "1.35", 169),
    ("TeamGroup", "Elite", "DDR5", 16, 2, 5600, 46, "1.10", 99),
    ("Patriot", "Viper Venom", "DDR5", 32, 2, 6000, 30, "1.35", 192),
    ("Patriot", "Viper Elite 5", "DDR5", 32, 2, 6200, 40, "1.35", 185),
    ("Lexar", "Ares RGB", "DDR5", 32, 2, 6400, 32, "1.40", 205),
    ("ADATA", "XPG Lancer RGB", "DDR5", 32, 2, 6000, 30, "1.35", 195),
    ("ADATA", "XPG Lancer Blade", "DDR5", 16, 2, 6000, 30, "1.35", 125),
    # ---- DDR4 ------------------------------------------------------------
    ("Corsair", "Vengeance LPX", "DDR4", 16, 2, 3200, 16, "1.35", 62),
    ("Corsair", "Vengeance LPX", "DDR4", 32, 2, 3200, 16, "1.35", 115),
    ("Corsair", "Vengeance RGB Pro", "DDR4", 32, 2, 3600, 18, "1.35", 129),
    ("Corsair", "Vengeance LPX", "DDR4", 64, 2, 3200, 16, "1.35", 215),
    ("G.Skill", "Ripjaws V", "DDR4", 16, 2, 3200, 16, "1.35", 58),
    ("G.Skill", "Ripjaws V", "DDR4", 32, 2, 3600, 16, "1.35", 112),
    ("G.Skill", "Trident Z RGB", "DDR4", 32, 2, 3600, 16, "1.35", 139),
    ("G.Skill", "Trident Z Neo", "DDR4", 32, 2, 3600, 14, "1.45", 149),
    ("Kingston", "Fury Beast", "DDR4", 16, 2, 3200, 16, "1.35", 60),
    ("Kingston", "Fury Beast", "DDR4", 32, 2, 3200, 16, "1.35", 109),
    ("Kingston", "Fury Renegade", "DDR4", 32, 2, 3600, 16, "1.35", 132),
    ("Crucial", "Basics", "DDR4", 16, 2, 3200, 22, "1.20", 52),
    ("Crucial", "Basics", "DDR4", 32, 2, 3200, 22, "1.20", 98),
    ("TeamGroup", "T-Force Vulcan Z", "DDR4", 16, 2, 3200, 16, "1.35", 55),
    ("TeamGroup", "T-Force Delta RGB", "DDR4", 32, 2, 3600, 18, "1.35", 125),
    ("TeamGroup", "Elite", "DDR4", 8, 1, 3200, 22, "1.20", 29),
    ("Patriot", "Viper Steel", "DDR4", 16, 2, 3600, 18, "1.35", 63),
    ("Patriot", "Viper Steel", "DDR4", 32, 2, 3600, 18, "1.35", 117),
    ("ADATA", "XPG Spectrix D50 RGB", "DDR4", 32, 2, 3200, 16, "1.35", 119),
    # ---- DDR3 ------------------------------------------------------------
    ("Corsair", "Vengeance", "DDR3", 16, 2, 1600, 9, "1.50", 64),
    ("G.Skill", "Ripjaws X", "DDR3", 8, 2, 1866, 10, "1.50", 41),
    ("Kingston", "HyperX Fury", "DDR3", 8, 2, 1600, 10, "1.50", 36),
    ("Crucial", "Value", "DDR3", 8, 1, 1600, 11, "1.35", 28),
]




PROMOTIONS = [
    ("G.Skill", "Trident Z5 RGB", 32, 6000, 0.24),
    ("Kingston", "Fury Beast", 32, 6000, 0.16),
    ("Crucial", "Pro", 32, 5600, 0.22),
    ("TeamGroup", "T-Force Vulcan", 32, 6000, 0.15),
    ("Corsair", "Vengeance LPX", 32, 3200, 0.15),
    ("G.Skill", "Ripjaws V", 32, 3600, 0.25),
    ("Kingston", "Fury Beast", 32, 3200, 0.16),
    ("ADATA", "XPG Spectrix D50 RGB", 32, 3200, 0.15),
]



WATCHLIST = [
    ("G.Skill", "Trident Z5 RGB", 32, 6000, 1.05),
    ("G.Skill", "Ripjaws V", 32, 3600, 1.05),
    ("Corsair", "Vengeance DDR5", 32, 6000, 0.90),
    ("Kingston", "Fury Renegade", 32, 6400, 0.92),
    ("Corsair", "Vengeance RGB Pro", 32, 3600, 0.88),
]
