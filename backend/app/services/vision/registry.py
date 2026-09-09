from typing import Dict, Any, List, Optional
from pydantic import BaseModel

class DiseaseInfo(BaseModel):
    disease_id: str
    common_name: str
    scientific_name: Optional[str] = None
    pathogen_type: str  # fungal, bacterial, viral, pest_induced, physiological, healthy
    symptoms: List[str]
    ipm_treatment: str
    chemical_treatment: str
    prevention_advisory: str

class VisionModelRegistry:
    """
    Catalog of supported crops, pathologically verified plant diseases,
    diagnostic symptoms, and CIBRC-compliant IPM treatments.
    """
    CROP_TAXONOMY: Dict[str, Dict[str, DiseaseInfo]] = {
        "chilli": {
            "leaf_curl": DiseaseInfo(
                disease_id="chilli_leaf_curl",
                common_name="Chilli Leaf Curl Virus (Gemini virus transmitted by Whiteflies)",
                scientific_name="Chilli leaf curl virus (ChiLCV)",
                pathogen_type="viral",
                symptoms=["Upward puckering and curling of leaves", "Shortened internodes and bushy stunted growth", "Thickened, brittle leaves with reduced pod size"],
                ipm_treatment="Install yellow sticky traps (10-15 per acre). Spray 10,000 ppm Neem oil (Azadirachtin) @ 2ml/L to control vector whiteflies.",
                chemical_treatment="Fipronil 5% SC @ 2ml/L or Diafenthiuron 50% WP @ 1g/L on lower leaf surfaces.",
                prevention_advisory="Eradicate weed hosts (Solanum nigrum) along field borders. Never spray broad-spectrum pyrethroids during active bloom."
            ),
            "leaf_spot": DiseaseInfo(
                disease_id="chilli_cercospora_leaf_spot",
                common_name="Cercospora Leaf Spot / Frog-eye Spot",
                scientific_name="Cercospora capsici",
                pathogen_type="fungal",
                symptoms=["Circular brown lesions with distinct gray centers", "Dark brown margins surrounded by yellowish halo", "Premature defoliation in severe infections"],
                ipm_treatment="Spray bio-fungicide Trichoderma viride or Pseudomonas fluorescens @ 5g/L.",
                chemical_treatment="Mancozeb 75% WP @ 2.5g/L or Azoxystrobin 23% SC @ 1ml/L.",
                prevention_advisory="Avoid overhead sprinkler irrigation; ensure adequate spacing for cross-ventilation."
            ),
            "healthy": DiseaseInfo(
                disease_id="chilli_healthy",
                common_name="Healthy Chilli Foliage",
                pathogen_type="healthy",
                symptoms=["Uniform green leaf pigmentation", "Normal vegetative expansion", "Absence of curling or necrotic lesions"],
                ipm_treatment="Maintain regular monitoring and balanced NPK nutrition.",
                chemical_treatment="No chemical intervention required.",
                prevention_advisory="Continue standard intercultural operations and soil moisture management."
            )
        },
        "rice": {
            "bacterial_blight": DiseaseInfo(
                disease_id="rice_bacterial_leaf_blight",
                common_name="Bacterial Leaf Blight (BLB)",
                scientific_name="Xanthomonas oryzae pv. oryzae",
                pathogen_type="bacterial",
                symptoms=["Water-soaked stripes starting from leaf tips", "Yellowish to grayish-white undulating lesion margins", "Milky bacterial ooze beads on dew mornings"],
                ipm_treatment="Drain excess water from the field. Apply cow dung slurry filtrate (20%) or Pseudomonas fluorescens @ 5g/L.",
                chemical_treatment="Copper Oxychloride 50% WP @ 2.5g/L + Streptocycline @ 0.1g/L.",
                prevention_advisory="Avoid excessive nitrogen application; split nitrogen into 3 equal top dressings."
            ),
            "blast": DiseaseInfo(
                disease_id="rice_blast",
                common_name="Rice Blast (Leaf & Neck Blast)",
                scientific_name="Magnaporthe oryzae",
                pathogen_type="fungal",
                symptoms=["Spindle/diamond-shaped lesions with brown borders and ash-gray centers", "Blackish rot at panicle neck causing chaffy grains"],
                ipm_treatment="Seed treatment with Trichoderma viride @ 10g/kg seed.",
                chemical_treatment="Tricyclazole 75% WP @ 0.6g/L or Isoprothiolane 40% EC @ 1.5ml/L.",
                prevention_advisory="Maintain continuous shallow standing water during tillering to panicle initiation."
            ),
            "brown_spot": DiseaseInfo(
                disease_id="rice_brown_spot",
                common_name="Brown Spot",
                scientific_name="Bipolaris oryzae",
                pathogen_type="fungal",
                symptoms=["Small oval sesame-seed-like dark brown spots on coleoptiles and leaves"],
                ipm_treatment="Correct soil nutrient deficiencies (Zinc and Potassium).",
                chemical_treatment="Mancozeb 75% WP @ 2g/L.",
                prevention_advisory="Apply balanced potash fertilizers before panicle emergence."
            ),
            "healthy": DiseaseInfo(
                disease_id="rice_healthy",
                common_name="Healthy Rice Plant",
                pathogen_type="healthy",
                symptoms=["Vigorous green tillers", "Intact leaf blades without lesions"],
                ipm_treatment="Follow standard water-saving irrigation (AWD - Alternate Wetting and Drying).",
                chemical_treatment="None required.",
                prevention_advisory="Monitor for early stem borer dead hearts."
            )
        },
        "tomato": {
            "bacterial_spot": DiseaseInfo(
                disease_id="tomato_bacterial_spot",
                common_name="Bacterial Spot",
                scientific_name="Xanthomonas perforans",
                pathogen_type="bacterial",
                symptoms=["Small dark brown water-soaked lesions on leaves", "Raised scab-like spots with chlorotic yellow halos", "Defoliation and sunscald of exposed fruit"],
                ipm_treatment="Seed treatment with hot water (50°C for 25 min). Spray Copper Oxychloride 50% WP @ 2.5g/L + Streptocycline @ 0.1g/L.",
                chemical_treatment="Copper Hydroxide 53.8% DF @ 1.5g/L or Mancozeb + Copper complex.",
                prevention_advisory="Avoid overhead irrigation; sanitize pruning shears between plants."
            ),
            "early_blight": DiseaseInfo(
                disease_id="tomato_early_blight",
                common_name="Early Blight",
                scientific_name="Alternaria solani",
                pathogen_type="fungal",
                symptoms=["Concentric target-board rings on older lower leaves", "Yellow halo around dark brown spots", "Stem collar rot in young transplants"],
                ipm_treatment="Prune lower infected leaves touching the soil. Mulch around plant base with clean straw.",
                chemical_treatment="Chlorothalonil 75% WP @ 2g/L or Mancozeb 75% WP @ 2.5g/L or Azoxystrobin 23% SC @ 1ml/L.",
                prevention_advisory="Crop rotation away from solanaceous crops for at least 2 seasons. Ensure wide row spacing for canopy aeration."
            ),
            "late_blight": DiseaseInfo(
                disease_id="tomato_late_blight",
                common_name="Late Blight",
                scientific_name="Phytophthora infestans",
                pathogen_type="fungal",
                symptoms=["Irregular water-soaked greasy lesions rapidly expanding from leaf tips", "White cottony fungal down on undersides during cool humid weather", "Dark brown firm fruit rot"],
                ipm_treatment="Immediately remove and bury severely blighted haulms. Avoid overhead watering during cloudy spells.",
                chemical_treatment="Metalaxyl-M 4% + Mancozeb 64% WP @ 2.5g/L or Cymoxanil 8% + Mancozeb 64% WP @ 2g/L.",
                prevention_advisory="Monitor regional blight forecasting warnings; spray preventive protectant before dense fog spells."
            ),
            "leaf_mold": DiseaseInfo(
                disease_id="tomato_leaf_mold",
                common_name="Leaf Mold",
                scientific_name="Passalora fulva",
                pathogen_type="fungal",
                symptoms=["Pale yellow chlorotic patches on upper leaf surface", "Olive-green to velvety brown mold growth on lower leaf surface", "Leaves curl, wither, and drop prematurely"],
                ipm_treatment="Increase ventilation in polyhouses/field tunnels. Reduce relative humidity below 85%.",
                chemical_treatment="Difenoconazole 25% EC @ 0.5ml/L or Copper Oxychloride @ 2.5g/L.",
                prevention_advisory="Ensure drip irrigation instead of sprinkler; stake plants to promote air movement."
            ),
            "septoria_leaf_spot": DiseaseInfo(
                disease_id="tomato_septoria_leaf_spot",
                common_name="Septoria Leaf Spot",
                scientific_name="Septoria lycopersici",
                pathogen_type="fungal",
                symptoms=["Numerous small circular spots with dark brown margins and sunken grayish centers", "Minute black fruiting bodies (pycnidia) visible inside lesions", "Progressive defoliation from lower canopy upwards"],
                ipm_treatment="Deep summer plowing to bury crop debris. Spray bio-agent Pseudomonas fluorescens @ 5g/L.",
                chemical_treatment="Mancozeb 75% WP @ 2.5g/L or Chlorothalonil 75% WP @ 2g/L.",
                prevention_advisory="Eradicate solanaceous weeds (e.g. nightshade) around farm borders."
            ),
            "spider_mites": DiseaseInfo(
                disease_id="tomato_spider_mites",
                common_name="Two-Spotted Spider Mites",
                scientific_name="Tetranychus urticae",
                pathogen_type="pest_induced",
                symptoms=["Fine stippling / yellow speckling on upper leaf surface", "Delicate silken webbing under leaf surfaces", "Leaves turn bronze, dry out, and drop"],
                ipm_treatment="Spray wettable sulfur 80% WDG @ 3g/L or Neem oil 10,000 ppm @ 3ml/L. Conserve predatory phytoseiid mites.",
                chemical_treatment="Spiromesifen 22.9% SC @ 1ml/L or Propargite 57% EC @ 2ml/L.",
                prevention_advisory="Avoid excessive dusty field borders; spray water wash on lower leaves during hot dry spells."
            ),
            "target_spot": DiseaseInfo(
                disease_id="tomato_target_spot",
                common_name="Target Spot",
                scientific_name="Corynespora cassiicola",
                pathogen_type="fungal",
                symptoms=["Pinpoint brown spots expanding into circular lesions with light brown centers", "Distinct concentric rings resembling early blight but without yellow halos", "Pitted lesions on fruit"],
                ipm_treatment="Improve canopy air circulation. Avoid handling wet plants.",
                chemical_treatment="Azoxystrobin 18.2% + Difenoconazole 11.4% SC @ 1ml/L or Mancozeb @ 2.5g/L.",
                prevention_advisory="Destroy volunteer tomato plants and maintain 3-year crop rotation."
            ),
            "yellow_leaf_curl_virus": DiseaseInfo(
                disease_id="tomato_leaf_curl",
                common_name="Tomato Yellow Leaf Curl Virus (TYLCV)",
                scientific_name="Tomato yellow leaf curl virus (Begomovirus)",
                pathogen_type="viral",
                symptoms=["Severe upward and inward leaf curling", "Thickened puckered leaves with vein clearing and chlorosis", "Stunted bushy growth and premature flower drop"],
                ipm_treatment="Set up 15 yellow sticky traps/acre. Spray Azadirachtin (Neem) 10,000 ppm @ 2ml/L to control whitefly vector.",
                chemical_treatment="Imidacloprid 17.8% SL @ 0.3ml/L or Acetamiprid 20% SP @ 0.4g/L on lower leaf surfaces.",
                prevention_advisory="Use silver reflective mulch to deter whitefly landing; install 40-mesh insect net in nursery beds."
            ),
            "leaf_curl": DiseaseInfo(
                disease_id="tomato_leaf_curl",
                common_name="Tomato Leaf Curl Virus (TYLCV)",
                scientific_name="Tomato yellow leaf curl virus (Begomovirus)",
                pathogen_type="viral",
                symptoms=["Severe upward and inward leaf curling", "Thickened puckered leaves with vein clearing and chlorosis", "Stunted bushy growth and premature flower drop"],
                ipm_treatment="Set up 15 yellow sticky traps/acre. Spray Azadirachtin (Neem) 10,000 ppm @ 2ml/L.",
                chemical_treatment="Imidacloprid 17.8% SL @ 0.3ml/L or Acetamiprid 20% SP @ 0.4g/L.",
                prevention_advisory="Use silver reflective mulch to deter whitefly vectors."
            ),
            "mosaic_virus": DiseaseInfo(
                disease_id="tomato_mosaic_virus",
                common_name="Tomato Mosaic Virus (ToMV)",
                scientific_name="Tomato mosaic virus (Tobamovirus)",
                pathogen_type="viral",
                symptoms=["Mottled light and dark green mosaic patterns on leaves", "Distorted fern-leaf or shoe-string appearance", "Internal brown necrotic rings in ripening fruit"],
                ipm_treatment="Uproot and burn infected plants immediately. Workers must wash hands with 20% non-fat dry milk or soap before touching plants.",
                chemical_treatment="No direct chemical cure for viral infections. Apply micronutrients and bio-stimulants to support systemic resistance.",
                prevention_advisory="Do not smoke or use tobacco near the crop (tobamovirus is mechanically transmissible via touch)."
            ),
            "healthy": DiseaseInfo(
                disease_id="tomato_healthy",
                common_name="Healthy Tomato Foliage",
                pathogen_type="healthy",
                symptoms=["Vibrant dark green leaf expansion", "Sturdy vigorous foliage without chlorosis or necrosis", "Normal turgor pressure and uniform vegetative growth"],
                ipm_treatment="Stake plants to keep leaves elevated above soil splash. Maintain balanced drip irrigation.",
                chemical_treatment="None required.",
                prevention_advisory="Standard foliar calcium spray during flowering to prevent blossom end rot."
            )
        },
        "potato": {
            "early_blight": DiseaseInfo(
                disease_id="potato_early_blight",
                common_name="Early Blight of Potato",
                scientific_name="Alternaria solani",
                pathogen_type="fungal",
                symptoms=["Dark brown target-like spots with concentric rings on foliage"],
                ipm_treatment="Apply Trichoderma viride @ 5g/L.",
                chemical_treatment="Mancozeb 75% WP @ 2.5g/L.",
                prevention_advisory="Avoid nitrogen deficiency; maintain optimal plant vigor."
            ),
            "late_blight": DiseaseInfo(
                disease_id="potato_late_blight",
                common_name="Late Blight of Potato",
                scientific_name="Phytophthora infestans",
                pathogen_type="fungal",
                symptoms=["Water-soaked pale green to brown lesions rapidly expanding in cool humid weather", "White cottony fungal growth on lower leaf surface"],
                ipm_treatment="Destroy infected haulms immediately. Hill up rows to protect tubers from spore wash.",
                chemical_treatment="Metalaxyl 8% + Mancozeb 64% WP @ 2g/L or Cymoxanil + Mancozeb @ 2g/L.",
                prevention_advisory="Check regional late blight forewarning alerts during cloudy misty winter spells."
            ),
            "healthy": DiseaseInfo(
                disease_id="potato_healthy",
                common_name="Healthy Potato Canopy",
                pathogen_type="healthy",
                symptoms=["Lush dark green leaves, vigorous canopy expansion"],
                ipm_treatment="Routine scouting for aphid vectors.",
                chemical_treatment="None required.",
                prevention_advisory="Regular hilling and weed management."
            )
        },
        "sugarcane": {
            "red_rot": DiseaseInfo(
                disease_id="sugarcane_red_rot",
                common_name="Red Rot of Sugarcane",
                scientific_name="Colletotrichum falcatum",
                pathogen_type="fungal",
                symptoms=["Third or fourth leaf from top shows yellowing and drying", "Longitudinal splitting reveals red internal tissues with crosswise white patches", "Sour alcoholic fermentation odor"],
                ipm_treatment="Uproot and burn affected clumps immediately. Plant disease-free setts treated with Carbendazim.",
                chemical_treatment="Sett dip in Carbendazim 50% WP (1g/L water) for 15 minutes before planting.",
                prevention_advisory="Avoid ratoon cropping in red-rot affected fields."
            ),
            "healthy": DiseaseInfo(
                disease_id="sugarcane_healthy",
                common_name="Healthy Sugarcane Foliage",
                pathogen_type="healthy",
                symptoms=["Erect robust green leaves with clear white midribs"],
                ipm_treatment="Earthing up operations at 90 days to prevent lodging.",
                chemical_treatment="None required.",
                prevention_advisory="Ensure proper furrow irrigation intervals."
            )
        },
        "banana": {
            "sigatoka": DiseaseInfo(
                disease_id="banana_sigatoka",
                common_name="Black Sigatoka / Yellow Sigatoka",
                scientific_name="Pseudocercospora fijiensis",
                pathogen_type="fungal",
                symptoms=["Narrow reddish-brown streaks parallel to leaf veins", "Elliptical spots with gray centers and black borders", "Extensive premature leaf defoliation"],
                ipm_treatment="Deleafing of severely infected necrotic leaves. Ensure optimal plantation drainage.",
                chemical_treatment="Propiconazole 25% EC @ 1ml/L or Carbendazim 50% WP @ 1g/L with mineral oil.",
                prevention_advisory="Maintain wide spacing (1.8m x 1.8m) to facilitate sunlight and air penetration."
            ),
            "cordana": DiseaseInfo(
                disease_id="banana_cordana",
                common_name="Cordana Leaf Spot",
                scientific_name="Cordana musae",
                pathogen_type="fungal",
                symptoms=["Large oval or diamond-shaped pale brown lesions with bright yellow halos", "Concentric zonation on older leaves"],
                ipm_treatment="Removal of lower decaying leaves. Balanced potassium nutrition.",
                chemical_treatment="Mancozeb 75% WP @ 2.5g/L.",
                prevention_advisory="Avoid dense under-canopy weed growth."
            ),
            "pestalotiopsis": DiseaseInfo(
                disease_id="banana_pestalotiopsis",
                common_name="Pestalotiopsis Leaf Blight",
                scientific_name="Pestalotiopsis microspora",
                pathogen_type="fungal",
                symptoms=["Irregular dark brown marginal necrosis with ash-gray center"],
                ipm_treatment="Prune infected marginal tissue. Avoid wounding leaves.",
                chemical_treatment="Copper Oxychloride 50% WP @ 2.5g/L.",
                prevention_advisory="Maintain soil organic carbon with FYM."
            ),
            "healthy": DiseaseInfo(
                disease_id="banana_healthy",
                common_name="Healthy Banana Foliage",
                pathogen_type="healthy",
                symptoms=["Broad vibrant green intact leaf blades with stout midribs"],
                ipm_treatment="Maintain regular suckering and pseudostem earthing.",
                chemical_treatment="None required.",
                prevention_advisory="Regular irrigation intervals."
            )
        },
        "corn_maize": {
            "blight": DiseaseInfo(
                disease_id="maize_leaf_blight",
                common_name="Northern Corn Leaf Blight (NCLB)",
                scientific_name="Exserohilum turcicum",
                pathogen_type="fungal",
                symptoms=["Long elliptical cigar-shaped grayish-green to tan lesions", "Lesions coalesce covering large areas of the leaf blade"],
                ipm_treatment="Crop rotation with non-host legumes. Deep tillage of infected stubble.",
                chemical_treatment="Azoxystrobin 18.2% + Difenoconazole 11.4% SC @ 1ml/L or Mancozeb @ 2.5g/L.",
                prevention_advisory="Plant tolerant hybrids; avoid excessive overhead sprinkler wetting."
            ),
            "common_rust": DiseaseInfo(
                disease_id="maize_common_rust",
                common_name="Common Rust of Maize",
                scientific_name="Puccinia sorghi",
                pathogen_type="fungal",
                symptoms=["Small powdery golden-brown to cinnamon-brown pustules on both leaf surfaces"],
                ipm_treatment="Destroy volunteer maize plants.",
                chemical_treatment="Propiconazole 25% EC @ 1ml/L.",
                prevention_advisory="Plant early in the season to escape peak spore showers."
            ),
            "gray_leaf_spot": DiseaseInfo(
                disease_id="maize_gray_leaf_spot",
                common_name="Gray Leaf Spot",
                scientific_name="Cercospora zeae-maydis",
                pathogen_type="fungal",
                symptoms=["Rectangular blocky lesions delimited by parallel leaf veins"],
                ipm_treatment="Incorporate crop residue after harvest.",
                chemical_treatment="Pyraclostrobin 20% WG @ 1g/L.",
                prevention_advisory="Ensure balanced nitrogen and potassium fertilization."
            ),
            "healthy": DiseaseInfo(
                disease_id="maize_healthy",
                common_name="Healthy Maize Foliage",
                pathogen_type="healthy",
                symptoms=["Erect robust green leaves with intact venation"],
                ipm_treatment="Monitor whorl leaves for fall armyworm eggs.",
                chemical_treatment="None required.",
                prevention_advisory="Timely intercultural weeding."
            )
        },
        "guava": {
            "anthracnose": DiseaseInfo(
                disease_id="guava_anthracnose",
                common_name="Guava Anthracnose / Die-back",
                scientific_name="Colletotrichum gloeosporioides",
                pathogen_type="fungal",
                symptoms=["Pinhead necrotic spots on leaves and twigs leading to die-back", "Dark sunken lesions on maturing fruit"],
                ipm_treatment="Prune and burn dead twigs 5 cm below infected zone. Apply Bordeaux paste on cut ends.",
                chemical_treatment="Copper Oxychloride 50% WP @ 3g/L or Carbendazim @ 1g/L.",
                prevention_advisory="Avoid fruit injury during harvest; spray preventive copper after post-harvest pruning."
            ),
            "fruit_fly": DiseaseInfo(
                disease_id="guava_fruit_fly",
                common_name="Oriental Fruit Fly Damage",
                scientific_name="Bactrocera dorsalis",
                pathogen_type="pest_induced",
                symptoms=["Oviposition puncture marks on tender fruits", "Premature fruit drop and internal pulp decay"],
                ipm_treatment="Install methyl eugenol pheromone traps @ 10/acre. Rake soil around tree basins to expose pupae.",
                chemical_treatment="Bait spray: Jaggery (10g) + Malathion 50% EC (2ml) per litre water.",
                prevention_advisory="Bag individual fruits with butter paper covers at marble stage."
            ),
            "healthy": DiseaseInfo(
                disease_id="guava_healthy",
                common_name="Healthy Guava Foliage",
                pathogen_type="healthy",
                symptoms=["Glossy dark green elliptical leaves with prominent venation"],
                ipm_treatment="Standard basin weeding and canopy light pruning.",
                chemical_treatment="None required.",
                prevention_advisory="Annual organic manuring before monsoon."
            )
        },
        "cucumber_pumpkin": {
            "downy_mildew": DiseaseInfo(
                disease_id="cucurbit_downy_mildew",
                common_name="Downy Mildew of Cucurbits",
                scientific_name="Pseudoperonospora cubensis",
                pathogen_type="fungal",
                symptoms=["Angular yellow chlorotic lesions bounded by veins on upper surface", "Purplish-gray downy sporulation on lower leaf surface"],
                ipm_treatment="Avoid overhead irrigation. Ensure wide vine spacing on trellises.",
                chemical_treatment="Cymoxanil 8% + Mancozeb 64% WP @ 2g/L or Metalaxyl 8% + Mancozeb 64% WP @ 2.5g/L.",
                prevention_advisory="Spray protectant Mancozeb before anticipated rain spells."
            ),
            "powdery_mildew": DiseaseInfo(
                disease_id="cucurbit_powdery_mildew",
                common_name="Powdery Mildew",
                scientific_name="Podosphaera xanthii",
                pathogen_type="fungal",
                symptoms=["White talcum-like powdery talc spots on upper leaf surfaces and stems", "Leaves turn brown, curl, and become brittle"],
                ipm_treatment="Spray wettable sulfur 80% WDG @ 2.5g/L or potassium bicarbonate @ 3g/L.",
                chemical_treatment="Difenoconazole 25% EC @ 0.5ml/L or Azoxystrobin @ 1ml/L.",
                prevention_advisory="Avoid excessive nitrogen fertilization."
            ),
            "bacterial_leaf_spot": DiseaseInfo(
                disease_id="cucurbit_bacterial_spot",
                common_name="Bacterial Leaf Spot",
                scientific_name="Xanthomonas cucurbitae",
                pathogen_type="bacterial",
                symptoms=["Small angular water-soaked lesions drying into translucent beige spots"],
                ipm_treatment="Hot water seed treatment. Avoid working among wet vines.",
                chemical_treatment="Copper Hydroxide 53.8% DF @ 1.5g/L + Streptocycline @ 0.1g/L.",
                prevention_advisory="Rotate with non-cucurbit crops for 2 years."
            ),
            "mosaic_disease": DiseaseInfo(
                disease_id="cucurbit_mosaic_virus",
                common_name="Cucumber Mosaic Virus (CMV)",
                scientific_name="Cucumber mosaic virus",
                pathogen_type="viral",
                symptoms=["Yellow-green foliar mosaic, distortion, and blistering", "Severe vine stunting"],
                ipm_treatment="Control aphid vectors with yellow sticky traps and neem oil spray @ 3ml/L.",
                chemical_treatment="No chemical cure for viral infections; rogue infected vines immediately.",
                prevention_advisory="Eradicate weed hosts (Commelina, Solanum) around field perimeters."
            ),
            "healthy": DiseaseInfo(
                disease_id="cucurbit_healthy",
                common_name="Healthy Cucurbit Foliage",
                pathogen_type="healthy",
                symptoms=["Vibrant green lobed leaves with robust petioles"],
                ipm_treatment="Maintain regular trellis training and furrow irrigation.",
                chemical_treatment="None required.",
                prevention_advisory="Routine scouting for leaf beetles and aphids."
            )
        },
        "apple": {
            "apple_scab": DiseaseInfo(
                disease_id="apple_scab",
                common_name="Apple Scab",
                scientific_name="Venturia inaequalis",
                pathogen_type="fungal",
                symptoms=["Dull olive-green velvety spots turning dark brown to black on leaves and fruit", "Distorted puckered leaves and scabby cracked fruit"],
                ipm_treatment="Rake and destroy fallen overwintered leaves. Urea spray (5%) on fallen foliage to accelerate leaf decay.",
                chemical_treatment="Difenoconazole 25% EC @ 0.3ml/L or Mancozeb 75% WP @ 2.5g/L or Dodine @ 1g/L.",
                prevention_advisory="Maintain open tree canopy with winter pruning to facilitate rapid leaf drying."
            ),
            "black_rot": DiseaseInfo(
                disease_id="apple_black_rot",
                common_name="Black Rot / Frogeye Leaf Spot",
                scientific_name="Botryosphaeria obtusa",
                pathogen_type="fungal",
                symptoms=["Small purple spots expanding into circular lesions with tan centers and purple margins (frogeye appearance)", "Black firm rot in fruit with concentric rings"],
                ipm_treatment="Prune out dead wood, mummified fruits, and fire blight cankers during dormancy.",
                chemical_treatment="Captan 50% WP @ 2.5g/L or Thiophanate-methyl 70% WP @ 1g/L.",
                prevention_advisory="Remove all pruned wood from the orchard immediately."
            ),
            "cedar_apple_rust": DiseaseInfo(
                disease_id="apple_cedar_rust",
                common_name="Cedar Apple Rust",
                scientific_name="Gymnosporangium juniperi-virginianae",
                pathogen_type="fungal",
                symptoms=["Bright orange-yellow spots on upper leaf surfaces with black fungal fruiting bodies in center", "Tube-like aecial structures on lower leaf surface"],
                ipm_treatment="Eradicate wild red cedar / juniper trees within 1 km radius of orchard.",
                chemical_treatment="Myclobutanil 10% WP @ 0.5g/L or Mancozeb @ 2.5g/L.",
                prevention_advisory="Plant rust-resistant apple cultivars."
            ),
            "healthy": DiseaseInfo(
                disease_id="apple_healthy",
                common_name="Healthy Apple Canopy",
                pathogen_type="healthy",
                symptoms=["Uniform green elliptical leaves, strong spur leaf clusters"],
                ipm_treatment="Regular dormant pruning and balanced orchard nutrition.",
                chemical_treatment="None required.",
                prevention_advisory="Ensure proper tree basin mulching."
            )
        }
    }

    @classmethod
    def get_supported_crops(cls) -> List[str]:
        return list(cls.CROP_TAXONOMY.keys())

    @classmethod
    def get_disease_info(cls, crop: str, disease_key: str) -> Optional[DiseaseInfo]:
        crop_dict = cls.CROP_TAXONOMY.get(crop.lower())
        if not crop_dict:
            return None
        # 1. Exact match
        norm = (disease_key or "").lower().strip()
        if norm in crop_dict:
            return crop_dict[norm]
        # 2. Healthy keyword match
        if "health" in norm and "healthy" in crop_dict:
            return crop_dict["healthy"]
        # 3. Normalized alphanumeric / substring match
        clean = norm.replace("_", "").replace("-", "").replace(" ", "").replace(crop.lower(), "")
        for k, v in crop_dict.items():
            k_clean = k.replace("_", "").replace("-", "").replace(" ", "")
            if clean and (clean in k_clean or k_clean in clean):
                return v
        # 4. Partial word overlap
        words = [w for w in norm.replace("_", " ").split() if len(w) > 3]
        for w in words:
            for k, v in crop_dict.items():
                if w in k:
                    return v
        # 5. Crop-scoped fallback (never cross crops)
        for k, v in crop_dict.items():
            if k != "healthy":
                return v
        return next(iter(crop_dict.values())) if crop_dict else None
