from quizpipe.textnorm import excerpt_in_page, find_in_order, fold, normalize, page_variants


def ok(excerpt: str, raw_page: str) -> bool:
    return excerpt_in_page(excerpt, page_variants(raw_page))


def test_whitespace_quotes_and_dashes_are_tolerated():
    page = "L'axe d'Uranus\nest incliné d'environ 98° : couchée."
    assert ok("L’axe d’Uranus est incliné d'environ 98° : couchée.", page)


def test_hyphenation_both_readings():
    assert ok("un système complexe", "un sys-\ntème complexe")          # coupure de mot : tiret supprimé
    assert ok("c'est peut-être vrai", "c'est peut-\nêtre vrai")        # vrai tiret : conservé


def test_case_accents_and_digits_must_match():
    page = "Mercure est la plus petite. Environ 365,25 jours."
    assert not ok("mercure est la plus petite", page)
    assert not ok("Environ 365,35 jours", page)
    assert not ok("Environ 365,25 jour", page)        # mot tronqué : « jour » n'est pas « jours »
    assert not ok("ercure est la plus petite", page)  # début de mot coupé
    assert ok("Environ 365,25 jours.", page)
    assert not ok("Mércure est la plus petite", page)


def test_superscripts_are_not_flattened():
    assert ok("T² = a³", "T² = a³")
    assert not ok("T2 = a3", "T² = a³")


def test_skip_marker_keeps_order():
    page = "Mercure, Vénus, la Terre, Mars, Jupiter, Saturne, Uranus et Neptune."
    assert ok("Mercure, Vénus [...] Uranus et Neptune.", page)
    assert ok("Mercure, Vénus […] Uranus et Neptune.", page)
    assert not ok("Uranus et Neptune. [...] Mercure, Vénus", page)


def test_tiny_segments_are_refused():
    assert not ok("la [...] Terre", "la Terre est ronde")


def test_find_in_order():
    text = "Dans l'ordre : Mercure, Vénus, la Terre, Mars."
    assert find_in_order(["Mercure", "Vénus", "Terre", "Mars"], text)
    assert not find_in_order(["Vénus", "Mercure"], text)


def test_fold():
    assert fold("Éléphant") == "elephant"
    assert normalize("  a \n b  ") == "a b"
