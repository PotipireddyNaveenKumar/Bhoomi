from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from app.services.rag.evidence_model import CanonicalSourceCitation, AuthorityTier


class Citation(BaseModel):
    document_title: str
    authority: str
    source_agency: str
    publication_date: str
    section: str
    url_or_ref: str


class CitationBuilder:
    """
    Constructs verifiable agricultural source citations preserving full provenance.
    Strictly avoids fabricating ICAR/government authority unless metadata establishes it.
    """

    @staticmethod
    def resolve_authority_level(authority_str: str, source_type: Optional[str] = None) -> str:
        auth_lower = (authority_str or "").lower()
        st_lower = (source_type or "").lower()

        if any(k in auth_lower for k in ["icar", "dppqs", "ministry of agriculture", "imd", "agmarknet", "cibrc", "krishi vigyan"]):
            return AuthorityTier.TIER_1_GOVT_ICAR.value
        if any(k in auth_lower for k in ["angrau", "tnau", "pjtsau", "uas", "university", "kvk", "state department"]):
            return AuthorityTier.TIER_2_AGRI_UNIVERSITY.value
        if any(k in auth_lower for k in ["spices board", "tea board", "coffee board", "fao", "cgiar", "irri"]):
            return AuthorityTier.TIER_3_COMMODITY_BOARD.value
        if st_lower in ["official_extension", "peer_reviewed"]:
            return AuthorityTier.TIER_2_AGRI_UNIVERSITY.value

        return AuthorityTier.TIER_4_GENERAL.value

    @classmethod
    def build_canonical_citations(cls, metadata_list: List[Dict[str, Any]]) -> List[CanonicalSourceCitation]:
        citations: List[CanonicalSourceCitation] = []
        seen_titles = set()

        for idx, m in enumerate(metadata_list, 1):
            doc_id = m.get("id") or m.get("chunk_id") or f"CIT-{idx}"
            doc_title = m.get("document_title") or m.get("document") or m.get("title") or f"Agricultural Knowledge Record {doc_id}"
            
            # Avoid duplicate citations for identical documents
            if doc_title in seen_titles:
                continue
            seen_titles.add(doc_title)

            authority = m.get("authority") or m.get("source") or "Agricultural Extension Reference"
            tier = m.get("source_authority") or cls.resolve_authority_level(authority, m.get("source_type"))
            if tier == "tier_1":
                tier = AuthorityTier.TIER_1_GOVT_ICAR.value
            elif tier == "tier_2":
                tier = AuthorityTier.TIER_2_AGRI_UNIVERSITY.value
            elif tier == "tier_3":
                tier = AuthorityTier.TIER_3_COMMODITY_BOARD.value
            elif tier == "tier_4":
                tier = AuthorityTier.TIER_4_GENERAL.value

            citations.append(CanonicalSourceCitation(
                citation_id=f"[{idx}]",
                document_title=doc_title,
                authority=authority,
                authority_level=tier,
                section=m.get("section") or "General Agronomic Advisory",
                source_date=m.get("publication_date") or m.get("source_date"),
                source_url=m.get("source_url") or m.get("url_or_ref")
            ))

        return citations

    @classmethod
    def build_citations(cls, metadata_list: List[Dict[str, Any]]) -> List[Citation]:
        """
        Backward compatible citation builder for legacy endpoints and tests.
        """
        citations = []
        for m in metadata_list:
            doc_id = m.get("id") or m.get("chunk_id") or "KB-AGRI"
            doc_title = m.get("document_title") or m.get("document") or f"Agricultural Advisory ({doc_id})"
            authority = m.get("authority") or m.get("source") or "Agricultural Extension Authority"
            source_agency = m.get("source") or authority
            pub_date = str(m.get("publication_date") or "2024")
            section = m.get("section") or "Agronomic Advisory"
            url_or_ref = m.get("source_url") or m.get("url_or_ref") or "Official Extension Advisory Bulletin"

            citations.append(Citation(
                document_title=doc_title,
                authority=authority,
                source_agency=source_agency,
                publication_date=pub_date,
                section=section,
                url_or_ref=url_or_ref
            ))
        return citations
