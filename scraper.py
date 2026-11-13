#!/usr/bin/env python3

import re
import csv
import sys
import html
import json
import time
import random
import getpass
import argparse
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse, urldefrag
from urllib.robotparser import RobotFileParser
from datetime import datetime
import os

# ─────────────────────────────────────────
# COULEURS TERMINAL
# ─────────────────────────────────────────
class C:
    RESET = "\033[0m"
    ROUGE = "\033[91m"
    VERT  = "\033[92m"
    JAUNE = "\033[93m"
    BLEU  = "\033[94m"
    CYAN  = "\033[96m"
    GRAS  = "\033[1m"

def info(msg):   print(f"{C.BLEU}[*]{C.RESET} {msg}")
def succes(msg): print(f"{C.VERT}[+]{C.RESET} {msg}")
def erreur(msg): print(f"{C.ROUGE}[-]{C.RESET} {msg}")
def warn(msg):   print(f"{C.JAUNE}[!]{C.RESET} {msg}")


# ─────────────────────────────────────────
# PATTERNS REGEX
# ─────────────────────────────────────────
PATTERN_EMAIL = re.compile(
    r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}"
)
PATTERN_TEL = re.compile(
    r"(\+?\d[\d\s\-().]{7,}\d)"
)
PATTERN_NOM = re.compile(
    r"\b([A-Z][a-z]+ [A-Z][a-z]+)\b"
)

# Headers pour éviter d'être bloqué
HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
}


# ─────────────────────────────────────────
# 1. EXTRACTION — Emails, Téléphones, Noms
# ─────────────────────────────────────────
def extraire_contacts(html, url):
    """Extrait tous les contacts depuis le HTML d'une page."""
    soup = BeautifulSoup(html, "html.parser")
    texte = soup.get_text(separator=" ")

    emails = list(set(PATTERN_EMAIL.findall(texte)))
    telephones = list(set(PATTERN_TEL.findall(texte)))
    noms = list(set(PATTERN_NOM.findall(texte)))

    # Filtrer les faux positifs téléphone (trop courts ou trop longs)
    telephones = [t.strip() for t in telephones if 8 <= len(re.sub(r"\D", "", t)) <= 15]

    # Filtrer les emails de librairies/assets
    emails = [e for e in emails if not any(x in e for x in [
        ".png", ".jpg", ".css", ".js", "example", "sentry", "noreply"
    ])]

    return {
        "url": url,
        "emails": emails,
        "telephones": telephones,
        "noms": noms
    }


# ─────────────────────────────────────────
# 2. WEB CRAWLER
# ─────────────────────────────────────────
def get_liens_internes(html, base_url):
    """Extrait tous les liens internes d'une page."""
    soup = BeautifulSoup(html, "html.parser")
    domaine = _hote(base_url)
    liens = set()

    for tag in soup.find_all("a", href=True):
        lien = urldefrag(urljoin(base_url, tag["href"]))[0]  # Retire les ancres
        parsed = urlparse(lien)
        # Même site (www.exemple.com == exemple.com), http(s) seulement
        if parsed.scheme in ("http", "https") and _hote(lien) == domaine:
            # Ignore les fichiers non-HTML
            if not re.search(r"\.(pdf|jpe?g|png|gif|svg|webp|zip|mp4|mp3|css|js|ico)$", parsed.path, re.I):
                liens.add(lien)

    return liens


def _hote(url):
    hote = urlparse(url).netloc.lower().split("@")[-1].split(":")[0]
    return hote[4:] if hote.startswith("www.") else hote


def charger_robots(url_depart):
    """Lit le robots.txt du site. Retourne une fonction autorise(url) -> bool."""
    parsed = urlparse(url_depart)
    rp = RobotFileParser()
    try:
        resp = requests.get(f"{parsed.scheme}://{parsed.netloc}/robots.txt", headers=HEADERS, timeout=10)
        rp.parse(resp.text.splitlines() if resp.status_code == 200 else [])
    except requests.RequestException:
        rp.parse([])
    return lambda url: rp.can_fetch(HEADERS["User-Agent"], url)

