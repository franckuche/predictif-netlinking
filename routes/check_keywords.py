from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import pandas as pd
from dotenv import load_dotenv
import os
from bs4 import BeautifulSoup
from urllib.parse import urlparse
import asyncio
import requests
import time

# Création d'une instance de APIRouter
router = APIRouter()

# Chargement des variables d'environnement
load_dotenv()
print("Chargement des variables d'environnement...")
yourtext_guru_api_key = os.getenv("YTG_api_key")
babbar_api_key = os.getenv("BABBAR_API_KEY")
spaceserp_api_key = os.getenv("SPACESERP_API_KEY")

# Configuration du routeur et des templates
router = APIRouter()
templates = Jinja2Templates(directory="templates")
print("Routeur et templates configurés.")

def check_account_status():
    print("Vérification du statut du compte")
    url = "https://yourtext.guru/api/status"
    headers = {"KEY": yourtext_guru_api_key, "accept": "application/json"}
    response = requests.get(url, headers=headers)
    print("Réponse complète de l'API de vérification du statut:", response.json())
    if response.status_code == 200:
        return response.json()
    else:
        print("Erreur lors de la vérification du statut:", response.text)
        return {"error": response.status_code, "message": response.text}

def launch_guide_generation(yourtext_guru_api_key, keywords, language="fr_fr"):
    print("Lancement de la génération de guide")
    url = "https://yourtext.guru/api/guide"
    headers = {"KEY": yourtext_guru_api_key, "accept": "application/json"}
    data = {"query": keywords, "type": "premium", "lang": language}
    response = requests.post(url, headers=headers, json=data)
    print("Réponse de l'API de génération de guide:", response.json())
    if response.status_code == 200:
        return response.json()
    else:
        print("Erreur lors de la génération du guide:", response.text)
        return {"error": response.status_code, "message": response.text}

# Fonction pour récupérer les données SERP
def fetch_data(keywords_list, yourtext_guru_api_key, guide_id, babbar_api_token, spaceserp_api_key):
    print("Début de la récupération des données SERP...")
    all_results = []
    base_url = "https://api.spaceserp.com/google/search"
    for keyword in keywords_list:
        keyword = keyword.strip()
        params = {
            "apiKey": spaceserp_api_key,
            "q": keyword,
            "domain": "google.fr",
            "gl": "fr",
            "hl": "fr",
            "resultFormat": "json",
            "pageSize": "10",
            "device": "mobile",
            "resultBlocks": "organic_results"
        }

        # Construction de l'URL de la requête
        request_url = f"{base_url}?{'&'.join([f'{key}={value}' for key, value in params.items()])}"
        print(f"Requête envoyée : {request_url}")  # Imprime l'URL complète de la requête


        response = requests.get(base_url, params=params)
        if response.status_code == 200:
            response_data = response.json()
            organic_results = response_data.get("organic_results", [])
            print("Réponse complète de Space SERP:", response_data)
            for item in organic_results:
                cleaned_url = item.get("link").replace("https://www.google.com", "").rstrip("}")

                text_content, html_content, image_count = scrape_content(cleaned_url)
                if text_content is None:  # Vérifier si text_content est None
                    text_content = ""  # Assigner une chaîne vide comme valeur par défaut

                hn_counts, total_headings, headings_texts = count_hn_tags(html_content)

                optimization_result = check_content_optimization(yourtext_guru_api_key, guide_id, text_content)

                score = optimization_result.get("score", "Non disponible")
                danger = optimization_result.get("danger", "Non disponible")

                url_overview = get_url_overview(babbar_api_token, cleaned_url)

                if url_overview:
                    result = {
                        "Position": item.get("position"),
                        "Url": cleaned_url,
                        "Titre": item.get("title"),
                        "Nombre de mots": len(text_content.split()), 
                        "Nombre d'images": image_count,
                        "Nombre de headings": total_headings,
                        "h1": hn_counts.get("h1", 0),
                        "h2": hn_counts.get("h2", 0),
                        "Score": score,
                        "Danger": danger,
                        "domainCount": url_overview.get("domainCount", "Non disponible"),
                        "hostCount": url_overview.get("hostCount", "Non disponible"),
                        "linkCount": url_overview.get("linkCount", "Non disponible"),
                    }
                else:
                    result = {
                        "Position": item.get("position"),
                        "Url": cleaned_url,
                        "Titre": item.get("title"),
                        "Nombre de mots": len(text_content.split()), 
                        "Nombre d'images": image_count,
                        "Nombre de headings": total_headings,
                        "h1": hn_counts.get("h1", 0),
                        "h2": hn_counts.get("h2", 0),
                        "Score": score,
                        "Danger": danger,
                        "domainCount": "Non disponible",
                        "hostCount": "Non disponible",
                        "linkCount": "Non disponible",
                    }
                all_results.append(result)
        else:
            print(f"Échec de la récupération des données pour le mot-clé: '{keyword}', Status Code: {response.status_code}")

    print("Données SERP et optimisation récupérées.")
    return all_results

