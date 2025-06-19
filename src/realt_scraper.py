from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
import time
import configparser
import os
import requests
from webdriver_manager.chrome import ChromeDriverManager
from utils import parse_invoice_pdf, store_invoice_data, load_config  # Ajouter ces imports
# Importer la bibliothèque pour générer des User-Agents aléatoires
from fake_useragent import UserAgent
ua = UserAgent()

# Load configuration
config = load_config()

# Configure Chrome options for robust headless operation
chrome_options = Options()
chrome_options.add_argument('--headless')
chrome_options.add_argument('--disable-gpu')
chrome_options.add_argument('--disable-dev-shm-usage')
chrome_options.add_argument('--no-sandbox')
chrome_options.add_argument('--remote-debugging-port=9222')

chrome_options.add_argument(f"user-agent={ua.chrome}")
chrome_options.add_argument("--window-size=1920,1080")
chrome_options.add_argument("--start-maximized")

#chrome_options.add_argument('--incognito')
# chrome_options.add_argument('--disable-extensions')
# chrome_options.add_argument('--disable-popup-blocking')
# chrome_options.add_argument('--disable-software-rasterizer')
# chrome_options.add_experimental_option('excludeSwitches', ['enable-automation'])
# chrome_options.add_experimental_option('detach', False)

try:
    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=chrome_options
    )
except Exception as e:
    print(f"Erreur lors du lancement de Chrome/Chromium : {e}")
    raise

