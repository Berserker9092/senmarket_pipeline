"""
Pipeline Module 0 - SenMarket
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

# === Gestion des chemins (fonctionne que le package soit installé ou non) ===
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

# Essayer les différents emplacements possibles
try:
    from senmarket.generateur import generer
except ImportError:
    from generateur import generer

try:
    from senmarket.nettoyage import nettoyer, exporter_parquet
    from senmarket.chemins import raw_dir, processed_dir
except ImportError:
    from src.senmarket.nettoyage import nettoyer, exporter_parquet
    from src.senmarket.chemins import raw_dir, processed_dir


def charger_brut(run_date: str) -> dict[str, pd.DataFrame]:
    """Charge les CSV bruts."""
    dossier = raw_dir(run_date)
    tables = {}
    for nom in ["clients", "vendeurs", "produits", "commandes",
                "lignes_commande", "paiements", "avis", "navigation"]:
        path = dossier / f"{nom}.csv"
        if not path.exists():
            raise FileNotFoundError(f"Fichier manquant : {path}")
        tables[nom] = pd.read_csv(path)
    return tables


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-date", required=True, help="Date au format AAAA-MM-JJ")
    parser.add_argument("--generer", action="store_true", help="Générer les données brutes")
    parser.add_argument("--rows", type=int, default=10000, help="Nombre de lignes de commande")
    parser.add_argument("--defauts", nargs="*", default=["tous"], help="Liste des défauts")
    parser.add_argument("--sans-tests", action="store_true", help="Ne pas lancer les vérifications")
    args = parser.parse_args()

    run_date = args.run_date
    print(f"=== Pipeline SenMarket — {run_date} ===")

    # 1. Génération
    if args.generer:
        print(f"Génération de {args.rows} lignes...")
        generer(run_date, n_lignes=args.rows, defauts=args.defauts)
        print("Génération terminée.")

    # 2. Chargement
    print("Chargement des CSV bruts...")
    tables = charger_brut(run_date)

    # 3. Nettoyage
    print("Nettoyage...")
    tables_propres = nettoyer(tables, run_date)

    # 4. Export Parquet
    print("Export Parquet...")
    out = exporter_parquet(tables_propres, run_date)
    print(f"Parquet écrits dans : {out}")

    # 5. Contrôle rapide
    if not args.sans_tests:
        print("\n=== Contrôle qualité ===")
        for nom, df in tables_propres.items():
            print(f"{nom:<20} {len(df):>8} lignes")

        cles = {
            "clients": "client_id",
            "vendeurs": "vendeur_id",
            "produits": "produit_id",
            "commandes": "commande_id",
            "lignes_commande": "ligne_commande_id",
            "paiements": "paiement_id",
            "avis": "avis_id",
            "navigation": "evenement_id",
        }
        print("\nClés primaires uniques :")
        for nom, col in cles.items():
            unique = tables_propres[nom][col].is_unique
            print(f"  {nom}: {unique}")

    print("\nPipeline terminé avec succès.")


if __name__ == "__main__":
    main()