def crawler_site(url_depart, profondeur=2, delai=1.0, max_pages=100, respecter_robots=True):
    """
    Crawle un site web jusqu'à une certaine profondeur.
    Respecte robots.txt et s'arrête après max_pages pages.
    Retourne une liste de contacts trouvés.
    """
    if not url_depart.startswith(("http://", "https://")):
        url_depart = "https://" + url_depart
    info(f"Démarrage du crawler sur {url_depart} (profondeur={profondeur}, max {max_pages} pages)")
    autorise = charger_robots(url_depart) if respecter_robots else (lambda url: True)

    visites = set()
    a_visiter = {url_depart}
    tous_contacts = []

    for niveau in range(profondeur):
        info(f"Niveau {niveau+1}/{profondeur} — {len(a_visiter)} page(s) à crawler")
        prochaines = set()

        for url in a_visiter:
            if url in visites:
                continue
            if len(visites) >= max_pages:
                warn(f"Limite de {max_pages} pages atteinte.")
                break
            if not autorise(url):
                warn(f"Ignoré (interdit par robots.txt) : {url}")
                visites.add(url)
                continue
            visites.add(url)

            try:
                resp = requests.get(url, headers=HEADERS, timeout=10)
                if resp.status_code != 200:
                    continue

                info(f"Crawling : {url}")
                contacts = extraire_contacts(resp.text, url)

                if any([contacts["emails"], contacts["telephones"], contacts["noms"]]):
                    succes(f"  → {len(contacts['emails'])} email(s), "
                           f"{len(contacts['telephones'])} tél, "
                           f"{len(contacts['noms'])} nom(s)")
                    tous_contacts.append(contacts)

                # Récupère les liens pour le niveau suivant
                nouveaux = get_liens_internes(resp.text, url)
                prochaines.update(nouveaux - visites)

                # Délai aléatoire pour ne pas surcharger le serveur
                time.sleep(delai + random.uniform(0, 0.5))

            except Exception as e:
                erreur(f"Erreur sur {url} : {e}")

        a_visiter = prochaines

    info(f"Crawler terminé. {len(visites)} page(s) visitée(s).")
    return tous_contacts


# ─────────────────────────────────────────
# 3. LINKEDIN SCRAPER
# ─────────────────────────────────────────
def linkedin_scraper(type_cible, cible, email_linkedin, mdp_linkedin):
    """
    Scrape LinkedIn via Selenium.
    type_cible : 'profil' ou 'entreprise'
    cible      : URL LinkedIn ou nom à rechercher
    """
    try:
        import undetected_chromedriver as uc
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
    except ImportError:
        erreur("Installe : pip install selenium undetected-chromedriver")
        return []

    info("Démarrage du navigateur (LinkedIn)...")
    options = uc.ChromeOptions()
    # options.add_argument("--headless")  # Décommente pour mode invisible
    driver = uc.Chrome(options=options)
    contacts = []

    try:
        # ── Connexion LinkedIn ──
        driver.get("https://www.linkedin.com/login")
        time.sleep(2)

        driver.find_element(By.ID, "username").send_keys(email_linkedin)
        driver.find_element(By.ID, "password").send_keys(mdp_linkedin)
        driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
        time.sleep(3)

        if "feed" not in driver.current_url and "checkpoint" not in driver.current_url:
            erreur("Connexion LinkedIn échouée. Vérifie tes identifiants.")
            return []

        succes("Connecté à LinkedIn !")

        # ── Scraping Profil ──
        if type_cible == "profil":
            url = cible if cible.startswith("http") else f"https://www.linkedin.com/in/{cible}"
            driver.get(url)
            time.sleep(3)

            soup = BeautifulSoup(driver.page_source, "html.parser")

            nom = soup.find("h1")
            poste = soup.find("div", {"class": re.compile("text-body-medium")})
            localisation = soup.find("span", {"class": re.compile("text-body-small.*inline")})
            entreprise_tag = soup.find("span", {"class": re.compile("inline-show-more-text")})

            contact = {
                "source": "LinkedIn - Profil",
                "url": url,
                "nom": nom.text.strip() if nom else "N/A",
                "poste": poste.text.strip() if poste else "N/A",
                "localisation": localisation.text.strip() if localisation else "N/A",
                "entreprise": entreprise_tag.text.strip() if entreprise_tag else "N/A",
            }

            succes(f"Profil trouvé : {contact['nom']} — {contact['poste']}")
            contacts.append(contact)

        # ── Scraping Entreprise ──
        elif type_cible == "entreprise":
            url = cible if cible.startswith("http") else f"https://www.linkedin.com/company/{cible}/people/"
            driver.get(url)
            time.sleep(3)

            soup = BeautifulSoup(driver.page_source, "html.parser")
            cartes = soup.find_all("li", {"class": re.compile("org-people-profile-card")})

            for carte in cartes:
                nom_tag = carte.find("div", {"class": re.compile("artdeco-entity-lockup__title")})
                poste_tag = carte.find("div", {"class": re.compile("artdeco-entity-lockup__subtitle")})

                contact = {
                    "source": "LinkedIn - Entreprise",
                    "url": url,
                    "nom": nom_tag.text.strip() if nom_tag else "N/A",
                    "poste": poste_tag.text.strip() if poste_tag else "N/A",
                }
                succes(f"Employé trouvé : {contact['nom']} — {contact['poste']}")
                contacts.append(contact)

    except Exception as e:
        erreur(f"Erreur LinkedIn : {e}")
    finally:
        driver.quit()

    return contacts


