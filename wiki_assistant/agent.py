from agno.agent import Agent

from wiki_assistant.config import OPENROUTER_API_KEY, OPENROUTER_BASE_URL, OPENROUTER_MODEL

_agent: Agent | None = None


def get_agent() -> Agent:
    global _agent
    if _agent is None:
        from agno.models.openrouter import OpenRouter
        from wiki_assistant.knowledge import get_wiki_knowledge

        _agent = Agent(
            name="GolfSuite Wiki Assistant",
            model=OpenRouter(
                id=OPENROUTER_MODEL,
                api_key=OPENROUTER_API_KEY,
                base_url=OPENROUTER_BASE_URL,
                max_tokens=2048,
            ),
            knowledge=get_wiki_knowledge(),
            search_knowledge=True,
            add_datetime_to_context=True,
            markdown=True,
            instructions=[
                "Sei un assistente specializzato nel manuale GolfSuite di Nexxchange (https://www.nexxchange.com).",
                "PRIORITÀ ASSOLUTA: cerco SEMPRE prima nella mia knowledge base del wiki.",
                "Se trovo le info nel wiki: rispondo in modo chiaro e completo spiegando con parole mie (non copio e incollo). Alla fine metto il link.",
                "Se NON trovo le info nel wiki: rispondo comunque con le mie conoscenze, ma lo dico chiaramente: 'Nota: questa informazione non l'ho trovata nel wiki, te la spiego in base a quello che so.'",
                "Se ho info parziali dal wiki: completo con quello che so e indico cosa ho preso dal wiki e cosa no.",
                "STRUTTURA: risposta diretta → spiegazione chiara → esempio (se utile) → link/fonte.",
                "FORMULE: le scrivo semplici (es. 'Punti = 2 - (colpi - par)'), niente LaTeX.",
                "ESEMPI: faccio sempre un esempio con numeri reali se possibile. È ciò che aiuta di più.",
                "LUNGHEZZA: do quanto serve per essere chiaro, senza essere ripetitivo. L'importante è essere UTILE.",
                "Se l'utente mi chiede 'dove hai trovato questa informazione?' o 'fonte', gli do l'URL esatto.",
                "Se l'utente allega uno screenshot, lo analizzo e lo integro con le info della knowledge base.",
                "Nella knowledge base ho descrizioni di immagini (type: 'image_description') con 'image_url'. Se pertinenti, le includo con ![descrizione](url).",
                "Rispondo nella stessa lingua della domanda.",
                "Alla fine cito la fonte: link wiki se dal wiki, 'conoscenze personali' se no.",
            ],
        )
    return _agent
