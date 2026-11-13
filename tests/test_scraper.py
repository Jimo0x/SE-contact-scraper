import csv
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import scraper  # noqa: E402

PAGE = """<html><body>
<p>Contact : jean.dupont@acme-corp.bj ou +229 01 23 45 67</p>
<p>Responsable : Marie Curie</p>
<img src="logo@2x.png">
<a href="/equipe">Équipe</a> <a href="https://www.acme-corp.bj/contact#form">Contact</a>
<a href="https://autre-site.com/">Ailleurs</a> <a href="/brochure.pdf">PDF</a>
<a href="mailto:x@y.bj">mail</a>
</body></html>"""


def test_extraire_contacts():
    c = scraper.extraire_contacts(PAGE, "https://acme-corp.bj/")
    assert c["emails"] == ["jean.dupont@acme-corp.bj"]
    assert any("229" in t for t in c["telephones"])
    assert "Marie Curie" in c["noms"]


def test_liens_internes_meme_site_avec_ou_sans_www():
    liens = scraper.get_liens_internes(PAGE, "https://acme-corp.bj/")
    assert liens == {"https://acme-corp.bj/equipe", "https://www.acme-corp.bj/contact"}


@pytest.mark.parametrize("valeur,attendu", [
    ("=HYPERLINK(\"http://evil\")", "'=HYPERLINK(\"http://evil\")"),
    ("@SUM(1+1)", "'@SUM(1+1)"),
    ("-2+3+cmd|' /C calc'!A0", "'-2+3+cmd|' /C calc'!A0"),
    ("+229 01 23 45 67", "+229 01 23 45 67"),     # un vrai numéro reste intact
    ("jean@acme.bj", "jean@acme.bj"),
])
def test_cellule_sure(valeur, attendu):
    assert scraper.cellule_sure(valeur) == attendu


def test_export_csv_neutralise_les_formules(tmp_path):
    f = tmp_path / "c.csv"
    scraper.export_csv([{"url": "https://x", "emails": [], "telephones": [], "noms": ["=cmd|' /C calc'!A0"]}], str(f))
    lignes = list(csv.reader(open(f, encoding="utf-8")))
    assert lignes[1][4].startswith("'=")


def test_rapport_html_echappe(tmp_path):
    f = tmp_path / "r.html"
    scraper.generer_rapport([{"url": "https://x/<script>", "emails": ["<img src=x onerror=alert(1)>@a.bj"],
                              "telephones": [], "noms": []}], str(f))
    page = f.read_text(encoding="utf-8")
    assert "<script>" not in page and "<img src=x" not in page


def test_crawler_respecte_robots_et_max_pages(monkeypatch):
    appels = []

    class Rep:
        def __init__(self, texte, code=200):
            self.text, self.status_code = texte, code

    def faux_get(url, **kw):
        appels.append(url)
        if url.endswith("/robots.txt"):
            return Rep("User-agent: *\nDisallow: /prive")
        liens = "".join(f'<a href="/page{i}">p</a>' for i in range(10)) + '<a href="/prive">x</a>'
        return Rep(f"<p>a@acme.bj</p>{liens}")

    monkeypatch.setattr(scraper.requests, "get", faux_get)
    monkeypatch.setattr(scraper.time, "sleep", lambda s: None)
    scraper.crawler_site("https://acme.bj/", profondeur=3, delai=0, max_pages=5)
    pages = [u for u in appels if not u.endswith("robots.txt")]
    assert "https://acme.bj/prive" not in pages
    assert len(pages) <= 5