# ─────────────────────────────────────────
# 4. EXPORT CSV
# ─────────────────────────────────────────
def cellule_sure(valeur):
    """Neutralise l'injection de formule CSV (=, @, +, - interprétés par Excel/LibreOffice).

    Les données viennent de pages web : un attaquant peut y placer =HYPERLINK(...) ou
    =cmd|... Un numéro de téléphone (+229 01 23...) reste intact.
    """
    v = str(valeur)
    if v[:1] in ("=", "@", "\t", "\r") or (v[:1] in ("+", "-") and not re.fullmatch(r"[+\-][\d\s().\-]+", v)):
        return "'" + v
    return v


class _CsvSur:
    def __init__(self, writer):
        self.writer = writer

    def writerow(self, row):
        self.writer.writerow([cellule_sure(x) for x in row])


def export_csv(tous_contacts, fichier="contacts.csv"):
    with open(fichier, "w", newline="", encoding="utf-8") as f:
        writer = _CsvSur(csv.writer(f))
        writer.writerow(["Source", "URL", "Email", "Téléphone", "Nom"])

        for c in tous_contacts:
            # Contacts web
            if "emails" in c:
                for email in c["emails"]:
                    writer.writerow(["Web", c["url"], email, "", ""])
                for tel in c["telephones"]:
                    writer.writerow(["Web", c["url"], "", tel, ""])
                for nom in c["noms"]:
                    writer.writerow(["Web", c["url"], "", "", nom])
            # Contacts LinkedIn
            else:
                writer.writerow([
                    c.get("source", "LinkedIn"),
                    c.get("url", ""),
                    c.get("email", ""),
                    c.get("tel", ""),
                    c.get("nom", "")
                ])

    succes(f"Export CSV : {fichier}")


# ─────────────────────────────────────────
# 5. EXPORT JSON
# ─────────────────────────────────────────
def export_json(tous_contacts, fichier="contacts.json"):
    with open(fichier, "w", encoding="utf-8") as f:
        json.dump(tous_contacts, f, ensure_ascii=False, indent=2)
    succes(f"Export JSON : {fichier}")


