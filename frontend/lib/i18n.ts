/**
 * Lightweight UI localisation. English is the source language: dictionary keys
 * are the literal English strings, so any untranslated string renders as-is.
 * Backend multilingual research is separate (OD-30); this covers interface text.
 */

export type Locale = "en" | "fr" | "de" | "es" | "zu";

export const SUPPORTED_LOCALES: Locale[] = ["en", "fr", "de", "es", "zu"];

const dictionaries: Record<Exclude<Locale, "en">, Record<string, string>> = {
  fr: {
    "Speak or type to IAM": "Parlez ou écrivez à IAM",
    "Ask IAM to remember something": "Demandez à IAM de mémoriser quelque chose",
    "Tell IAM what to create": "Dites à IAM quoi créer",
    "Online · ready when you are": "En ligne · prêt quand vous voulez",
    "Recall · searching your memories": "Rappel · recherche dans vos mémoires",
    "Suggestions": "Suggestions",
    "Mode": "Mode",
    "Conversation history": "Historique des conversations",
    "IAM options": "Options IAM",
    "Toggle theme": "Changer de thème",
    "Enable voice": "Activer la voix",
    "Disable voice": "Désactiver la voix",
    "Retry": "Réessayer",
    "Close options": "Fermer les options",
    "Search catalogue": "Rechercher dans le catalogue",
  },
  de: {
    "Speak or type to IAM": "Sprechen oder mit IAM schreiben",
    "Ask IAM to remember something": "IAM bitten, sich etwas zu merken",
    "Tell IAM what to create": "IAM sagen, was erstellt werden soll",
    "Online · ready when you are": "Online · bereit, wenn Sie es sind",
    "Recall · searching your memories": "Erinnerung · durchsucht Ihre Speicher",
    "Suggestions": "Vorschläge",
    "Mode": "Modus",
    "Conversation history": "Kontextverlauf",
    "IAM options": "IAM-Optionen",
    "Toggle theme": "Design wechseln",
    "Enable voice": "Sprache aktivieren",
    "Disable voice": "Sprache deaktivieren",
    "Retry": "Erneut versuchen",
    "Close options": "Optionen schließen",
    "Search catalogue": "Katalog durchsuchen",
  },
  es: {
    "Speak or type to IAM": "Habla o escribe a IAM",
    "Ask IAM to remember something": "Pide a IAM que recuerde algo",
    "Tell IAM what to create": "Dile a IAM qué crear",
    "Online · ready when you are": "En línea · listo cuando quieras",
    "Recall · searching your memories": "Recordar · buscando tus recuerdos",
    "Suggestions": "Sugerencias",
    "Mode": "Modo",
    "Conversation history": "Historial de conversaciones",
    "IAM options": "Opciones de IAM",
    "Toggle theme": "Cambiar tema",
    "Enable voice": "Activar voz",
    "Disable voice": "Desactivar voz",
    "Retry": "Reintentar",
    "Close options": "Cerrar opciones",
    "Search catalogue": "Buscar en el catálogo",
  },
  zu: {
    "Speak or type to IAM": "Khuluma noma ubhalele i-IAM",
    "Ask IAM to remember something": "Cela i-IAM ukukhumbula okuthile",
    "Tell IAM what to create": "Tshela i-IAM ukuthi idaleni",
    "Online · ready when you are": "Ku-inthanethi · ulungile uma ukulungele",
    "Recall · searching your memories": "Ukukhumbula · kusesha izinkumbulo zakho",
    "Suggestions": "Iziphakamiso",
    "Mode": "Imodi",
    "Conversation history": "Umlando wezingxoxo",
    "IAM options": "Izinketho ze-IAM",
    "Toggle theme": "Shintsha itimu",
    "Enable voice": "Vula izwi",
    "Disable voice": "Vala izwi",
    "Retry": "Zama futhi",
    "Close options": "Vala izinketho",
    "Search catalogue": "Sesha ikhathalogu",
  },
};

export function detectLocale(): Locale {
  if (typeof navigator === "undefined") return "en";
  const raw = (navigator.language || "").toLowerCase().split("-")[0];
  return (SUPPORTED_LOCALES as string[]).includes(raw) ? (raw as Locale) : "en";
}

export function t(text: string, locale: Locale): string {
  if (locale === "en") return text;
  return dictionaries[locale][text] ?? text;
}
