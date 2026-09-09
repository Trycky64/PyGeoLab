"""Runtime translations for the two supported interface languages."""

from __future__ import annotations

import re

from PySide6.QtCore import QLocale, QTranslator
from PySide6.QtWidgets import QApplication

ENGLISH: dict[str, str] = {
    " min": " min",
    " px": " px",
    " u/s": " units/s",
    "&Affichage": "&View",
    "&Aide": "&Help",
    "&Annuler": "&Undo",
    "&Dupliquer": "&Duplicate",
    "&Enregistrer": "&Save",
    "&Exporter": "&Export",
    "&Fichier": "&File",
    "&Nouveau": "&New",
    "&Objets": "&Objects",
    "&Ouvrir…": "&Open…",
    "&Préférences…": "&Preferences…",
    "&Quitter": "&Quit",
    "&Raccourcis clavier…": "&Keyboard shortcuts…",
    "&Rétablir": "&Redo",
    "&Supprimer": "&Delete",
    "&Édition": "&Edit",
    "&Magnétisme (maintenir Alt pour suspendre)": "&Snapping (hold Alt to suspend)",
    "&Modifier la fonction…": "&Edit function…",
    "+ Curseur": "+ Slider",
    "Action": "Action",
    "Activer la sauvegarde automatique": "Enable autosave",
    "Activer le snapping": "Enable snapping",
    "Affichage": "View",
    "Afficher": "Show",
    "Afficher la dérivée": "Show derivative",
    "Afficher la grille": "Show grid",
    "Afficher le label": "Show label",
    "Afficher les axes": "Show axes",
    "Afficher les extrema": "Show extrema",
    "Afficher les intersections": "Show intersections",
    "Afficher les labels": "Show labels",
    "Afficher les racines": "Show roots",
    "Algèbre": "Algebra",
    "Analyse numérique": "Numerical analysis",
    "Angle": "Angle",
    "Aucun curseur": "No sliders",
    "Aucun résultat sur cet intervalle": "No result in this interval",
    "Aucune fonction valide": "No valid function",
    "Barre d'état": "Status bar",
    "Basse": "Low",
    "Bissectrice": "Angle bisector",
    "Calculer": "Calculate",
    "Cercle": "Circle",
    "Cercle centre-rayon": "Center-radius circle",
    "Cercle circonscrit": "Circumcircle",
    "Cercles": "Circles",
    "Choisir…": "Choose…",
    "Clair": "Light",
    "Construction indéfinie": "Undefined construction",
    "Constructions": "Constructions",
    "Copie impossible": "Copy failed",
    "Copier le viewport en PNG": "Copy viewport as PNG",
    "Copier le viewport en SVG": "Copy viewport as SVG",
    "Copier les informations système": "Copy system information",
    "Copier les informations &système": "Copy &system information",
    "Couleur": "Color",
    "Couleur par défaut": "Default color",
    "Curseur invalide": "Invalid slider",
    "Curseurs": "Sliders",
    "Demi-droite": "Ray",
    "Descendants": "Descendants",
    "Deuxième fonction": "Second function",
    "Distance": "Distance",
    "Document complet": "Full document",
    "Document de récupération restauré": "Recovery document restored",
    "Droite": "Line",
    "Dupliquer": "Duplicate",
    "Début": "Start",
    "Dépendances": "Dependencies",
    "Dérivée en x": "Derivative at x",
    "Déverrouiller": "Unlock",
    "Effacer la sélection": "Clear selection",
    "Effacer les fichiers récents": "Clear recent files",
    "Enregistrement impossible": "Save failed",
    "Enregistrer &sous…": "Save &as…",
    "Enregistrer le projet": "Save project",
    "Enregistrer les modifications avant de continuer ?": "Save changes before continuing?",
    "Export impossible": "Export failed",
    "Exporter": "Export",
    "Expression": "Expression",
    "Extrema": "Extrema",
    "Fenêtre principale PyGeoLab": "PyGeoLab main window",
    "Fichiers &récents": "&Recent files",
    "Fin": "End",
    "Fonction": "Function",
    "Fonction invalide": "Invalid function",
    "Fonctions": "Functions",
    "Fond transparent": "Transparent background",
    "Fond transparent par défaut": "Transparent background by default",
    "Français": "Français",
    "Grouper par catégorie": "Group by category",
    "Grouper par type": "Group by type",
    "Hauteur": "Height",
    "Haute": "High",
    "Homothétie": "Scaling",
    "Image &PNG…": "&PNG image…",
    "Image &SVG…": "&SVG image…",
    "Informations système copiées": "System information copied",
    "Intersection": "Intersection",
    "Intersections": "Intersections",
    "Intervalle autosave": "Autosave interval",
    "Intégrale": "Integral",
    "La langue sera appliquée au prochain démarrage.": "The language will apply after restart.",
    "La récupération est illisible et a été ignorée.": (
        "The recovery file is unreadable and was ignored."
    ),
    "La sélection ne convient pas à cette mesure": (
        "The selection is not suitable for this measurement"
    ),
    "Langue": "Language",
    "Largeur": "Width",
    "Lignes": "Lines",
    "Le projet n'a pas pu être enregistré.": "The project could not be saved.",
    "Le projet n'a pas pu être ouvert. Le document courant a été conservé.": (
        "The project could not be opened. The current document was preserved."
    ),
    "Le viewport PNG n'a pas pu être copié.": "The PNG viewport could not be copied.",
    "Le viewport SVG n'a pas pu être copié.": "The SVG viewport could not be copied.",
    "Limiter le domaine": "Limit domain",
    "Liste des raccourcis clavier": "Keyboard shortcut list",
    "Magnétisme (maintenir Alt pour suspendre)": "Snapping (hold Alt to suspend)",
    "Masquer": "Hide",
    "Maximum": "Maximum",
    "Mesurer l'aire sélectionnée": "Measure selected area",
    "Mesurer l'&aire sélectionnée": "Measure selected &area",
    "Mesurer la longueur sélectionnée": "Measure selected length",
    "Mesurer la &longueur sélectionnée": "Measure selected &length",
    "Mettre au premier plan": "Bring to front",
    "Mettre à l'arrière-plan": "Send to back",
    "Médiatrice": "Perpendicular bisector",
    "Milieu": "Midpoint",
    "Minimum": "Minimum",
    "Modifications non enregistrées": "Unsaved changes",
    "Modifier": "Edit",
    "Modifier la fonction": "Edit function",
    "Modifier la fonction…": "Edit function…",
    "Modifier le curseur": "Edit slider",
    "Nom": "Name",
    "Nombres": "Numbers",
    "Nouveau": "New",
    "Normale": "Normal",
    "Nouveau curseur": "New slider",
    "Nouveau curseur…": "New slider…",
    "Nouveau &curseur…": "New &slider…",
    "Nouvelle fonction": "New function",
    "Nouvelle fonction…": "New function…",
    "Nouvelle &fonction…": "New &function…",
    "Objet": "Object",
    "Objets": "Objects",
    "Opacité du remplissage": "Fill opacity",
    "Options d'export": "Export options",
    "Opération": "Operation",
    "Ordre du document": "Document order",
    "Outils de construction": "Construction tools",
    "Ouvrir…": "Open…",
    "Ouverture impossible": "Open failed",
    "Ouvrir le dossier des logs": "Open log folder",
    "Ouvrir le dossier des &logs": "Open &log folder",
    "Ouvrir un projet": "Open project",
    "Panneau Algèbre": "Algebra panel",
    "Panneau Analyse numérique": "Numerical analysis panel",
    "Panneau Curseurs": "Sliders panel",
    "Panneau Propriétés": "Properties panel",
    "Parallèle": "Parallel",
    "Paramètres": "Parameters",
    "Pas": "Step",
    "Perpendiculaire": "Perpendicular",
    "Point": "Point",
    "Points": "Points",
    "Point sur objet": "Point on object",
    "Polygone": "Polygon",
    "Polygones": "Polygons",
    "Préférences": "Preferences",
    "Préférences…": "Preferences…",
    "Préférences de PyGeoLab": "PyGeoLab preferences",
    "Prêt": "Ready",
    "Projection": "Projection",
    "Projet PyGeoLab (*.pgl)": "PyGeoLab project (*.pgl)",
    "Propriétés": "Properties",
    "Qualité d'export": "Export quality",
    "Qualité du tracé": "Plot quality",
    "Raccourci": "Shortcut",
    "Raccourcis actifs": "Active shortcuts",
    "Raccourcis clavier": "Keyboard shortcuts",
    "Raccourcis clavier…": "Keyboard shortcuts…",
    "Racines": "Roots",
    "Rechercher…": "Search…",
    "Reset": "Reset",
    "Quitter": "Quit",
    "Restaurer les valeurs par défaut": "Restore defaults",
    "Rotation": "Rotation",
    "Récupération disponible": "Recovery available",
    "Récupération impossible": "Recovery failed",
    "Résolution": "Resolution",
    "Résultats limités aux 500 premiers": "Results limited to the first 500",
    "Sans regroupement": "No grouping",
    "Sauvegarde automatique effectuée": "Autosave completed",
    "Segment": "Segment",
    "Sombre": "Dark",
    "Style de ligne": "Line style",
    "Supprimer": "Delete",
    "Annuler": "Undo",
    "Rétablir": "Redo",
    "Enregistrer": "Save",
    "Enregistrer sous…": "Save as…",
    "Image PNG…": "PNG image…",
    "Image SVG…": "SVG image…",
    "Symétrie axiale": "Reflection across line",
    "Symétrie centrale": "Point reflection",
    "Système": "System",
    "Sélection": "Select",
    "Sélection effacée": "Selection cleared",
    "Sélection uniquement": "Selection only",
    "Sélectionner les descendants": "Select descendants",
    "Sélectionner les parents": "Select parents",
    "Sélectionnez un objet": "Select an object",
    "Sélectionnez un objet mesurable": "Select a measurable object",
    "Sélectionnez une fonction à modifier": "Select a function to edit",
    "Taille de point par défaut": "Default point size",
    "Taille du point": "Point size",
    "Taille du snap": "Snap size",
    "Thème": "Theme",
    "Tolérance": "Tolerance",
    "Tout sélectionner": "Select all",
    "Tout &sélectionner": "Select &all",
    "Translation": "Translation",
    "Trier par nom": "Sort by name",
    "Trier par type": "Sort by type",
    "Une sauvegarde de récupération a été trouvée. La restaurer ?": (
        "A recovery save was found. Restore it?"
    ),
    "Valeur": "Value",
    "Variable": "Variable",
    "Vecteur": "Vector",
    "Verrouiller": "Lock",
    "Verrouillé": "Locked",
    "Viewport PNG copié": "PNG viewport copied",
    "Viewport SVG copié": "SVG viewport copied",
    "Viewport actuel": "Current viewport",
    "Visible": "Visible",
    "Zone": "Area",
    "Zone de géométrie dynamique": "Dynamic geometry canvas",
    "x / début": "x / start",
    "À propos de PyGeoLab": "About PyGeoLab",
    "À &propos de PyGeoLab": "&About PyGeoLab",
    "Échantillons": "Samples",
    "Épaisseur": "Width",
    "Épaisseur par défaut": "Default width",
    "indéfini": "undefined",
    "↔": "↔",
    "⏸": "⏸",
    "▶": "▶",
}