# ─────────────────────────────────────────
# 6. RAPPORT HTML
# ─────────────────────────────────────────
def generer_rapport(tous_contacts, fichier="rapport.html"):
    """Génère un rapport HTML sans dépendance externe (pas de Jinja2 requis)."""

    total_emails = sum(len(c.get("emails", [])) for c in tous_contacts)
    total_tels   = sum(len(c.get("telephones", [])) for c in tous_contacts)
    total_noms   = sum(len(c.get("noms", [])) for c in tous_contacts)
    total_pages  = len(tous_contacts)
    date_scan    = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Construction des lignes du tableau
    e = lambda v: html.escape(str(v))  # le contenu scrappé est contrôlé par le site visité
    lignes = ""
    for c in tous_contacts:
        if "emails" in c:
            for email in c.get("emails", []):
                lignes += f"<tr><td>Web</td><td>{e(c['url'])}</td><td>{e(email)}</td><td>—</td><td>—</td></tr>\n"
            for tel in c.get("telephones", []):
                lignes += f"<tr><td>Web</td><td>{e(c['url'])}</td><td>—</td><td>{e(tel)}</td><td>—</td></tr>\n"
            for nom in c.get("noms", []):
                lignes += f"<tr><td>Web</td><td>{e(c['url'])}</td><td>—</td><td>—</td><td>{e(nom)}</td></tr>\n"
        else:
            lignes += (f"<tr><td>{e(c.get('source','LinkedIn'))}</td>"
                       f"<td>{e(c.get('url',''))}</td>"
                       f"<td>{e(c.get('email','—'))}</td>"
                       f"<td>{e(c.get('tel','—'))}</td>"
                       f"<td>{e(c.get('nom','—'))}</td></tr>\n")

    page = f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<title>Rapport SE Contact Scraper</title>
