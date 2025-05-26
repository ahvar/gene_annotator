import requests
from flask import current_app
from flask_babel import _


def translate(text, source_language, dest_language):
    if (
        "MS_TRANSLATOR_KEY" not in current_app.config
        or not current_app.config["MS_TRANSLATOR_KEY"]
    ):
        return _("Error: the translation service is not configured")
    endpoint = "https://gene-annotator.cognitiveservices.azure.com/translator/text/v3.0/translate"
    headers = {
        "Ocp-Apim-Subscription-Key": current_app.config["MS_TRANSLATOR_KEY"],
        "Ocp-Apim-Subscription-Region": "southcentralus",
        "Content-Type": "application/json",
    }
    params = {"api-version": "3.0", "from": source_language, "to": dest_language}
    r = requests.post(
        endpoint,
        headers=headers,
        params=params,
        json=[{"Text": text}],
    )
    if r.status_code != 200:
        return _("Error: the translation service failed.")
    return r.json()[0]["translations"][0]["text"]