ERRORS_ENGLISH: dict[str, str] = {
    "Aucun chemin d'enregistrement défini": "No save path is defined",
    "Au moins deux échantillons sont nécessaires": "At least two samples are required",
    "Au moins deux sous-intervalles sont nécessaires": "At least two subintervals are required",
    "Ce nom est déjà utilisé": "This name is already in use",
    "Couche d'analyse inconnue": "Unknown analysis layer",
    "Couleur par défaut invalide": "Invalid default color",
    "Domaine de fonction invalide": "Invalid function domain",
    "Domaine invalide": "Invalid domain",
    "Dépendances invalides": "Invalid dependencies",
    "Définition d'objet invalide": "Invalid object definition",
    "Drapeaux d'objet invalides": "Invalid object flags",
    "Erreur interne — PyGeoLab": "Internal error — PyGeoLab",
    "Format ou version .pgl invalide": "Invalid .pgl format or version",
    "Identifiant UUID invalide": "Invalid UUID",
    "Identifiant d'objet dupliqué": "Duplicate object identifier",
    "Identifiant d'objet invalide": "Invalid object identifier",
    "Intervalle d'autosave invalide": "Invalid autosave interval",
    "Intervalle de sampling invalide": "Invalid sampling interval",
    "Intervalle ou échantillonnage invalide": "Invalid interval or sampling",
    "Intervalle, échantillonnage ou tolérance invalide": "Invalid interval, sampling, or tolerance",
    "La dépendance demandée n'existe pas": "The requested dependency does not exist",
    "La fonction est discontinue ou invalide sur l'intervalle": (
        "The function is discontinuous or invalid over the interval"
    ),
    "La fonction sélectionnée est invalide": "The selected function is invalid",
    "La limite d'historique doit être positive": "The history limit must be positive",
    "La valeur doit appartenir aux bornes du curseur": "The value must be within the slider bounds",
    "La valeur doit être finie": "The value must be finite",
    "Langue inconnue": "Unknown language",
    "Le facteur de résolution doit être compris entre 0.25 et 8": (
        "The resolution factor must be between 0.25 and 8"
    ),
    "Le facteur de zoom doit être positif et fini": "The zoom factor must be positive and finite",
    "Le minimum doit être inférieur au maximum": "The minimum must be lower than the maximum",
    "Le pas de dérivation doit être positif et fini": (
        "The derivative step must be positive and finite"
    ),
    "Le pas doit être strictement positif": "The step must be strictly positive",
    "Le projet doit être un objet JSON": "The project must be a JSON object",
    "Le rayon doit être numérique": "The radius must be numeric",
    "Le rayon doit être positif ou nul": "The radius must be nonnegative",
    "Le résultat numérique n'est pas fini": "The numerical result is not finite",
    "Le seuil de snapping doit être compris entre 1 et 100 pixels": (
        "The snapping threshold must be between 1 and 100 pixels"
    ),
    "Le viewport nécessite des dimensions positives": "The viewport requires positive dimensions",
    "Les bornes d'intégration doivent être finies": "The integration bounds must be finite",
    "Les coordonnées doivent être finies": "Coordinates must be finite",
    "Les coordonnées écran doivent être finies": "Screen coordinates must be finite",
    "Les dimensions doivent être comprises entre 1 et 20 000 pixels": (
        "Dimensions must be between 1 and 20,000 pixels"
    ),
    "Les valeurs du curseur doivent être finies": "Slider values must be finite",
    "Liste d'objets invalide": "Invalid object list",
    "Métadonnées de document invalides": "Invalid document metadata",
    "Nom de document invalide": "Invalid document name",
    "Nom de fonction ou variable invalide": "Invalid function name or variable",
    "Opacité attendue entre 0 et 1": "Opacity must be between 0 and 1",
    "Opération numérique inconnue": "Unknown numerical operation",
    "Paramètres invalides": "Invalid parameters",
    "Qualité de sampling inconnue": "Unknown sampling quality",
    "Qualité d'export invalide": "Invalid export quality",
    "Seul un point libre non verrouillé peut être déplacé": (
        "Only an unlocked free point can be moved"
    ),
    "Style de ligne inconnu": "Unknown line style",
    "Style invalide": "Invalid style",
    "Sélectionnez une fonction valide": "Select a valid function",
    "Taille de point par défaut invalide": "Invalid default point size",
    "Taille de snap invalide": "Invalid snap size",
    "Thème inconnu": "Unknown theme",
    "Type ou nom d'objet invalide": "Invalid object type or name",
    "Un objet numérique est attendu": "A numeric object is required",
    "Un point est attendu": "A point is required",
    "Un polygone nécessite au moins trois sommets": "A polygon requires at least three vertices",
    "Un support linéaire ou circulaire est attendu": "A line-like object or circle is required",
    "Un support linéaire ou un cercle est attendu": "A line-like object or circle is required",
    "Une aire nécessite un polygone": "Area requires a polygon",
    "Une dépendance cyclique est interdite": "Cyclic dependencies are not allowed",
    "Une dépendance ne peut être répétée": "A dependency cannot be repeated",
    "Une dépendance référence un objet absent": "A dependency references a missing object",
    "Une droite nécessite une normale non nulle": "A line requires a nonzero normal",
    "Une droite non dégénérée est attendue": "A nondegenerate line is required",
    "Une fonction nécessite une expression et une variable": (
        "A function requires an expression and a variable"
    ),
    "Une longueur nécessite un segment ou un vecteur": "Length requires a segment or vector",
    "Valeur hors du domaine de la fonction": "Value outside the function domain",
    "Version .pgl non prise en charge": "Unsupported .pgl version",
    "Version .pgl plus récente que cette application": (
        "The .pgl version is newer than this application"
    ),
    "Zoom de viewport invalide": "Invalid viewport zoom",
    "Épaisseur attendue entre 0.5 et 20": "Width must be between 0.5 and 20",
    "Épaisseur par défaut invalide": "Invalid default width",
}


