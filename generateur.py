"""
Générateur de données SenMarket - Module 0
Génère d'abord une vérité propre, puis injecte des défauts contrôlés.
"""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from faker import Faker

from src.senmarket.chemins import ensure_dirs, raw_dir

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

VILLES = {
    "Dakar": ("Dakar", 0.32),
    "Pikine": ("Dakar", 0.08),
    "Guédiawaye": ("Dakar", 0.05),
    "Rufisque": ("Dakar", 0.04),
    "Thiès": ("Thiès", 0.09),
    "Touba": ("Diourbel", 0.07),
    "Saint-Louis": ("Saint-Louis", 0.05),
    "Kaolack": ("Kaolack", 0.05),
    "Ziguinchor": ("Ziguinchor", 0.04),
    "Mbour": ("Thiès", 0.04),
    "Diourbel": ("Diourbel", 0.03),
    "Louga": ("Louga", 0.03),
    "Tambacounda": ("Tambacounda", 0.03),
    "Kolda": ("Kolda", 0.02),
    "Fatick": ("Fatick", 0.02),
    "Matam": ("Matam", 0.02),
    "Kaffrine": ("Kaffrine", 0.01),
    "Kédougou": ("Kédougou", 0.01),
    "Sédhiou": ("Sédhiou", 0.01),
}

CATEGORIES = {
    "Telephonie": ["Samsung A15", "iPhone 13", "Tecno Spark", "Infinix Hot", "Redmi Note"],
    "Tissus & Mode": ["Bazin riche", "Wax hollandais", "Boubou brodé", "Sandales cuir", "Sac en cuir"],
    "Alimentation": ["Riz brisé 25kg", "Huile 5L", "Lait en poudre", "Sucre 1kg", "Thé Attaya"],
    "Maison": ["Matelas mousse", "Ventilateur", "Gaz 6kg", "Casserole inox", "Seau plastique"],
    "Electromenager": ["Réfrigérateur", "Machine à laver", "Micro-ondes", "Fer à repasser", "Mixeur"],
    "Beaute": ["Crème Nivea", "Huile de coco", "Parfum", "Savon de Marseille", "Dentifrice"],
}

PRENOMS = [
    "Awa", "Fatou", "Aïssatou", "Ndèye", "Mariama", "Khady", "Astou", "Bineta",
    "Moussa", "Ibrahima", "Cheikh", "Ousmane", "Mamadou", "Modou", "Papa", "Amadou",
    "Sokhna", "Adama", "Lamine", "Seydou", "Pape", "Abdoulaye", "Omar", "Youssou"
]

NOMS = [
    "Diallo", "Ndiaye", "Sow", "Ba", "Diop", "Sarr", "Fall", "Gueye",
    "Mbaye", "Cissé", "Thiam", "Kane", "Sy", "Faye", "Seck", "Diouf",
    "Sène", "Wade", "Camara", "Touré", "Keita", "Traoré", "Samb", "Ndour"
]

METHODES_PAIEMENT = ["wave", "orange_money", "carte", "especes"]
STATUTS_COMMANDE = ["livree", "expediee", "en_cours", "annulee"]
STATUTS_PAIEMENT = ["reussi", "echoue", "en_attente"]
TYPES_NAV = ["vue_produit", "ajout_panier", "debut_paiement"]


def _seed_from(run_date: str, base_seed: int = 42) -> int:
    """Graine stable dérivée de la date + seed de base."""
    h = hashlib.md5(f"{base_seed}-{run_date}".encode()).hexdigest()
    return int(h[:8], 16)


def _id(prefix: str, n: int) -> str:
    return f"{prefix}{n:07d}"


# ---------------------------------------------------------------------------
# Génération de la vérité
# ---------------------------------------------------------------------------