# Fonction modifiée pour obtenir le texte du contenu HTML
def scrape_content(url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
    }
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            text = soup.get_text(separator=' ', strip=True)
            html_content = str(soup)
            image_count = len(soup.find_all('img'))
            return text, html_content, image_count
        else:
            print(f"Erreur lors de la requête HTTP: Status code {response.status_code}")
    except Exception as e:
        print(f"Une erreur est survenue lors du scraping de l'URL '{url}': {e}")
    return "", None, 0  # Retourner une chaîne vide pour text_content et 0 pour image_count si une erreur se produit


def count_hn_tags(html_content):
    if html_content is None:
        return {f"h{i}": 0 for i in range(1, 7)}, 0, []

    soup = BeautifulSoup(html_content, 'html.parser')
    hn_counts = {f"h{i}": len(soup.find_all(f"h{i}")) for i in range(1, 7)}
    total_headings = sum(hn_counts.values())

    # Pour stocker les textes des balises hn
    headings_texts = []

    # Imprimer et collecter le texte de chaque balise hn
    for i in range(1, 7):
        headings = soup.find_all(f"h{i}")
        print(f"Balises h{i}: {len(headings)}")
        for heading in headings:
            headings_texts.append(heading.get_text())

    return hn_counts, total_headings, headings_texts

