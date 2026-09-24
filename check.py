"""Veille stock Apple Refurb - MacBook Pro 14 M5 Pro (FGDR4F/A).
Vérifie si le bouton « Ajouter au panier » est cliquable (isBuyable) et envoie un email
uniquement au passage indisponible -> disponible."""
import json, os, smtplib, sys, urllib.request
from datetime import datetime
from email.mime.text import MIMEText
from zoneinfo import ZoneInfo

PART = "FGDR4F/A"
API = f"https://www.apple.com/fr/shop/delivery-message?parts.0={PART}&mts.0=regular&mts.1=compact"
PRODUCT_URL = ("https://www.apple.com/fr/shop/product/fgdr4f/a/MacBook-Pro-14-pouces-reconditionn%C3%A9-avec-puce-"
               "Apple-M5-Pro-CPU-15-c%C5%93urs-et-GPU-16-c%C5%93urs-Noir-sid%C3%A9ral")
STATE_FILE = "state.json"
FORCE_TEST = os.environ.get("FORCE_TEST", "false").lower() == "true"


def find(obj, key):
    if isinstance(obj, dict):
        if key in obj:
            return obj[key]
        obj = list(obj.values())
    if isinstance(obj, list):
        for v in obj:
            r = find(v, key)
            if r is not None:
                return r
    return None


def fetch():
    req = urllib.request.Request(API, headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0 Safari/537.36",
        "Accept": "application/json",
        "Accept-Language": "fr-FR,fr;q=0.9",
    })
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode("utf-8"))


def send_mail(subject, html):
    user, pwd, to = os.environ["GMAIL_USER"], os.environ["GMAIL_APP_PASSWORD"], os.environ["MAIL_TO"]
    msg = MIMEText(html, "html", "utf-8")
    msg["Subject"], msg["From"], msg["To"] = subject, user, to
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as s:
        s.login(user, pwd)
        s.sendmail(user, [a.strip() for a in to.split(",")], msg.as_string())


def main():
    now = datetime.now(ZoneInfo("Europe/Paris")).strftime("%d/%m/%Y à %H:%M:%S")
    data = fetch()
    raw = find(data, "isBuyable")
    if raw is None:
        sys.exit("Champ isBuyable introuvable : API Apple modifiée ou requête bloquée")
    buyable = raw is True or str(raw).lower() == "true"
    reason = find(data, "reason") or ""
    delivery = find(data, "displayName") or ""

    try:
        state = json.load(open(STATE_FILE))
    except Exception:
        state = {}
    was = state.get("buyable", False)
    print(f"{now} | isBuyable={buyable} reason={reason} livraison={delivery} | précédent={was}")

    if (buyable and not was) or FORCE_TEST:
        tag = "[TEST] " if FORCE_TEST else ""
        statut = "✅ cliquable" if buyable else "❌ non cliquable"
        html = f"""<p>Salut Paul,</p>
<p>{'<i>Email de test : la veille fonctionne.</i><br>' if FORCE_TEST else ''}Le <b>MacBook Pro 14 pouces reconditionné M5 Pro</b> (CPU 15 cœurs, GPU 16 cœurs, 24 Go, 1 To, noir sidéral) à <b>2 459 €</b> :</p>
<ul>
<li><b>Vérifié le :</b> {now} (heure de Paris)</li>
<li><b>Bouton « Ajouter au panier » :</b> {statut} (isBuyable = {str(buyable).lower()}{', ' + reason if reason else ''})</li>
<li><b>Livraison :</b> {delivery}</li>
</ul>
<p>👉 <a href="{PRODUCT_URL}">Ouvrir la page produit Apple</a></p>
<p>Fred</p>"""
        send_mail(f"{tag}🟢 MacBook Pro 14\" M5 Pro reconditionné — Ajouter au panier {statut}", html)
        print("Email envoyé")

    if buyable != was:  # n'écrit l'état que s'il change (pas de commit toutes les 10 min)
        json.dump({"buyable": buyable, "changed_at": now}, open(STATE_FILE, "w"), ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
