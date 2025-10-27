# -*- coding: utf-8 -*-

# Configuration additionnelle du module
# Ce fichier peut contenir des paramètres système ou des configurations avancées

# Exemple : Paramètres pour le formulaire de contact
CONTACT_FORM_CONFIG = {
    'default_subject': 'Demande de renseignements pour un box',
    'redirect_after_submit': '/contactus-thank-you',
    'send_confirmation_email': True,
}

# URL du formulaire de contact
CONTACT_URL = '/contactus'