def check_content_optimization(yourtext_guru_api_key, guide_id, content, max_attempts=3):
    url = f"https://yourtext.guru/api/check/{guide_id}"
    headers = {"KEY": yourtext_guru_api_key, "Content-Type": "application/json"}
    payload = {"content": content}
    
    for attempt in range(max_attempts):
        print(f"Tentative {attempt + 1} d'envoi de la requête d'optimisation pour guide_id={guide_id} avec contenu.")
        try:
            response = requests.post(url, headers=headers, json=payload)
            print(f"Réponse reçue de l'API d'optimisation avec le code de statut: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"Réponse de l'API d'optimisation: Score={data.get('score', 'Non disponible')}, Danger={data.get('danger', 'Non disponible')}")
                return data
            else:
                print(f"Erreur lors de l'appel de l'API d'optimisation du contenu: {response.status_code}, Réponse: {response.text}")
                if response.status_code == 556:  # Code d'erreur spécifique à "No Corresponding Guide"
                    print("Guide correspondant non trouvé, tentative de réessai après un délai.")
                    time.sleep(5)  # Attend 5 secondes avant de réessayer
                else:
                    return {"score": "Non disponible", "danger": "Non disponible"}
        except Exception as e:
            print(f"Exception lors de l'appel de l'API d'optimisation du contenu: {e}")
            time.sleep(5)  # Attend également avant de réessayer en cas d'exception

    # Si toutes les tentatives échouent
    return {"error": "Impossible d'obtenir une réponse valide après plusieurs tentatives"}

# Fonction pour évaluer l'optimisation du contenu
def process_and_evaluate_contents(urls, yourtext_guru_api_key, guide_id):
    optimization_results = []
    print(f"Évaluation de l'optimisation pour {len(urls)} URLs avec guide_id={guide_id}.")
    
    for url in urls:
        print(f"Traitement de l'URL: {url}")
        text_content, html_content = scrape_content(url)  # Assurez-vous que scrape_content retourne le texte et le contenu HTML
        
        if text_content:
            print(f"Contenu de taille {len(text_content)} caractères récupéré. Lancement de l'évaluation d'optimisation.")
        else:
            print("Aucun contenu récupéré, évaluation d'optimisation ignorée.")
        
        optimization_result = check_content_optimization(yourtext_guru_api_key, guide_id, text_content)
        
        print(f"Résultat d'optimisation pour {url}: Score={optimization_result['score']}, Danger={optimization_result['danger']}")
        
        optimization_results.append({
            "Url": url,
            "Score": optimization_result.get("score", "Non disponible"),
            "Danger": optimization_result.get("danger", "Non disponible")
        })
    
    print("Évaluation de l'optimisation terminée.")
    return optimization_results

@router.post("/keywords-resultats/", response_class=HTMLResponse)
async def get_keywords_results(request: Request, keywords: str = Form(...)):
    # Votre code existant pour récupérer les résultats...
    single_keyword = keywords.strip()
    guide_generation_result = launch_guide_generation(yourtext_guru_api_key, single_keyword, "fr_fr")
    guide_id = guide_generation_result.get("guide_id", "")
    
    if guide_id:
        babbar_api_token = os.getenv("BABBAR_API_KEY")
        results = fetch_data([single_keyword], yourtext_guru_api_key, guide_id, babbar_api_token, spaceserp_api_key)
        
        # Créez ici le DataFrame à partir de vos résultats
        df = pd.DataFrame(results)

        # Remplacer les valeurs spécifiques par des messages personnalisés si nécessaire
        df['domainCount'].replace({0: "URLs non trouvées BDD de Babbar"}, inplace=True)
        df['hostCount'].replace({0: "URLs non trouvées BDD de Babbar"}, inplace=True)
        df['linkCount'].replace({0: "URLs non trouvées BDD de Babbar"}, inplace=True)

        # Convertir le DataFrame en HTML
        html_table = df.to_html(classes='dataframe', index=False, border=0, escape=False)

        # Maintenant, envoyez les résultats et les statistiques au template, incluant `html_table`
        return templates.TemplateResponse("keywords-resultats.html", {
            "request": request, 
            "keyword": single_keyword,
            "html_table": html_table,  # Ajoutez cette ligne pour passer le tableau HTML
            "stats": calculate_stats(results)  # Supposons que vous avez une fonction pour calculer les statistiques
        })
    else:
        return templates.TemplateResponse("error_template.html", {
            "request": request, 
            "message": "Impossible de générer un guide pour le mot-clé fourni."
        })
    
def safe_int(value):
    """Convertit une valeur en int si possible, sinon retourne 0."""
    try:
        return int(value)
    except (ValueError, TypeError):
        return 0

def calculate_stats(results):
    """Calculer les statistiques à partir des résultats."""
    # Extraction des valeurs en utilisant safe_int pour gérer les valeurs non numériques
    word_counts = [safe_int(result.get('Nombre de mots', 0)) for result in results]
    image_counts = [safe_int(result.get("Nombre d'images", 0)) for result in results]
    heading_counts = [safe_int(result.get('Nombre de headings', 0)) for result in results]
    h1_counts = [safe_int(result.get('h1', 0)) for result in results]
    h2_counts = [safe_int(result.get('h2', 0)) for result in results]
    scores = [float(result.get('Score', 0)) for result in results if result.get('Score') != "Non disponible"]
    dangers = [float(result.get('Danger', 0)) for result in results if result.get('Danger') != "Non disponible"]
    domain_counts = [safe_int(result.get('domainCount', 0)) for result in results]
    host_counts = [safe_int(result.get('hostCount', 0)) for result in results]
    link_counts = [safe_int(result.get('linkCount', 0)) for result in results]

    # Fonctions utilitaires pour calculer moyenne, max, et min
    
    # Calcule la moyenne d'une liste de nombres et formate sans décimales
    def calculate_average_h1(lst):
        return round(sum(lst) / len(lst)) if lst else 0
    
    def calculate_average(lst):
        return round(sum(lst) / len(lst), 2) if lst else 0
     
    def calculate_max(lst):
        return round(max(lst), 2) if lst else "N/A"

    def calculate_min(lst):
        return round(min(lst), 2) if lst else "N/A"

    # Calcul des statistiques
    stats = {
        'moyenne_mots': calculate_average(word_counts),
        'max_mots': calculate_max(word_counts),
        'min_mots': calculate_min(word_counts),
        'moyenne_images': calculate_average(image_counts),
        'max_images': calculate_max(image_counts),
        'min_images': calculate_min(image_counts),
        'moyenne_headings': calculate_average(heading_counts),
        'max_headings': calculate_max(heading_counts),
        'min_headings': calculate_min(heading_counts),
        'moyenne_h1': calculate_average_h1(h1_counts),
        'max_h1': calculate_max(h1_counts),
        'min_h1': calculate_min(h1_counts),
        'moyenne_h2': calculate_average(h2_counts),
        'max_h2': calculate_max(h2_counts),
        'min_h2': calculate_min(h2_counts),
        'moyenne_score': f"{calculate_average(scores):.2f}%",
        'max_score': f"{calculate_max(scores):.2f}%",
        'min_score': f"{calculate_min(scores):.2f}%",
        'moyenne_danger': f"{calculate_average(dangers):.2f}%",
        'max_danger': f"{calculate_max(dangers):.2f}%",
        'min_danger': f"{calculate_min(dangers):.2f}%",
        'moyenne_domainCount': calculate_average(domain_counts) if domain_counts else "URLs indispo Babbar",
        'max_domainCount': calculate_max(domain_counts),
        'min_domainCount': calculate_min(domain_counts),
        'moyenne_hostCount': calculate_average(host_counts) if host_counts else "URLs indispo Babbar",
        'max_hostCount': calculate_max(host_counts),
        'min_hostCount': calculate_min(host_counts),
        'moyenne_linkCount': calculate_average(link_counts) if link_counts else "URLs indispo Babbar",
        'max_linkCount': calculate_max(link_counts),
        'min_linkCount': calculate_min(link_counts),
    }

    # Ajustement pour les cas où il n'y a pas de données disponibles
    for key in ['domainCount', 'hostCount', 'linkCount']:
        if not any([safe_int(result.get(key, 0)) for result in results]):
            stats[f'moyenne_{key}'] = "URLs indispo Babbar"
            stats[f'max_{key}'] = "N/A"
            stats[f'min_{key}'] = "N/A"

    return stats

def calculate_average(lst):
    """Calcule la moyenne d'une liste de nombres."""
    return round(sum(lst) / len(lst), 2) if lst else 0

def calculate_max(lst):
    """Trouve le maximum dans une liste de nombres."""
    return max(lst) if lst else 0

def calculate_min(lst):
    """Trouve le minimum dans une liste de nombres."""
    return min(lst) if lst else 0


# Route GET pour le formulaire de vérification des mots-clés
@router.get("/check-keywords")
async def check_keywords_form(request: Request):
    print("Affichage du formulaire de vérification des mots-clés...")
    return templates.TemplateResponse("check-keywords.html", {"request": request})

def get_url_overview(babbar_api_token, url, max_attempts=3, delay_between_attempts=60):  
    api_url = "https://www.babbar.tech/api/url/overview/main"
    headers = {
        "Authorization": f"Bearer {babbar_api_token}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
    payload = {"url": url}

    for attempt in range(max_attempts):
        response = requests.post(api_url, headers=headers, json=payload)
        if response.status_code == 200:
            data = response.json()
            backlinks = data.get("backlinks", {})
            return {
                "domainCount": backlinks.get("domainCount", "Non disponible"),
                "hostCount": backlinks.get("hostCount", "Non disponible"),
                "linkCount": backlinks.get("linkCount", "Non disponible"),
            }
        elif response.status_code == 404:  # Spécifiquement pour gérer le code de statut 404
            print("URL non trouvée dans la base de données de Babbar.")
            return {
                "error": "URL non trouvée BDD de Babbar",  # Message spécifique pour l'erreur 404
                "domainCount": "URLs indispo Babbar",
                "hostCount": "URLs indispo Babbar",
                "linkCount": "URLs indispo Babbar",
            }
        else:
            print(f"Tentative {attempt + 1}/{max_attempts}: Erreur lors de l'appel de l'API Babbar: {response.status_code}, Réponse: {response.text}")
            if response.status_code == 429:  # Code pour "Too Many Attempts."
                print("Attendre pour respecter la limite de taux d'appel...")
            time.sleep(delay_between_attempts)  # Attendre avant de réessayer pour les autres erreurs

    print("Échec après plusieurs tentatives.")
    return None
