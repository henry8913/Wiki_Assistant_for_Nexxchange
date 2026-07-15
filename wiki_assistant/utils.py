def format_source_reference(source_url: str, title: str = "") -> str:
    ref = f"📎 [Fonte]({source_url})"
    if title:
        ref = f"📎 [{title}]({source_url})"
    return ref


def truncate_text(text: str, max_chars: int = 500) -> str:
    if len(text) <= max_chars:
        return text
    return text[:max_chars].rsplit(" ", 1)[0] + "..."