def generer_verite(
    run_date: str,
    n_lignes: int = 10_000,
    n_jours: int = 365,
    seed: int = 42,
) -> dict[str, pd.DataFrame]:
    """Génère un jeu parfaitement cohérent (la vérité)."""
    rng = np.random.default_rng(_seed_from(run_date, seed))
    fake = Faker("fr_FR")
    Faker.seed(_seed_from(run_date, seed))

    date_fin = datetime.strptime(run_date, "%Y-%m-%d").date()
    date_debut = date_fin - timedelta(days=n_jours)

    # --- Vendeurs (20) ---
    n_vendeurs = 20
    vendeurs = pd.DataFrame({
        "vendeur_id": [_id("VEN", i) for i in range(1, n_vendeurs + 1)],
        "nom_vendeur": [f"{rng.choice(PRENOMS)} {rng.choice(NOMS)}" for _ in range(n_vendeurs)],
        "ville": rng.choice(list(VILLES.keys()), size=n_vendeurs),
    })
    vendeurs["region"] = vendeurs["ville"].map(lambda v: VILLES[v][0])

    # --- Produits (40) ---
    produits_list = []
    pid = 1
    for cat, noms in CATEGORIES.items():
        for nom in noms:
            produits_list.append({
                "produit_id": _id("PRD", pid),
                "nom_produit": nom,
                "categorie": cat,
                "vendeur_id": _id("VEN", rng.integers(1, n_vendeurs + 1)),
                "prix_catalogue_xof": int(rng.integers(1000, 500_001)),
                "actif": True,
            })
            pid += 1
    produits = pd.DataFrame(produits_list)

    # --- Clients ---
    n_clients = max(int(n_lignes / 3), 500)
    villes_list = list(VILLES.keys())
    probs_ville = np.array([VILLES[v][1] for v in villes_list])
    probs_ville /= probs_ville.sum()

    clients = pd.DataFrame({
        "client_id": [_id("CLI", i) for i in range(1, n_clients + 1)],
        "nom_client": [f"{rng.choice(PRENOMS)} {rng.choice(NOMS)}" for _ in range(n_clients)],
        "email": [fake.email() for _ in range(n_clients)],
        "telephone": [f"+221 7{rng.integers(0, 10)}{rng.integers(1000000, 9999999)}" for _ in range(n_clients)],
        "ville": rng.choice(villes_list, size=n_clients, p=probs_ville),
        "date_inscription": [
            date_debut + timedelta(days=int(rng.integers(0, n_jours - 30)))
            for _ in range(n_clients)
        ],
    })
    clients["region"] = clients["ville"].map(lambda v: VILLES[v][0])

    # --- Commandes ---
    n_commandes = max(int(n_lignes / 2.5), 400)
    # Quelques gros clients
    poids_clients = rng.exponential(1.0, size=n_clients)
    poids_clients /= poids_clients.sum()

    commandes = pd.DataFrame({
        "commande_id": [_id("CMD", i) for i in range(1, n_commandes + 1)],
        "client_id": rng.choice(clients["client_id"], size=n_commandes, p=poids_clients),
        "date_commande": [
            date_debut + timedelta(days=int(rng.integers(0, n_jours)))
            for _ in range(n_commandes)
        ],
        "statut": rng.choice(STATUTS_COMMANDE, size=n_commandes, p=[0.55, 0.20, 0.15, 0.10]),
    })

    # Garantir date_commande >= date_inscription
    clients_dates = clients.set_index("client_id")["date_inscription"]
    commandes["date_inscription"] = commandes["client_id"].map(clients_dates)
    mask = commandes["date_commande"] < commandes["date_inscription"]
    commandes.loc[mask, "date_commande"] = commandes.loc[mask, "date_inscription"]
    commandes = commandes.drop(columns=["date_inscription"])

    # --- Lignes de commande ---
    # Nombre de lignes par commande (1 à 5, biaisé vers 1-2)
    n_lignes_par_cmd = rng.choice([1, 2, 3, 4, 5], size=n_commandes, p=[0.55, 0.25, 0.12, 0.05, 0.03])
    total_lignes = n_lignes_par_cmd.sum()

    lignes = []
    lid = 1
    for i, (cmd_id, n_lig) in enumerate(zip(commandes["commande_id"], n_lignes_par_cmd)):
        prods = rng.choice(produits["produit_id"], size=n_lig, replace=False)
        for prod_id in prods:
            prix_cat = produits.loc[produits["produit_id"] == prod_id, "prix_catalogue_xof"].iloc[0]
            # Prix payé = catalogue ±10 %
            facteur = rng.uniform(0.90, 1.10)
            prix_unit = max(100, int(prix_cat * facteur))
            qte = int(rng.choice([1, 2, 3, 4, 5], p=[0.55, 0.25, 0.12, 0.05, 0.03]))
            lignes.append({
                "ligne_commande_id": _id("LIG", lid),
                "commande_id": cmd_id,
                "produit_id": prod_id,
                "quantite": qte,
                "prix_unitaire_xof": prix_unit,
                "montant_xof": qte * prix_unit,
            })
            lid += 1
    lignes_commande = pd.DataFrame(lignes)

    # --- Paiements ---
    # ~98 % des commandes ont un paiement, ~2 % sans
    cmd_avec_paiement = commandes["commande_id"].sample(frac=0.98, random_state=seed).values
    montants_cmd = lignes_commande.groupby("commande_id")["montant_xof"].sum()

    paiements = []
    pid = 1
    for cmd_id in cmd_avec_paiement:
        montant = int(montants_cmd.get(cmd_id, 0))
        # ~1 % d'écart volontaire
        if rng.random() < 0.01:
            montant = int(montant * rng.uniform(0.95, 1.05))
        paiements.append({
            "paiement_id": _id("PAI", pid),
            "commande_id": cmd_id,
            "methode_paiement": rng.choice(METHODES_PAIEMENT, p=[0.45, 0.35, 0.08, 0.12]),
            "statut_paiement": rng.choice(STATUTS_PAIEMENT, p=[0.90, 0.06, 0.04]),
            "montant_xof": montant,
            "date_paiement": commandes.loc[commandes["commande_id"] == cmd_id, "date_commande"].iloc[0],
        })
        pid += 1
    paiements = pd.DataFrame(paiements)

    # --- Avis (~10 % des commandes livrées) ---
    cmd_livrees = commandes[commandes["statut"] == "livree"]["commande_id"]
    n_avis = max(int(len(cmd_livrees) * 0.10), 50)
    avis_cmd = rng.choice(cmd_livrees, size=min(n_avis, len(cmd_livrees)), replace=False)

    avis = []
    aid = 1
    for cmd_id in avis_cmd:
        prods_cmd = lignes_commande.loc[lignes_commande["commande_id"] == cmd_id, "produit_id"]
        if len(prods_cmd) == 0:
            continue
        prod_id = rng.choice(prods_cmd)
        client_id = commandes.loc[commandes["commande_id"] == cmd_id, "client_id"].iloc[0]
        date_cmd = commandes.loc[commandes["commande_id"] == cmd_id, "date_commande"].iloc[0]
        avis.append({
            "avis_id": _id("AVI", aid),
            "client_id": client_id,
            "produit_id": prod_id,
            "commande_id": cmd_id,
            "note": int(rng.integers(1, 6)),
            "date_avis": date_cmd + timedelta(days=int(rng.integers(1, 15))),
        })
        aid += 1
    avis = pd.DataFrame(avis)

    # --- Navigation ---
    n_sessions = int(n_commandes * 1.8)
    navigation = []
    eid = 1
    for s in range(n_sessions):
        session_id = f"SES{s:07d}"
        client_id = rng.choice(clients["client_id"]) if rng.random() > 0.30 else None
        n_events = int(rng.choice([1, 2, 3], p=[0.50, 0.35, 0.15]))
        prods = rng.choice(produits["produit_id"], size=n_events)
        base_date = date_debut + timedelta(days=int(rng.integers(0, n_jours)))

        for i, prod_id in enumerate(prods):
            typ = TYPES_NAV[min(i, 2)]
            navigation.append({
                "evenement_id": _id("NAV", eid),
                "session_id": session_id,
                "client_id": client_id,
                "produit_id": prod_id,
                "type_evenement": typ,
                "date_evenement": datetime.combine(base_date, datetime.min.time()) + timedelta(minutes=i * 3),
            })
            eid += 1
            if typ == "debut_paiement":
                break
    navigation = pd.DataFrame(navigation)

    return {
        "clients": clients,
        "vendeurs": vendeurs,
        "produits": produits,
        "commandes": commandes,
        "lignes_commande": lignes_commande,
        "paiements": paiements,
        "avis": avis,
        "navigation": navigation,
    }


