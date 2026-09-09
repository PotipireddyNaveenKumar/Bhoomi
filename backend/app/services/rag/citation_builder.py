from typing import List, Dict, Any
from pydantic import BaseModel

class Citation(BaseModel):
    document_title: str
    authority: str
    source_agency: str
    publication_date: str
    section: str
    url_or_ref: str

class CitationBuilder:
    @staticmethod
    def build_citations(metadata_list: List[Dict[str, Any]]) -> List[Citation]:
        citations = []
        for m in metadata_list:
            citations.append(Citation(
                document_title=m.get("document", "ICAR Package of Practices"),
                authority=m.get("authority", "Indian Council of Agricultural Research (ICAR)"),
                source_agency=m.get("source", "Ministry of Agriculture & Farmers Welfare"),
                publication_date=m.get("publication_date", "2024"),
                section=m.get("section", "Agronomic Advisory"),
                url_or_ref=m.get("ref", "Official State Agricultural Advisory Bulletin")
            ))
        return citations