try:
    # 1. Aller sur la page de login
    driver.get("https://realt.co/my-account/")
    print("Page de login chargée :", driver.current_url)
    # 2. Attendre que le formulaire de login soit présent (plus robuste)
    try:
        WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "form.woocommerce-form-login"))
        )
        print("Formulaire de login trouvé.")
        driver.save_screenshot("debug_login_form.png")
        
        # Gérer le bandeau de cookies s'il est présent
        try:
            cookie_accept_btn = WebDriverWait(driver, 3).until(
                EC.element_to_be_clickable((By.ID, "CybotCookiebotDialogBodyLevelButtonLevelOptinAllowAll"))
            )
            print("Bandeau de cookies détecté, tentative d'acceptation...")
            driver.save_screenshot("debug_cookie_banner.png")
            cookie_accept_btn.click()
            time.sleep(1)  # Attendre que le bandeau disparaisse
            print("Bandeau de cookies accepté.")
            driver.save_screenshot("debug_post_cookie.png")
        except Exception as e:
            print("Pas de bandeau de cookies ou déjà accepté:", e)
        
        username = driver.find_element(By.ID, "username")
        password = driver.find_element(By.ID, "password")
    except Exception as e:
        print("Erreur lors de l'attente du formulaire de connexion :", e)
        driver.save_screenshot("debug_login.png")
        print(driver.page_source)
        driver.quit()
        exit(1)
    my_user = config['DEFAULT']['username']
    my_pwd = config['DEFAULT']['password']
    username.send_keys(my_user)
    password.send_keys(my_pwd)

    # 3. Cliquer sur le bouton "Log in"
    login_btn = driver.find_element(By.NAME, "login")
    login_btn.click()
    print("Tentative de connexion...")
    time.sleep(2)  # Attendre que la page se charge
    #driver.save_screenshot("debug_post_login.png")

    # Vérifier si un message d'erreur de login est présent
    error_msg = driver.find_elements(By.CSS_SELECTOR, "ul.woocommerce-error li")
    if error_msg:  # Si un message d'erreur est trouvé
        error_text = error_msg[0].text
        print("Erreur de connexion détectée:", error_text)
        driver.save_screenshot("debug_login_error.png")
        driver.quit()
        raise Exception("Identifiants invalides")
    
    print("Connexion réussie, attente de la redirection...")
    time.sleep(5)  # Attendre que la session soit bien établie

    # Fonction pour récupérer les liens des factures sur une page
    def get_invoice_links():
        try:
            invoice_links = WebDriverWait(driver, 5).until(
                lambda d: d.find_elements(By.CSS_SELECTOR, "a.woocommerce-button.button.invoice")
            )
            return [link.get_attribute("href") for link in invoice_links]
        except Exception as e:
            print(f"Erreur lors de la récupération des factures sur cette page: {e}")
            return []

    # Fonction pour vérifier s'il y a une page suivante
    def has_next_page():
        try:
            next_button = driver.find_element(By.CSS_SELECTOR, "a.next.page-numbers")
            return next_button.get_attribute("href")
        except:
            return None

    # Liste pour stocker tous les liens de factures
    all_invoice_links = []
    current_page = 1

    while True:
        # Aller à la page des commandes (avec le numéro de page si > 1)
        url = "https://realt.co/my-account/orders/"
        if current_page > 1:
            url += str(current_page)
        url += "?order_sort_by=&order_sort_dir=&order_filter_by=status&order_filter_val=wc-completed"
        
        print(f"\nNavigation vers la page {current_page}...")
        driver.get(url)
        time.sleep(2)  # Attendre le chargement de la page
        #driver.save_screenshot(f"debug_orders_page_{current_page}.png")

        # Récupérer les liens des factures de la page courante
        try:
            page_links = get_invoice_links()
            print(f"Factures trouvées sur la page {current_page}: {len(page_links)}")
        except Exception as e:
            print(f"Erreur lors de la récupération des factures page {current_page}:", e)
            driver.save_screenshot(f"debug_orders_page_{current_page}_error.png")
            page_links = []

        all_invoice_links.extend(page_links)

        # Vérifier s'il y a une page suivante
        next_page_url = has_next_page()
        if not next_page_url:
            print("Plus de pages suivantes.")
            break
            
        current_page += 1

    print(f"\nNombre total de factures trouvées: {len(all_invoice_links)}")

    # Configuration de la session requests pour le téléchargement
    session_cookies = driver.get_cookies()
    s = requests.Session()
    
    # Copier les cookies Selenium
    for c in session_cookies:
        s.cookies.set(c['name'], c['value'])
    
    # Configuration complète des headers
    user_agent = driver.execute_script("return navigator.userAgent;")
    headers = {
        'User-Agent': user_agent,
        'Accept': 'application/pdf,application/x-pdf,application/octet-stream,*/*',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Referer': 'https://realt.co/my-account/orders/',
        'Origin': 'https://realt.co',
        'sec-ch-ua': '"Chromium";v="112"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Linux"',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'same-origin',
        'DNT': '1'
    }
    s.headers.update(headers)

    # Créer un dossier pour les factures s'il n'existe pas
    download_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'invoices')
    os.makedirs(download_dir, exist_ok=True)

    # Télécharger toutes les factures
    for i, href in enumerate(all_invoice_links, 1):
        print(f"\nTéléchargement de la facture {i}/{len(all_invoice_links)}")
        print(f"URL: {href}")
        
        try:
            r = s.get(href, allow_redirects=True)
            print(f"Status code: {r.status_code}")
            
            if r.status_code == 200:
                # Extraire l'ID de la commande de l'URL
                order_id = href.split('order_ids=')[1].split('&')[0]
                filename = f"invoice_{order_id}.pdf"
                filepath = os.path.join(download_dir, filename)
                
                # Vérifier si le contenu est bien un PDF
                if b'%PDF-' in r.content[:1024]:
                    with open(filepath, "wb") as f:
                        f.write(r.content)
                    print(f"Facture sauvegardée: {filename}")
                    
                    # Analyser et stocker les données de la facture
                    try:
                        invoice_data = parse_invoice_pdf(filepath)
                        store_invoice_data(invoice_data)
                        print(f"Données de la facture {order_id} extraites et stockées avec succès")
                    except Exception as e:
                        print(f"Erreur lors de l'analyse de la facture {order_id}: {e}")
                else:
                    print(f"Le contenu téléchargé n'est pas un PDF valide")
                    error_file = f"debug_download_error_{order_id}.html"
                    with open(error_file, "wb") as f:
                        f.write(r.content)
                    print(f"Contenu de l'erreur sauvegardé dans {error_file}")
            else:
                print(f"Échec du téléchargement: {r.status_code}")
                driver.save_screenshot(f"debug_download_error_{order_id}.png")
                
        except Exception as e:
            print(f"Erreur lors du téléchargement: {e}")
            
        time.sleep(1)  # Petit délai entre les téléchargements
finally:
    driver.quit()
