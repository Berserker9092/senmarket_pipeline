"""
Nettoyage des données SenMarket - Module 0
"""

from __future__ import annotations

import re
from pathlib import Path

import numpy as np
import pandas as pd

from senmarket.chemins import processed_dir, rejected_dir, ensure_dirs


def _to_int_safe(val):
    """Convertit un montant (même texte) en entier."""
    if pd.isna(val):
        return np.nan
    if isinstance(val, (int, float, np.integer, np.floating)):
        return int(val)
    s = str(val).upper()
    # Enlever tout sauf les chiffres
    chiffres = re.sub(r"[^\d]", "", s)
    if chiffres:
        return int(chiffres)
    return np.nan


def nettoyer(tables: dict[str, pd.DataFrame], run_date: str) -> dict[str, pd.DataFrame]:
    """
    Nettoie les 8 tables.
    - Corrige ce qui peut l'être
    - Met en quarantaine ce qui doit être rejeté
    - Retourne les tables propres
    """
    ensure_dirs(run_date)
    rejected_path = rejected_dir(run_date)
    rejected_path.mkdir(parents=True, exist_ok=True)

    clients = tables["clients"].copy()
    vendeurs = tables["vendeurs"].copy()
    produits = tables["produits"].copy()
    commandes = tables["commandes"].copy()
    lignes = tables["lignes_commande"].copy()
    paiements = tables["paiements"].copy()
    avis = tables["avis"].copy()
    navigation = tables["navigation"].copy()

    # ------------------------------------------------------------------
    # 1. Clients
    # ------------------------------------------------------------------
    clients["nom_client"] = clients["nom_client"].fillna("Inconnu")
    clients["ville"] = clients["ville"].fillna("Inconnue")
    clients["region"] = clients["region"].fillna("Inconnue")
    # email reste vide si manquant
    clients["email"] = clients["email"].fillna("")

    # ------------------------------------------------------------------
    # 2. Lignes de commande
    # ------------------------------------------------------------------
    # Convertir montant_texte → entier
    lignes["montant_xof"] = lignes["montant_xof"].apply(_to_int_safe)

    # Recalculer les montants manquants
    mask_montant_nan = lignes["montant_xof"].isna()
    lignes.loc[mask_montant_nan, "montant_xof"] = (
        lignes.loc[mask_montant_nan, "quantite"] * lignes.loc[mask_montant_nan, "prix_unitaire_xof"]
    )

    # Rejeter quantités invalides
    mask_qte = lignes["quantite"] <= 0
    lignes_rejetees_qte = lignes[mask_qte].copy()
    lignes = lignes[~mask_qte]

    # Rejeter outliers de prix
    mask_outlier = lignes["prix_unitaire_xof"] >= 50_000_000
    lignes_rejetees_outlier = lignes[mask_outlier].copy()
    lignes = lignes[~mask_outlier]

    # Supprimer les doublons exacts (on garde la première occurrence)
    lignes = lignes.drop_duplicates(subset=["ligne_commande_id"], keep="first")

    # ------------------------------------------------------------------
    # 3. Commandes – rejeter les dates futures
    # ------------------------------------------------------------------
    run_dt = pd.to_datetime(run_date)
    commandes["date_commande"] = pd.to_datetime(commandes["date_commande"], errors="coerce")
    mask_future = commandes["date_commande"] > run_dt
    commandes_futures = commandes[mask_future]["commande_id"].tolist()

    # On garde les commandes valides
    commandes = commandes[~mask_future]

    # Effet cascade : supprimer les lignes / paiements / avis liés aux commandes futures
    if commandes_futures:
        lignes = lignes[~lignes["commande_id"].isin(commandes_futures)]
        paiements = paiements[~paiements["commande_id"].isin(commandes_futures)]
        avis = avis[~avis["commande_id"].isin(commandes_futures)]

    # ------------------------------------------------------------------
    # 4. Paiements – rejeter les orphelins
    # ------------------------------------------------------------------
    commandes_ids = set(commandes["commande_id"])
    mask_orphelin = ~paiements["commande_id"].isin(commandes_ids)
    paiements_orphelins = paiements[mask_orphelin].copy()
    paiements = paiements[~mask_orphelin]

    # ------------------------------------------------------------------
    # 5. Avis – sécurité (client + produit + commande existent)
    # ------------------------------------------------------------------
    avis = avis[
        avis["commande_id"].isin(commandes_ids)
        & avis["produit_id"].isin(produits["produit_id"])
        & avis["client_id"].isin(clients["client_id"])
    ]

    # ------------------------------------------------------------------
    # 6. Sauvegarder les rejets (optionnel mais propre)
    # ------------------------------------------------------------------
    if not lignes_rejetees_qte.empty:
        lignes_rejetees_qte.to_csv(rejected_path / "lignes_quantite_invalide.csv", index=False)
    if not lignes_rejetees_outlier.empty:
        lignes_rejetees_outlier.to_csv(rejected_path / "lignes_outlier.csv", index=False)
    if not paiements_orphelins.empty:
        paiements_orphelins.to_csv(rejected_path / "paiements_orphelins.csv", index=False)

    return {
        "clients": clients,
        "vendeurs": vendeurs,
        "produits": produits,
        "commandes": commandes,
        "lignes_commande": lignes,
        "paiements": paiements,
        "avis": avis,
        "navigation": navigation,
    }


def exporter_parquet(tables: dict[str, pd.DataFrame], run_date: str) -> Path:
    """Exporte les 8 tables en Parquet."""
    out = processed_dir(run_date)
    out.mkdir(parents=True, exist_ok=True)

    for nom, df in tables.items():
        # Convertir les dates proprement
        df = df.copy()
        for col in df.columns:
            if "date" in col.lower():
                df[col] = pd.to_datetime(df[col], errors="coerce")
        df.to_parquet(out / f"{nom}.parquet", index=False)

    return out