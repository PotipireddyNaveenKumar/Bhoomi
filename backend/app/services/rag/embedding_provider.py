from abc import ABC, abstractmethod
from typing import List, Optional
import os
import math
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from app.core.config import settings
from app.core.logging import logger


class EmbeddingProvider(ABC):
    @abstractmethod
    def embed_text(self, text: str) -> List[float]:
        """Generates embedding vector for a single string."""
        pass

    @abstractmethod
    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generates embedding vectors for a batch of strings."""
        pass


class TfidfDenseEmbeddingProvider(EmbeddingProvider):
    """
    High-speed, zero-network, scikit-learn backed TF-IDF embedding provider.
    Ensures deterministic, fast local semantic representation without external API dependency.
    """
    def __init__(self, vocabulary_hint: Optional[List[str]] = None):
        self.vectorizer = TfidfVectorizer(
            ngram_range=(1, 2),
            max_features=512,
            sublinear_tf=True
        )
        seeds = list(vocabulary_hint) if vocabulary_hint else []
        if not seeds:
            seeds = [
                # English agronomy
                "chilli thrips leaf curl virus azadirachtin fipronil ipm pest",
                "tomato early blight late blight mancozeb metalaxyl fungicide",
                "cotton pink bollworm pheromone trap emamectin rosette flower",
                "rice blast bacterial leaf blight tricyclazole copper hydroxide",
                "potato late blight phytophthora cymoxanil earthing up",
                "maize corn fall armyworm spodoptera chlorantraniliprole whorl",
                "banana sigatoka panama wilt fusarium propiconazole trichoderma",
                "crop rotation legume nitrogen fixation soil health organic",
                "drip irrigation micro fertigation water saving pmksy efficiency",
                "yellow leaves chlorosis nitrogen deficiency ferrous zinc urea",
                "black cotton soil vertisols clay water retention broad bed furrow",
                "integrated pest management etl threshold sticky traps biological",
                "spray weather safety wind rain temperature agrochemical cibrc",
                "fertilizer dosage soil health card balanced npk split application",
                "pm-kisan pmfby crop insurance kcc subsidy financial assistance",
                "cost of cultivation profit per acre net yield economics",
                # Telugu agrarian terminology
                "మిరప ఆకులు ముడుచుకుంటున్నాయి తామర పురుగు నల్లి ఆకుముడత వైరస్ తెల్లదోమ",
                "టమాటా ఆకుమచ్చ ముడత తెగులు కాయ కుళ్లు నల్ల మచ్చలు బూడిద తెగులు",
                "పత్తి గులాబీ రంగు పురుగు తెల్లదోమ పత్తి పంట నల్లరేగడి నేల",
                "వరి అగ్గితెగులు పొడ తెగులు సుడిదోమ ఎరువులు యూరియా పిచికారీ",
                "బిందు సేద్యం నీటి పారుదల తేమ శాతం నేల సారం పంట మార్పిడి",
                "పిచికారీ వాతావరణం వర్షం గాలి వేగం మందులు భద్రతా నియమాలు",
                "ఎరువులు డోస్ ఎంత వేయాలి నత్రజని భాస్వరం పొటాష్ భూసార పరీక్ష",
                "పీఎం కిసాన్ పంట భీమా సబ్సిడీ నష్టపరిహారం కిసాన్ క్రెడిట్ కార్డు",
                # Hindi agrarian terminology
                "मिर्च पत्ते मुड़ रहे हैं थ्रिप्स माइट्स लीफ कर्ल वायरस सफेद मक्खी",
                "टमाटर झुलसा अगेती पछेती पत्ती धब्बे फल सड़न फफूंदनाशक",
                "कपास गुलाबी सुंडी सफेद मक्खी काली मिट्टी फसल प्रबंधन",
                "धान झोंका शीथ ब्लाइट भूरा फुदका यूरिया सिंचाई",
                "ड्रिप सिंचाई जल बचत मृदा स्वास्थ्य फसल चक्र संतुलित उर्वरक",
                "छिड़काव मौसम बारिश हवा की गति कीटनाशक सुरक्षा नियम",
                "खाद उर्वरक मात्रा एनपीके मिट्टी परीक्षण पीएम किसान फसल बीमा",
                # Tamil / Kannada / Malayalam terms
                "மிளகாய் இலை சுருட்டை தக்காளி பருத்தி நெல் உரம் பாசனம்",
                "ಮೆಣಸಿನಕಾಯಿ ಎಲೆ ಮುದುಡುವುದು ರೋಗ ಕೀಟ ನಿಯಂತ್ರಣ ನೀರಾವರಿ",
                "മുളക് ഇല ചുരുളൽ തക്കാളി രോഗം കീടനാശിനി തളിക്കൽ"
            ]

            # Ingest verified knowledge documents if available
            try:
                import json
                for k_path in [
                    "data/rag/verified_knowledge.json",
                    "backend/data/rag/verified_knowledge.json",
                    os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "data", "rag", "verified_knowledge.json")
                ]:
                    if os.path.exists(k_path):
                        with open(k_path, "r", encoding="utf-8") as kf:
                            doc_items = json.load(kf)
                        for d in doc_items:
                            text_blob = f"{d.get('question', '')} {d.get('answer', '')} {' '.join(d.get('keywords', []))}"
                            seeds.append(text_blob)
                        break
            except Exception as e:
                logger.debug(f"Could not seed TF-IDF from corpus: {e}")

        self.vectorizer.fit(seeds)

    def embed_text(self, text: str) -> List[float]:
        vec = self.vectorizer.transform([text]).toarray()[0]
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
        else:
            vec = np.ones(len(vec)) / math.sqrt(len(vec))
        return vec.tolist()

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        matrix = self.vectorizer.transform(texts).toarray()
        results = []
        for vec in matrix:
            norm = np.linalg.norm(vec)
            if norm > 0:
                vec = vec / norm
            else:
                vec = np.ones(len(vec)) / math.sqrt(len(vec))
            results.append(vec.tolist())
        return results


class EmbeddingProviderFactory:
    _instance: Optional[EmbeddingProvider] = None

    @classmethod
    def get_provider(cls) -> EmbeddingProvider:
        if cls._instance is not None:
            return cls._instance

        # We use TfidfDenseEmbeddingProvider as fast local default
        cls._instance = TfidfDenseEmbeddingProvider()
        return cls._instance

    @classmethod
    def reset(cls):
        cls._instance = None