# ---------------------------------------------------------------------------
# Injection de défauts
# ---------------------------------------------------------------------------

def injecter_defauts(
    tables: dict[str, pd.DataFrame],
    defauts: list[str],
    taux: dict[str, float] | None = None,
    seed: int = 42,
) -> tuple[dict[str, pd.DataFrame], dict[str, int]]:
    """Injecte les défauts demandés. Retourne tables modifiées + bilan."""
    rng = np.random.default_rng(seed + 99)
    bilan: dict[str, int] = {}
    taux = taux or {}

    def _taux(nom: str, default: float) -> float:
        return taux.get(nom, default)

    # --- doublon_ligne ---
    if "doublon_ligne" in defauts or "tous" in defauts:
        t = _taux("doublon_ligne", 0.05)
        df = tables["lignes_commande"]
        n = max(1, int(len(df) * t))
        idx = rng.choice(df.index, size=n, replace=False)
        doublons = df.loc[idx].copy()
        tables["lignes_commande"] = pd.concat([df, doublons], ignore_index=True)
        bilan["doublon_ligne"] = n

    # --- valeurs_manquantes ---
    if "valeurs_manquantes" in defauts or "tous" in defauts:
        t = _taux("valeurs_manquantes", 0.08)
        for col, table in [
            ("nom_client", "clients"),
            ("email", "clients"),
            ("ville", "clients"),
            ("montant_xof", "lignes_commande"),
        ]:
            df = tables[table]
            n = max(1, int(len(df) * t))
            idx = rng.choice(df.index, size=n, replace=False)
            df.loc[idx, col] = np.nan
            bilan[f"valeurs_manquantes_{col}"] = n

    # --- date_future ---
    if "date_future" in defauts or "tous" in defauts:
        t = _taux("date_future", 0.02)
        df = tables["commandes"]
        n = max(1, int(len(df) * t))
        idx = rng.choice(df.index, size=n, replace=False)
        df.loc[idx, "date_commande"] = df.loc[idx, "date_commande"] + pd.Timedelta(days=30)
        bilan["date_future"] = n

    # --- montant_texte (on force object dtype) ---
    if "montant_texte" in defauts or "tous" in defauts:
        t = _taux("montant_texte", 0.03)
        df = tables["lignes_commande"]
        # Important : on convertit la colonne en object pour accepter les strings
        df["montant_xof"] = df["montant_xof"].astype(object)
        n = max(1, int(len(df) * t))
        # On ne prend que les lignes qui ont encore une vraie valeur numérique
        candidats = df[df["montant_xof"].notna()].index
        if len(candidats) > 0:
            idx = rng.choice(candidats, size=min(n, len(candidats)), replace=False)
            formats = ["{} FCFA", "{} F CFA", "{}.000 XOF"]
            for i in idx:
                val = df.loc[i, "montant_xof"]
                try:
                    val_int = int(float(val))
                    fmt = rng.choice(formats)
                    df.loc[i, "montant_xof"] = fmt.format(val_int)
                except (ValueError, TypeError):
                    continue
            bilan["montant_texte"] = len(idx)
        else:
            bilan["montant_texte"] = 0

    # --- outlier ---
    if "outlier" in defauts or "tous" in defauts:
        t = _taux("outlier", 0.01)
        df = tables["lignes_commande"]
        n = max(1, int(len(df) * t))
        # On ne touche que les lignes numériques
        if df["montant_xof"].dtype == object:
            candidats = df[df["montant_xof"].apply(lambda x: isinstance(x, (int, float)) and pd.notna(x))].index
        else:
            candidats = df.index
        if len(candidats) > 0:
            idx = rng.choice(candidats, size=min(n, len(candidats)), replace=False)
            df.loc[idx, "prix_unitaire_xof"] = 99_999_999
            # On met aussi montant en cohérence seulement s'il est encore numérique
            for i in idx:
                if isinstance(df.loc[i, "montant_xof"], (int, float)) or pd.api.types.is_number(df.loc[i, "montant_xof"]):
                    df.loc[i, "montant_xof"] = df.loc[i, "quantite"] * 99_999_999
            bilan["outlier"] = len(idx)
        else:
            bilan["outlier"] = 0

    # --- quantite_negative ---
    if "quantite_negative" in defauts or "tous" in defauts:
        t = _taux("quantite_negative", 0.01)
        df = tables["lignes_commande"]
        n = max(1, int(len(df) * t))
        idx = rng.choice(df.index, size=n, replace=False)
        df.loc[idx, "quantite"] = rng.choice([-1, 0])
        bilan["quantite_negative"] = n

    # --- paiement_orphelin ---
    if "paiement_orphelin" in defauts or "tous" in defauts:
        t = _taux("paiement_orphelin", 0.01)
        df = tables["paiements"]
        n = max(1, int(len(df) * t))
        idx = rng.choice(df.index, size=n, replace=False)
        df.loc[idx, "commande_id"] = "CMD9999999"
        bilan["paiement_orphelin"] = n

    return tables, bilan


