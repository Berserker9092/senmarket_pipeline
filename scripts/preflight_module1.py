"""
Contrôle de pré-vol Module 1
Vérifie que les données sont prêtes pour charger dans les bases.
"""

from pathlib import Path
import sys
import pandas as pd

# Ajout du chemin
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

try:
    from senmarket.chemins import processed_dir
except ImportError:
    from src.senmarket.chemins import processed_dir


CLES = {
    "clients": "client_id",
    "vendeurs": "vendeur_id",
    "produits": "produit_id",
    "commandes": "commande_id",
    "lignes_commande": "ligne_commande_id",
    "paiements": "paiement_id",
    "avis": "avis_id",
    "navigation": "evenement_id",
}

RELATIONS = [
    ("commandes", "client_id", "clients"),
    ("lignes_commande", "commande_id", "commandes"),
    ("lignes_commande", "produit_id", "produits"),
    ("paiements", "commande_id", "commandes"),
    ("avis", "produit_id", "produits"),
    ("avis", "client_id", "clients"),
    ("avis", "commande_id", "commandes"),
]


def main(run_date: str | None = None):
    partitions = sorted(Path("data/processed").glob("date=*"))
    if not partitions:
        print("Aucune partition trouvée dans data/processed/")
        sys.exit(1)

    if run_date:
        dossier = Path(f"data/processed/date={run_date}")
        if not dossier.exists():
            print(f"Partition {run_date} introuvable")
            sys.exit(1)
    else:
        dossier = partitions[-1]  # la plus récente

    print(f"Partition contrôlée : {dossier.name}")
    print("-" * 60)

    # Chargement
    tables = {}
    for nom in CLES:
        path = dossier / f"{nom}.parquet"
        if not path.exists():
            print(f"MANQUANT : {path}")
            sys.exit(1)
        tables[nom] = pd.read_parquet(path)

    # 1. Taille + clé primaire unique
    print("\n1. Tailles et clés primaires")
    all_ok = True
    for nom, df in tables.items():
        unique = df[CLES[nom]].is_unique
        status = "OK" if unique else "ÉCHEC"
        if not unique:
            all_ok = False
        print(f"  {nom:<18} {len(df):>8} lignes | clé unique : {status}")

    # 2. Clés étrangères orphelines
    print("\n2. Clés étrangères (orphelins)")
    for enfant, colonne, parent in RELATIONS:
        orphelins = ~tables[enfant][colonne].isin(tables[parent][CLES[parent]])
        nb = orphelins.sum()
        status = "OK" if nb == 0 else f"{nb} orphelin(s)"
        if nb > 0:
            all_ok = False
        print(f"  {enfant}.{colonne} → {parent} : {status}")

    # 3. Cohérence paiement vs lignes
    print("\n3. Cohérence montants")
    lignes = tables["lignes_commande"].groupby("commande_id")["montant_xof"].sum()
    paye = tables["paiements"].groupby("commande_id")["montant_xof"].sum()
    comparaison = pd.concat([lignes, paye], axis=1, keys=["lignes", "paye"]).dropna()
    if len(comparaison) > 0:
        egal = (comparaison["lignes"] == comparaison["paye"]).mean()
        print(f"  Paiement = somme des lignes : {egal:.1%}")
    else:
        print("  Aucune commande en commun pour comparer")

    # 4. Colonnes que Module 1 va ajouter (doivent être absentes)
    print("\n4. Colonnes réservées Module 1 (doivent être absentes)")
    for table, colonne in [("produits", "stock"), ("avis", "commentaire"), ("paiements", "reference_transaction")]:
        present = colonne in tables[table].columns
        status = "Présent (à supprimer)" if present else "Absent (OK)"
        if present:
            all_ok = False
        print(f"  {table}.{colonne} : {status}")

    print("\n" + "=" * 60)
    if all_ok:
        print("Pré-vol OK — prêt pour Module 1")
    else:
        print("Pré-vol avec des problèmes — corrige avant Module 1")
    print("=" * 60)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-date", default=None)
    args = parser.parse_args()
    main(args.run_date)