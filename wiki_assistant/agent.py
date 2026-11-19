from agno.agent import Agent

from wiki_assistant.config import (
    CHAT_REASONING_EFFORT,
    OPENCODE_API_KEY,
    OPENCODE_BASE_URL,
    OPENCODE_MODEL,
    OPENCODE_SESSION_ID,
    OPENCODE_USER_AGENT,
)

_agent: Agent | None = None


def get_agent() -> Agent:
    global _agent
    if _agent is None:
        from agno.models.openai.chat import OpenAIChat
        from wiki_assistant.knowledge import get_wiki_knowledge

        _agent = Agent(
            name="GolfSuite Wiki Assistant",
            model=OpenAIChat(
                id=OPENCODE_MODEL,
                api_key=OPENCODE_API_KEY,
                base_url=OPENCODE_BASE_URL,
                default_headers={
                    "x-opencode-session": OPENCODE_SESSION_ID,
                    "User-Agent": OPENCODE_USER_AGENT,
                },
                max_tokens=2048,
                reasoning_effort=CHAT_REASONING_EFFORT or None,
            ),
            knowledge=get_wiki_knowledge(),
            # The wiki context is retrieved once and injected, so most questions
            # are answered with a single model request. The search tool stays
            # available as a fallback (the instructions allow one extra search).
            add_knowledge_to_context=True,
            search_knowledge=True,
            add_datetime_to_context=True,
            markdown=True,
            instructions=[
                "Sei un assistente specializzato nel manuale GolfSuite di Nexxchange (https://www.nexxchange.com).",
                "PRIORITÀ ASSOLUTA: cerco SEMPRE prima nella mia knowledge base del wiki.",
                "Le informazioni del wiki mi vengono già fornite nel contesto: le uso e rispondo subito.",
                "Posso fare AL MASSIMO UNA ricerca con search_knowledge_base, e solo se il contesto non basta. Mai più di una.",
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
