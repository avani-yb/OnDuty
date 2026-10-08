"""Localités du Cameroun proposées pour l'origine et la destination.

Source unique : le serveur valide les saisies avec cette liste et la
transmet à l'application (GET /api/localites/), qui oblige l'utilisateur à
choisir une localité de la liste. Le matching compare ainsi des noms
identiques, sans faute de frappe.

Liste : chefs-lieux des 58 départements et principales villes de chaque
région. Pour ajouter une localité, il suffit de l'ajouter ici.
"""

import unicodedata

LOCALITES = {
    "Adamaoua": [
        "Ngaoundéré", "Tibati", "Tignère", "Banyo", "Meiganga", "Ngaoundal", "Mbé",
        "Belel", "Nyambaka", "Martap", "Mayo-Darlé", "Kontcha", "Galim-Tignère",
        "Dir", "Djohong", "Ngaoui", "Bankim", "Mayo-Baléo",
    ],
    "Centre": [
        "Yaoundé", "Akonolinga", "Bafia", "Ntui", "Eséka", "Mbalmayo", "Mfou",
        "Ngoumou", "Monatélé", "Nanga-Eboko", "Obala", "Saa", "Okola", "Soa",
        "Akono", "Ayos", "Mbandjock", "Minta", "Yoko", "Makénéné", "Ombessa",
        "Bokito", "Ndikiniméki", "Esse", "Awaé", "Ebebda", "Evodoula",
        "Elig-Mfomo", "Nkoteng", "Ngomedzap", "Matomb", "Messondo", "Makak",
        "Dzeng", "Endom",
    ],
    "Est": [
        "Bertoua", "Batouri", "Yokadouma", "Abong-Mbang", "Bélabo", "Garoua-Boulaï",
        "Bétaré-Oya", "Doumé", "Lomié", "Moloundou", "Kenzou", "Ndélélé",
        "Mindourou", "Messamena", "Dimako", "Diang", "Ngoura", "Mandjou",
        "Nguélémendouka",
    ],
    "Extrême-Nord": [
        "Maroua", "Kousséri", "Yagoua", "Kaélé", "Mokolo", "Mora", "Mindif", "Bogo",
        "Pette", "Moulvoudaye", "Guidiguis", "Doukoula", "Maga", "Kolofata",
        "Tokombéré", "Koza", "Mogodé", "Bourrha", "Hina", "Makary", "Waza",
        "Blangoua", "Goulfey", "Logone-Birni", "Datcheka", "Kalfou", "Touloum",
        "Moutourwa", "Méri", "Gazawa", "Dargala",
    ],
    "Littoral": [
        "Douala", "Nkongsamba", "Edéa", "Yabassi", "Loum", "Mbanga", "Manjo", "Penja",
        "Melong", "Dibombari", "Njombé", "Dizangué", "Pouma", "Ngambé", "Ndom",
        "Nkondjock", "Yingui", "Massock", "Mouanko", "Bonaléa", "Souza",
    ],
    "Nord": [
        "Garoua", "Guider", "Poli", "Tcholliré", "Pitoa", "Figuil", "Mayo-Oulo",
        "Lagdo", "Touboro", "Rey-Bouba", "Bibémi", "Dembo", "Gashiga", "Ngong",
        "Touroua", "Béka", "Madingring",
    ],
    "Nord-Ouest": [
        "Bamenda", "Kumbo", "Wum", "Nkambé", "Ndop", "Mbengwi", "Fundong", "Bali",
        "Bafut", "Santa", "Batibo", "Jakiri", "Ndu", "Bambui", "Benakuma", "Nwa",
        "Misaje", "Njinikom", "Belo", "Ako", "Tubah", "Babessi", "Widikum",
    ],
    "Ouest": [
        "Bafoussam", "Dschang", "Mbouda", "Bafang", "Bangangté", "Foumban", "Baham",
        "Bandjoun", "Foumbot", "Kouoptamo", "Koutaba", "Magba", "Malantouen",
        "Massangam", "Bangourain", "Njimom", "Bana", "Bazou", "Tonga", "Bangou",
        "Batié", "Bamendjou", "Penka-Michel", "Fokoué", "Santchou", "Galim",
        "Batcham", "Babadjou", "Kékem", "Banwa", "Bandja", "Bayangam", "Poumougne",
    ],
    "Sud": [
        "Ebolowa", "Kribi", "Sangmélima", "Ambam", "Lolodorf", "Campo", "Akom II",
        "Bipindi", "Mvangan", "Meyomessala", "Djoum", "Mintom", "Oveng", "Zoétélé",
        "Bengbis", "Ma'an", "Olamzé", "Kyé-Ossi", "Biwong-Bane", "Efoulan", "Niété",
        "Mengong", "Mvengue", "Lokoundjé",
    ],
    "Sud-Ouest": [
        "Buea", "Kumba", "Mamfe", "Mundemba", "Bangem", "Fontem", "Limbe", "Tiko",
        "Muyuka", "Idenau", "Mbonge", "Konye", "Nguti", "Tombel", "Ekondo-Titi",
        "Eyumodjock", "Akwaya", "Tinto", "Wabane", "Alou", "Isangele", "Bamusso",
        "Toko",
    ],
}


def normaliser(texte: str) -> str:
    """Minuscules sans accents ni espaces superflus, pour comparer des noms."""
    sans_accents = unicodedata.normalize("NFD", texte or "").encode("ascii", "ignore").decode("ascii")
    return " ".join(sans_accents.lower().split())


# Nom normalisé → nom officiel (« yaounde » → « Yaoundé »)
_INDEX = {normaliser(nom): nom for noms in LOCALITES.values() for nom in noms}


def liste():
    """[{"nom", "region"}], triée par nom."""
    return sorted(
        ({"nom": nom, "region": region} for region, noms in LOCALITES.items() for nom in noms),
        key=lambda l: normaliser(l["nom"]),
    )


def valider(saisie: str) -> str:
    """Validateur DRF : retourne le nom officiel ou lève une ValidationError."""
    from rest_framework import serializers

    nom = nom_officiel(saisie)
    if nom is None:
        raise serializers.ValidationError("Choisissez une localité dans la liste proposée.")
    return nom


def nom_officiel(saisie: str):
    """Nom officiel de la localité saisie (accents/majuscules indifférents), ou None."""
    return _INDEX.get(normaliser(saisie))
