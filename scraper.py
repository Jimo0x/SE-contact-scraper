#!/usr/bin/env python3

import re
import csv
import json
import time
import random
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from datetime import datetime
from collections import defaultdict
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
    domaine = urlparse(base_url).netloc
    liens = set()

    for tag in soup.find_all("a", href=True):
        lien = urljoin(base_url, tag["href"])
        if urlparse(lien).netloc == domaine:
            # Ignore les fichiers non-HTML
            if not re.search(r"\.(pdf|jpg|png|gif|zip|mp4|css|js)$", lien, re.I):
                liens.add(lien.split("#")[0])  # Retire les ancres

    return liens

def crawler_site(url_depart, profondeur=2, delai=1.0):
    """
    Crawle un site web jusqu'à une certaine profondeur.
    Retourne une liste de contacts trouvés.
    """
    info(f"Démarrage du crawler sur {url_depart} (profondeur={profondeur})")

    visites = set()
    a_visiter = {url_depart}
    tous_contacts = []

    for niveau in range(profondeur):
        info(f"Niveau {niveau+1}/{profondeur} — {len(a_visiter)} page(s) à crawler")
        prochaines = set()

        for url in a_visiter:
            if url in visites:
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
def export_csv(tous_contacts, fichier="contacts.csv"):
    with open(fichier, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
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
    lignes = ""
    for c in tous_contacts:
        if "emails" in c:
            for email in c.get("emails", []):
                lignes += f"<tr><td>Web</td><td>{c['url']}</td><td>{email}</td><td>—</td><td>—</td></tr>\n"
            for tel in c.get("telephones", []):
                lignes += f"<tr><td>Web</td><td>{c['url']}</td><td>—</td><td>{tel}</td><td>—</td></tr>\n"
            for nom in c.get("noms", []):
                lignes += f"<tr><td>Web</td><td>{c['url']}</td><td>—</td><td>—</td><td>{nom}</td></tr>\n"
        else:
            lignes += (f"<tr><td>{c.get('source','LinkedIn')}</td>"
                       f"<td>{c.get('url','')}</td>"
                       f"<td>{c.get('email','—')}</td>"
                       f"<td>{c.get('tel','—')}</td>"
                       f"<td>{c.get('nom','—')}</td></tr>\n")

    html = f"""<!DOCTYPE html>
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
        f.write(html)
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


def main():
    tous_contacts = []
    choix = menu()

    # ── Web Crawler ──
    if choix == "1":
        url = input(">> URL du site (ex: https://example.com) : ").strip()
        profondeur = int(input(">> Profondeur de crawl (1=surface, 3=profond) : ") or "2")
        delai = float(input(">> Délai entre requêtes en secondes (ex: 1.0) : ") or "1.0")
        tous_contacts = crawler_site(url, profondeur, delai)

    # ── LinkedIn Profil ──
    elif choix == "2":
        email_li = input(">> Ton email LinkedIn : ").strip()
        mdp_li   = input(">> Ton mot de passe LinkedIn : ").strip()
        cible    = input(">> URL ou username du profil (ex: johndoe) : ").strip()
        tous_contacts = linkedin_scraper("profil", cible, email_li, mdp_li)

    # ── LinkedIn Entreprise ──
    elif choix == "3":
        email_li = input(">> Ton email LinkedIn : ").strip()
        mdp_li   = input(">> Ton mot de passe LinkedIn : ").strip()
        cible    = input(">> URL ou nom de l'entreprise (ex: google) : ").strip()
        tous_contacts = linkedin_scraper("entreprise", cible, email_li, mdp_li)

    elif choix == "4":
        print("Bye!")
        return

    else:
        erreur("Choix invalide.")
        return

    # ── Export & Rapport ──
    if tous_contacts:
        print(f"\n{C.JAUNE}[EXPORT]{C.RESET}")
        dossier = f"resultats_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        os.makedirs(dossier, exist_ok=True)

        export_csv(tous_contacts,  f"{dossier}/contacts.csv")
        export_json(tous_contacts, f"{dossier}/contacts.json")
        generer_rapport(tous_contacts, f"{dossier}/rapport.html")

        print(f"\n{C.CYAN}Résultats sauvegardés dans : {dossier}/{C.RESET}")
    else:
        warn("Aucun contact trouvé.")


if __name__ == "__main__":
    main()