class EnglishTranslator(QTranslator):
    """Translate the French source catalogue to English without external binaries."""

    def translate(
        self,
        context: str,
        source_text: str,
        disambiguation: str | None = None,
        n: int = -1,
    ) -> str:
        """Return the English equivalent of one Qt source string."""
        del context, disambiguation, n
        direct = ENGLISH.get(source_text, ERRORS_ENGLISH.get(source_text))
        if direct is not None:
            return direct
        replacements = (
            (r"^(\d+) objets sélectionnés$", r"\1 objects selected"),
            (r"^(\d+) objet\(s\) sélectionné\(s\)$", r"\1 object(s) selected"),
            (r"^(\d+) résultat\(s\)$", r"\1 result(s)"),
            (r"^Erreur : (.+)$", r"Error: \1"),
            (r"^Exporté vers (.+)$", r"Exported to \1"),
            (r"^Dossier des logs : (.+)$", r"Log folder: \1"),
            (r"^Échec de la sauvegarde automatique : (.+)$", r"Autosave failed: \1"),
            (r"^L'export ([A-Z]+) n'a pas pu être créé\.$", r"The \1 export could not be created."),
            (r"^Curseurs numériques introuvables : (.+)$", r"Numeric sliders not found: \1"),
            (r"^Impossible de lire le projet : (.+)$", r"Could not read project: \1"),
            (r"^Impossible d'enregistrer le projet : (.+)$", r"Could not save project: \1"),
            (r"^Impossible de supprimer la récupération : (.+)$", r"Could not remove recovery: \1"),
            (
                r"^Caractère interdit (.+) à la position (\d+)$",
                r"Forbidden character \1 at position \2",
            ),
            (r"^Nombre invalide à la position (\d+)$", r"Invalid number at position \1"),
            (r"^Exposant invalide à la position (\d+)$", r"Invalid exponent at position \1"),
            (r"^Nom vide ou déjà utilisé : (.+)$", r"Empty or duplicate name: \1"),
            (
                r"^Une erreur interne est survenue\. Elle a été enregistrée dans :\n(.+)$",
                r"An internal error occurred. It was recorded in:\n\1",
            ),
            (r"^indéfini — (.+)$", r"undefined — \1"),
            (r"^longueur (.+)$", r"length \1"),
        )
        for pattern, replacement in replacements:
            if re.match(pattern, source_text):
                return re.sub(pattern, replacement, source_text)
        if source_text.startswith("<b>PyGeoLab "):
            return source_text.replace(
                "Géométrie dynamique et visualisation mathématique.",
                "Dynamic geometry and mathematical visualization.",
            ).replace("Licence MIT", "MIT License")
        return source_text


_installed_translator: EnglishTranslator | None = None


def resolved_language(preference: str, locale: QLocale | None = None) -> str:
    """Resolve system language to French or English, with English as global fallback."""
    if preference in {"en", "fr"}:
        return preference
    current = locale or QLocale.system()
    return "fr" if current.language() == QLocale.Language.French else "en"


def install_application_translator(application: QApplication, preference: str) -> str:
    """Install the selected application translator and return its resolved language."""
    global _installed_translator
    if _installed_translator is not None:
        application.removeTranslator(_installed_translator)
        _installed_translator = None
    language = resolved_language(preference)
    if language == "en":
        _installed_translator = EnglishTranslator(application)
        application.installTranslator(_installed_translator)
    application.setProperty("pygeolabLanguage", language)
    return language


def translate_message(message: str) -> str:
    """Translate a dynamic domain error according to the active interface language."""
    application = QApplication.instance()
    if (
        not isinstance(application, QApplication)
        or application.property("pygeolabLanguage") != "en"
    ):
        return message
    return EnglishTranslator().translate("PyGeoLabError", message)
