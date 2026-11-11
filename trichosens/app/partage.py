"""Résumé du diagnostic à partager (SMS, WhatsApp, e-mail…) ou à enregistrer en PDF."""

from .engine import MOMENTS, NEEDS, Diagnostic


def texte_partage(d: Diagnostic, site_url: str) -> str:
    """Résumé court et lisible de la routine, avec le lien vers TrichoSens."""
    titre = f"Ma routine TrichoSens{' – ' + d.prenom if d.prenom else ''}"
    lignes = [
        titre,
        f"Type de cheveux : {d.type_cheveux.code} ({d.type_cheveux.nom.lower()})"
        + (f", avec une part de {d.type_secondaire.code}" if d.type_secondaire else ""),
        f"Priorités : {', '.join(NEEDS[p] for p in d.priorites)}",
        f"Lavage conseillé : {d.frequence_lavage}",
    ]
    for moment, label in MOMENTS.items():
        etapes = [s for s in d.routine if s.moment == moment]
        if not etapes:
            continue
        lignes.append("")
        lignes.append(f"{label} :")
        for s in etapes:
            produit = f" ({s.produit.nom_complet})" if s.produit else ""
            lignes.append(f"• {s.titre}{produit}")
    lignes += ["", f"Prochain point : {d.prochain_point.strftime('%d/%m/%Y')}",
               "", f"Faites votre diagnostic : {site_url}"]
    return "\n".join(lignes)
