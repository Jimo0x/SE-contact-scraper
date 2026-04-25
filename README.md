# 📇 SE Contact Scraper

> Un outil de scraping de contacts orienté Social Engineering — extrait emails, téléphones et noms depuis des sites web et LinkedIn, avec export et rapport HTML.

---

## 📋 Fonctionnalités

| Fonctionnalité | Description |
|---|---|
| 🌐 **Web Crawler** | Crawle automatiquement plusieurs pages d'un site |
| 📧 **Email Extractor** | Détecte et extrait toutes les adresses email |
| 📞 **Phone Extractor** | Extrait les numéros de téléphone (formats internationaux) |
| 👤 **Name Extractor** | Identifie les noms propres via regex |
| 🔗 **LinkedIn Profil** | Scrape nom, poste, entreprise, localisation d'un profil |
| 🏢 **LinkedIn Entreprise** | Liste les employés d'une entreprise LinkedIn |
| 📄 **Export CSV** | Sauvegarde les contacts dans un fichier CSV (compatible Excel) |
| 🗂️ **Export JSON** | Sauvegarde en JSON pour intégration ou traitement automatisé |
| 📊 **Rapport HTML** | Génère un rapport visuel avec stats et tableau des contacts |

---

## 🖥️ Prérequis

- Python 3.x
- Google Chrome installé (pour le scraping LinkedIn)
- Kali Linux recommandé

---

## 🚀 Installation

```bash
# Cloner le dépôt
git clone https://github.com/TON_USERNAME/se-contact-scraper.git
cd se-contact-scraper

# Installer les dépendances
pip install requests beautifulsoup4 selenium undetected-chromedriver
```

---

## ▶️ Utilisation

```bash
python3 scraper.py
```

### Menu principal

```
  ╔══════════════════════════════════════╗
  ║     SE Contact Scraper  v1.0         ║
  ║                                      ║
  ╚══════════════════════════════════════╝

  1. Scraper un site web (crawler multi-pages)
  2. Scraper un profil LinkedIn
  3. Scraper une entreprise LinkedIn
  4. Quitter
```

---

## 🧪 Exemples

### Web Crawler

```
>> Choix : 1
>> URL du site : https://example.com
>> Profondeur de crawl : 2
>> Délai entre requêtes : 1.0

[*] Démarrage du crawler sur https://example.com (profondeur=2)
[*] Niveau 1/2 — 1 page(s) à crawler
[*] Crawling : https://example.com
[+]   → 3 email(s), 1 tél, 5 nom(s)
[*] Niveau 2/2 — 8 page(s) à crawler
[+]   → 1 email(s), 0 tél, 2 nom(s)
...
[*] Crawler terminé. 9 page(s) visitée(s).
[+] Export CSV  : resultats_20240125_143022/contacts.csv
[+] Export JSON : resultats_20240125_143022/contacts.json
[+] Rapport HTML: resultats_20240125_143022/rapport.html
```

### LinkedIn Profil

```
>> Choix : 2
>> Ton email LinkedIn : toi@email.com
>> Ton mot de passe LinkedIn : ••••••••
>> URL ou username du profil : johndoe

[*] Démarrage du navigateur (LinkedIn)...
[+] Connecté à LinkedIn !
[+] Profil trouvé : John Doe — Senior Developer @ Google
```

### LinkedIn Entreprise

```
>> Choix : 3
>> Ton email LinkedIn : toi@email.com
>> Ton mot de passe LinkedIn : ••••••••
>> URL ou nom de l'entreprise : google

[+] Employé trouvé : Jane Smith — Product Manager
[+] Employé trouvé : Bob Martin — Software Engineer
...
```

---

## 📁 Structure du projet

```
se-contact-scraper/
│
├── scraper.py          # Script principal
└── README.md           # Documentation
```

### Structure des résultats générés

```
resultats_20240125_143022/
├── contacts.csv        ← Ouvrable dans Excel / LibreOffice
├── contacts.json       ← Pour intégration ou traitement automatisé
└── rapport.html        ← Rapport visuel à ouvrir dans le navigateur
```

---

## ⚙️ Détail des modules

### 🌐 Web Crawler
Commence par l'URL de départ, extrait tous les liens internes et les visite niveau par niveau. Un délai aléatoire est ajouté entre chaque requête pour éviter d'être bloqué.

### 📧 Extraction de contacts
Utilise des expressions régulières (regex) pour détecter :
- **Emails** : pattern RFC 5322 simplifié avec filtre anti-faux-positifs
- **Téléphones** : supporte les formats nationaux et internationaux (`+33`, `00...`)
- **Noms** : détecte les patterns `Prénom Nom` (deux mots capitalisés consécutifs)

### 🔗 LinkedIn Scraper
Utilise **Selenium** avec **undetected-chromedriver** pour contourner la détection de bot. Se connecte avec tes identifiants, puis scrape les informations publiques des profils et pages entreprises.

### 📊 Rapport HTML
Génère un rapport standalone (sans dépendance externe) avec :
- Statistiques globales (emails, téléphones, noms, pages scrapées)
- Tableau complet de tous les contacts trouvés
- Thème sombre style GitHub

---

## 🛡️ Bonnes pratiques intégrées

- **Délai aléatoire** entre les requêtes pour ne pas surcharger les serveurs
- **User-Agent réaliste** pour éviter les blocages basiques
- **Filtrage des faux positifs** (assets JS/CSS, emails de bibliothèques, etc.)
- **undetected-chromedriver** pour LinkedIn (contourne les détections de bot)

---

## ⚠️ Avertissement légal

> Ce projet est développé à des fins **éducatives et de recherche en sécurité** uniquement.  
> Scraper un site web ou un réseau social **sans autorisation** peut violer leurs **Conditions d'Utilisation** ainsi que des lois sur la protection des données (RGPD, CFAA, etc.).  
> Utilise cet outil **uniquement** sur des cibles pour lesquelles tu as une **autorisation explicite**.  
> L'auteur décline toute responsabilité en cas d'utilisation malveillante.

---


## 👤 Auteur

**Jimo0x**  
[![GitHub](https://img.shields.io/badge/GitHub-000?style=flat&logo=github)](https://github.com/Jimo0x)

---

## 📄 Licence

Ce projet est sous licence [MIT](LICENSE).
