import hashlib
from pathlib import Path

from agno.knowledge.reader.pdf_reader import PDFReader

from wiki_assistant.knowledge import get_wiki_knowledge

DEFAULT_DIR = Path("wiki_update")


def _file_hash(path: Path) -> str:
    """Short SHA-256 fingerprint of a file, used to detect updates."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()[:16]


def _stored_hash(kb, source_file: str):
    """Return the fingerprint already stored for a local file, if any."""
    from sqlalchemy import select

    table = kb.vector_db.table
    try:
        with kb.vector_db.Session() as sess:
            rows = sess.execute(
                select(table.c.meta_data)
                .where(table.c.meta_data.contains({"source_file": source_file}))
                .limit(1)
            ).fetchall()
        if rows:
            return (rows[0][0] or {}).get("file_hash")
    except Exception as exc:
        print(f"  (version check error: {exc})")
    return None


def ingest_local_pdfs(directory: Path = DEFAULT_DIR, force: bool = False) -> int:
    """Ingest every PDF in ``directory`` into the knowledge base.

    Files are tracked by name + content fingerprint, so:
    - new PDFs are inserted
    - changed PDFs replace their old chunks
    - unchanged PDFs are skipped (no wasted embeddings)
    """
    directory = Path(directory)
    if not directory.exists():
        print(f"\n📂 Cartella '{directory}' non trovata — salto i PDF locali.")
        return 0

    pdfs = sorted(directory.glob("*.pdf"))
    if not pdfs:
        print(f"\n📂 Nessun PDF in '{directory}'.")
        return 0

    print(f"\n=== PDF locali ({len(pdfs)} file in '{directory}') ===")
    kb = get_wiki_knowledge()
    inserted = 0
    skipped = 0

    for pdf in pdfs:
        source_file = pdf.name
        file_hash = _file_hash(pdf)
        stored = _stored_hash(kb, source_file)

        if not force and stored == file_hash:
            print(f"  ✓ {source_file} — già aggiornato")
            skipped += 1
            continue

        try:
            kb.vector_db.delete_by_metadata({"source_file": source_file})
        except Exception as exc:
            print(f"  (delete error {source_file}: {exc})")

        print(f"  ⬆ {source_file} — ingestion...", end=" ", flush=True)
        try:
            kb.insert(
                name=pdf.stem,
                path=str(pdf),
                metadata={
                    "source_url": f"wiki_update/{source_file}",
                    "source_file": source_file,
                    "type": "local_pdf",
                    "file_hash": file_hash,
                    "title": pdf.stem,
                },
                reader=PDFReader(),
                skip_if_exists=True,
            )
            inserted += 1
            print("ok")
        except Exception as exc:
            print(f"errore: {exc}")

    print(f"PDF locali: {inserted} aggiornati/inseriti, {skipped} invariati.")
    return inserted