# ---------------------------------------------------------------------------
# Écriture
# ---------------------------------------------------------------------------

def ecrire_brut(
    tables: dict[str, pd.DataFrame],
    run_date: str,
    bilan: dict[str, int] | None = None,
) -> Path:
    """Écrit les CSV bruts + bilan + log simulé."""
    ensure_dirs(run_date)
    out = raw_dir(run_date)
    out.mkdir(parents=True, exist_ok=True)

    for nom, df in tables.items():
        # Convertir dates en string pour CSV
        df = df.copy()
        for col in df.columns:
            if pd.api.types.is_datetime64_any_dtype(df[col]) or isinstance(df[col].dtype, pd.DatetimeTZDtype):
                df[col] = df[col].astype(str)
            elif df[col].dtype == object:
                # essayer de détecter des dates
                pass
        df.to_csv(out / f"{nom}.csv", index=False)

    # Bilan
    if bilan:
        pd.DataFrame([bilan]).to_csv(out / "bilan_generation.csv", index=False)

    # Log simulé
    log_path = out / "senmarket.log"
    n_total = sum(len(df) for df in tables.values())
    with open(log_path, "w") as f:
        f.write(f"{run_date} 10:23:45 INFO ingestion: {n_total} lignes chargées\n")
        f.write(f"{run_date} 10:23:46 WARN ingestion: valeurs manquantes détectées\n")
        f.write(f"{run_date} 10:23:47 ERROR ingestion: échec de connexion à l'API Wave\n")

    return out


def generer(
    run_date: str,
    n_lignes: int = 10_000,
    defauts: list[str] | None = None,
    seed: int = 42,
) -> Path:
    """Point d'entrée principal."""
    tables = generer_verite(run_date, n_lignes=n_lignes, seed=seed)
    bilan = {}
    if defauts:
        tables, bilan = injecter_defauts(tables, defauts, seed=seed)
    return ecrire_brut(tables, run_date, bilan)