# Contrat de données — SenMarket

## 1. Décisions structurantes

1. **Granularité**  
   - Une ligne de `commandes` = une commande (panier).  
   - Une ligne de `lignes_commande` = un produit dans une commande.  
   - Le montant total d’une commande = somme des `montant_xof` de ses lignes.

2. **Identifiants**  
   Identifiants texte stables avec préfixe + 7 chiffres :  
   `CLI0000001`, `VEN0000001`, `PRD0000001`, `CMD0000001`,  
   `LIG0000001`, `PAI0000001`, `AVI0000001`, `NAV0000001`.  
   Les noms ne sont jamais utilisés comme clés.

3. **Prix**  
   - `prix_catalogue_xof` dans `produits` (peut changer).  
   - `prix_unitaire_xof` et `montant_xof` dans `lignes_commande` = prix réellement payé (peut différer du catalogue de ±10 %).

---

## 2. Tables

| Table              | Clé primaire          | Colonnes principales                                                                 | Relations |
|--------------------|-----------------------|--------------------------------------------------------------------------------------|---------|
| clients            | client_id             | nom_client, email, telephone, ville, region, date_inscription                        | - |
| vendeurs           | vendeur_id            | nom_vendeur, ville, region                                                           | - |
| produits           | produit_id            | nom_produit, categorie, vendeur_id, prix_catalogue_xof, actif                        | vendeur_id → vendeurs |
| commandes          | commande_id           | client_id, date_commande, statut                                                     | client_id → clients |
| lignes_commande    | ligne_commande_id     | commande_id, produit_id, quantite, prix_unitaire_xof, montant_xof                    | commande_id → commandes<br>produit_id → produits |
| paiements          | paiement_id           | commande_id, methode_paiement, statut_paiement, montant_xof, date_paiement           | commande_id → commandes |
| avis               | avis_id               | client_id, produit_id, commande_id, note, date_avis                                  | client_id → clients<br>produit_id → produits<br>commande_id → commandes |
| navigation         | evenement_id          | session_id, client_id, produit_id, type_evenement, date_evenement                    | client_id → clients (facultatif)<br>produit_id → produits (facultatif) |

---

## 3. Règles métier importantes

- Montants toujours en **entiers** (XOF, pas de centimes).
- `montant_xof` = `quantite` × `prix_unitaire_xof`.
- `date_commande` ≥ `date_inscription`.
- Statuts commandes : `livree`, `expediee`, `en_cours`, `annulee`.
- Méthodes paiement : `wave`, `orange_money`, `carte`, `especes`.
- Note avis : 1 à 5.
- Types navigation : `vue_produit`, `ajout_panier`, `debut_paiement`.

**Colonnes interdites pour l’instant** (créées au Module 1) :  
`stock`, `commentaire`, `reference_transaction`.