<style>
  body {{ font-family: 'Segoe UI', sans-serif; background: #0d1117; color: #c9d1d9; margin: 0; padding: 20px; }}
  h1 {{ color: #58a6ff; border-bottom: 1px solid #30363d; padding-bottom: 10px; }}
  .stats {{ display: flex; gap: 20px; margin: 20px 0; }}
  .card {{ background: #161b22; border: 1px solid #30363d; border-radius: 8px;
           padding: 20px; flex: 1; text-align: center; }}
  .card h2 {{ font-size: 2em; color: #58a6ff; margin: 0; }}
  .card p {{ color: #8b949e; margin: 5px 0 0; }}
  table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
  th {{ background: #161b22; color: #58a6ff; padding: 10px; text-align: left;
        border-bottom: 2px solid #30363d; }}
  td {{ padding: 8px 10px; border-bottom: 1px solid #21262d; font-size: 0.9em; }}
  tr:hover {{ background: #161b22; }}
  .badge {{ background: #1f6feb; color: white; padding: 2px 8px;
            border-radius: 12px; font-size: 0.8em; }}
  footer {{ margin-top: 40px; color: #8b949e; font-size: 0.85em; text-align: center; }}
</style>
</head>
<body>
<h1>🔍 SE Contact Scraper — Rapport</h1>
<p>Scan effectué le : <strong>{date_scan}</strong></p>

<div class="stats">
  <div class="card"><h2>{total_emails}</h2><p>Emails trouvés</p></div>
  <div class="card"><h2>{total_tels}</h2><p>Téléphones trouvés</p></div>
  <div class="card"><h2>{total_noms}</h2><p>Noms trouvés</p></div>
  <div class="card"><h2>{total_pages}</h2><p>Pages scrapées</p></div>
</div>

<table>
  <thead>
    <tr>
      <th>Source</th><th>URL</th><th>Email</th><th>Téléphone</th><th>Nom</th>
    </tr>
  </thead>
  <tbody>
    {lignes if lignes else '<tr><td colspan="5" style="text-align:center">Aucun contact trouvé</td></tr>'}
  </tbody>
</table>

<footer>SE Contact Scraper v1.0 — Projet 2/12 Cybersecurity Portfolio</footer>
</body>
</html>"""

    with open(fichier, "w", encoding="utf-8") as f:
        f.write(page)
    succes(f"Rapport HTML : {fichier}")


# ─────────────────────────────────────────
# MENU PRINCIPAL
# ─────────────────────────────────────────
def menu():
    print(f"""{C.CYAN}{C.GRAS}
  ╔══════════════════════════════════════╗
  ║     SE Contact Scraper  v1.0         ║
  ║                                      ║
  ╚══════════════════════════════════════╝
{C.RESET}""")
    print("  1. Scraper un site web (crawler multi-pages)")
    print("  2. Scraper un profil LinkedIn")
    print("  3. Scraper une entreprise LinkedIn")
    print("  4. Quitter")
    return input(f"\n{C.GRAS}>> Choix : {C.RESET}").strip()


def demander_nombre(question, defaut, type_=int):
    while True:
        rep = input(question).strip()
        if not rep:
            return defaut
        try:
            return type_(rep)
        except ValueError:
            erreur("Nombre invalide, réessaie.")


def exporter(tous_contacts, dossier=None):
    if not tous_contacts:
        warn("Aucun contact trouvé.")
        return
    print(f"\n{C.JAUNE}[EXPORT]{C.RESET}")
    dossier = dossier or f"resultats_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    os.makedirs(dossier, exist_ok=True)
    export_csv(tous_contacts,  f"{dossier}/contacts.csv")
    export_json(tous_contacts, f"{dossier}/contacts.json")
    generer_rapport(tous_contacts, f"{dossier}/rapport.html")
    print(f"\n{C.CYAN}Résultats sauvegardés dans : {dossier}/{C.RESET}")


def menu_interactif():
    tous_contacts = []
    choix = menu()

    # ── Web Crawler ──
    if choix == "1":
        url = input(">> URL du site (ex: https://example.com) : ").strip()
        profondeur = demander_nombre(">> Profondeur de crawl (1=surface, 3=profond) [2] : ", 2)
        delai = demander_nombre(">> Délai entre requêtes en secondes [1.0] : ", 1.0, float)
        tous_contacts = crawler_site(url, profondeur, delai)

    # ── LinkedIn ──
    elif choix in ("2", "3"):
        email_li = input(">> Ton email LinkedIn : ").strip()
        mdp_li   = getpass.getpass(">> Ton mot de passe LinkedIn (masqué) : ")
        if choix == "2":
            cible = input(">> URL ou username du profil (ex: johndoe) : ").strip()
            tous_contacts = linkedin_scraper("profil", cible, email_li, mdp_li)
        else:
            cible = input(">> URL ou nom de l'entreprise (ex: google) : ").strip()
            tous_contacts = linkedin_scraper("entreprise", cible, email_li, mdp_li)

    elif choix == "4":
        print("Bye!")
        return
    else:
        erreur("Choix invalide.")
        return

    exporter(tous_contacts)


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="SE Contact Scraper — collecte de contacts publics (OSINT). "
                    "À utiliser uniquement dans un cadre autorisé (audit, test de sensibilisation).",
        epilog="Sans argument, le menu interactif s'ouvre (crawler web + LinkedIn).",
    )
    parser.add_argument("url", nargs="?", help="site à crawler (ex: https://exemple.com)")
    parser.add_argument("-d", "--profondeur", type=int, default=2, help="profondeur de crawl (défaut : 2)")
    parser.add_argument("--delai", type=float, default=1.0, help="délai entre requêtes en secondes (défaut : 1.0)")
    parser.add_argument("--max-pages", type=int, default=100, help="nombre maximum de pages (défaut : 100)")
    parser.add_argument("-o", "--output", help="dossier de sortie (défaut : resultats_<date>)")
    args = parser.parse_args(argv)

    if not args.url:
        menu_interactif()
        return 0
    if args.delai < 0.5:
        warn("Délai minimum : 0.5 s (pour ne pas surcharger le site).")
        args.delai = 0.5
    exporter(crawler_site(args.url, args.profondeur, args.delai, args.max_pages), args.output)
    return 0


if __name__ == "__main__":
    sys.exit(main())
