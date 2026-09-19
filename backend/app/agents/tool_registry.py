from typing import Dict, Any, List
from decimal import Decimal
from app.services.weather.weather_service import WeatherService
from app.services.market.market_service import MarketService
from app.services.finance.profit_service import FinancialService
from app.services.simulation.simulation_service import SimulationService
from app.services.risk.risk_service import RiskAssessmentService
from app.services.crop.lifecycle_service import CropLifecycleService
from app.services.crop.recommendation_service import CropRecommendationService, CropRecommendationInput
from app.services.crop.fertilizer_service import FertilizerRecommendationService, FertilizerInput
from app.services.crop.comparison_service import CropComparisonService
from app.services.yield_prediction.yield_service import YieldPredictionService, YieldPredictionInput
from app.services.rag.rag_service import AgriculturalRAGService, RAGQueryInput
from app.services.farm_manager.state_engine import FarmStateEngine
from app.services.farm_manager.daily_briefing import DailyFarmBriefingService
from app.services.farm_manager.change_detector import FarmChangeDetectionService
from app.services.farm_manager.personal_planner import PersonalCropPlanner
from app.services.farm_manager.farm_plan import FarmPlanManager
from app.services.farm_manager.crop_health_timeline import CropHealthTimeline
from app.services.memory.farm_memory_v2 import FarmMemoryV2
from app.schemas.finance import ProfitCalculationRequest
from app.schemas.simulation import SimulationRequest
from app.schemas.risk import RiskAssessmentRequest

class ToolRegistry:
    """
    Central Tool Registry providing deterministic domain tool execution for BHOOMI AI Agent.
    Strictly isolates numerical ML/finance calculations and trusted RAG retrieval from LLM synthesis.
    """
    @staticmethod
    def get_tool_definitions() -> List[Dict[str, Any]]:
        return [
            {
                "name": "crop_recommendation",
                "description": "ML recommendation of top suitable crops based on soil N, P, K, pH, rainfall, and temperature",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "nitrogen": {"type": "number"},
                        "phosphorus": {"type": "number"},
                        "potassium": {"type": "number"},
                        "ph": {"type": "number"},
                        "rainfall": {"type": "number"},
                        "temperature": {"type": "number"},
                        "humidity": {"type": "number"}
                    },
                    "required": ["nitrogen", "phosphorus", "potassium", "ph", "rainfall"]
                }
            },
            {
                "name": "yield_prediction",
                "description": "ML prediction of expected crop yield (quintals/acre & tonnes/ha) with confidence interval",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "crop_name": {"type": "string"},
                        "state": {"type": "string"},
                        "season": {"type": "string"},
                        "area_acres": {"type": "number"},
                        "annual_rainfall_mm": {"type": "number"}
                    },
                    "required": ["crop_name", "area_acres"]
                }
            },
            {
                "name": "fertilizer_recommendation",
                "description": "Agronomic RAG and SafetyEngine validated fertilizer dosage and application schedule",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "crop_name": {"type": "string"},
                        "crop_stage": {"type": "string"},
                        "soil_type": {"type": "string"},
                        "nitrogen": {"type": "number"},
                        "phosphorus": {"type": "number"},
                        "potassium": {"type": "number"}
                    },
                    "required": ["crop_name"]
                }
            },
            {
                "name": "compare_crops",
                "description": "Multi-crop side-by-side comparison of yield, revenue, costs, net profit, and risks",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "crops": {"type": "array", "items": {"type": "string"}},
                        "area_acres": {"type": "number"},
                        "soil_type": {"type": "string"},
                        "location": {"type": "string"}
                    },
                    "required": ["crops"]
                }
            },
            {
                "name": "search_agricultural_rag",
                "description": "Search verified ICAR, SAU, and official agricultural extension research documents",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"},
                        "crop": {"type": "string"}
                    },
                    "required": ["query"]
                }
            },
            {
                "name": "get_current_weather",
                "description": "Fetch current meteorological facts and forecast for farmer location",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "location": {"type": "string", "description": "District / village name"}
                    }
                }
            },
            {
                "name": "get_mandi_prices",
                "description": "Fetch real mandi price, transport cost, and net realization comparison",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "commodity": {"type": "string"},
                        "location": {"type": "string"}
                    },
                    "required": ["commodity"]
                }
            },
            {
                "name": "calculate_profit",
                "description": "Deterministic Decimal profit, gross revenue, and cost calculation",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "crop_name": {"type": "string"},
                        "area_acres": {"type": "number"},
                        "expected_yield_quintals_per_acre": {"type": "number"},
                        "expected_market_price_per_quintal": {"type": "number"},
                        "cultivation_cost_total": {"type": "number"}
                    },
                    "required": ["crop_name", "area_acres", "expected_yield_quintals_per_acre", "expected_market_price_per_quintal", "cultivation_cost_total"]
                }
            },
            {
                "name": "run_what_if_simulation",
                "description": "Deterministic What-If farm simulator for price drops, yield shocks, and weather deficit",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "crop_name": {"type": "string"},
                        "area_acres": {"type": "number"},
                        "price_change_percent": {"type": "number"},
                        "yield_change_percent": {"type": "number"},
                        "rainfall_change_percent": {"type": "number"}
                    },
                    "required": ["crop_name", "area_acres"]
                }
            },
            {
                "name": "assess_farm_risk",
                "description": "Evaluates multi-factor risk across weather, yield, market, crop health, and economics",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "crop_name": {"type": "string"},
                        "crop_stage": {"type": "string"},
                        "location": {"type": "string"}
                    },
                    "required": ["crop_name"]
                }
            },
            {
                "name": "get_daily_briefing",
                "description": "Generates structured Today or Weekly farm briefing with prioritized actions",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "timeframe": {"type": "string", "enum": ["today", "week"]}
                    }
                }
            },
            {
                "name": "get_farm_changes",
                "description": "Analyzes what changed in weather, mandi market, crop stage, and farm tasks since yesterday",
                "parameters": {
                    "type": "object",
                    "properties": {}
                }
            },
            {
                "name": "plan_season_crops",
                "description": "Ranks seasonal crops with multi-objective score (agronomic fit, profit, water, risk)",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "area_acres": {"type": "number"},
                        "season": {"type": "string"}
                    }
                }
            },
            {
                "name": "record_farmer_decision",
                "description": "Records the farmer's definitive crop planting or selling decision and updates the Farm Plan",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "decision": {"type": "string"},
                        "crop_name": {"type": "string"}
                    },
                    "required": ["decision"]
                }
            },
            {
                "name": "diagnose_plant_disease",
                "description": "Analyze leaf photo using deep learning vision models to diagnose plant diseases and provide verified IPM treatments",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "crop_name": {"type": "string", "description": "Crop name, e.g. tomato, chilli"},
                        "image_path": {"type": "string", "description": "Path to uploaded leaf image file"}
                    },
                    "required": ["crop_name"]
                }
            }
        ]

    @staticmethod
    async def execute_tool(tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        if tool_name == "crop_recommendation":
            inp = CropRecommendationInput(
                nitrogen=float(arguments.get("nitrogen", 90.0)),
                phosphorus=float(arguments.get("phosphorus", 42.0)),
                potassium=float(arguments.get("potassium", 43.0)),
                temperature=float(arguments.get("temperature", 25.0)),
                humidity=float(arguments.get("humidity", 80.0)),
                ph=float(arguments.get("ph", 6.5)),
                rainfall=float(arguments.get("rainfall", 200.0))
            )
            res = CropRecommendationService.predict(inp)
            return {
                "card_type": "crop_recommendation_card",
                "title": f"Crop Recommendation ML ({res.model_name})",
                "data": res.model_dump()
            }

        elif tool_name == "yield_prediction":
            inp = YieldPredictionInput(
                crop_name=arguments.get("crop_name") or arguments.get("crop") or "Crop",
                state=arguments.get("state") or "India",
                season=arguments.get("season", "Kharif"),
                area_acres=float(arguments.get("area_acres", 1.0)),
                annual_rainfall_mm=float(arguments.get("annual_rainfall_mm", 850.0))
            )
            res = YieldPredictionService.predict(inp)
            return {
                "card_type": "yield_prediction_card",
                "title": f"Yield Prediction: {inp.crop_name}",
                "data": res.model_dump()
            }

        elif tool_name == "fertilizer_recommendation":
            inp = FertilizerInput(
                crop_name=arguments.get("crop_name") or arguments.get("crop") or "Crop",
                crop_stage=arguments.get("crop_stage", "vegetative"),
                soil_type=arguments.get("soil_type", "Loam"),
                nitrogen=float(arguments.get("nitrogen", 40.0)),
                phosphorus=float(arguments.get("phosphorus", 20.0)),
                potassium=float(arguments.get("potassium", 30.0))
            )
            res = FertilizerRecommendationService.recommend(inp)
            return {
                "card_type": "fertilizer_card",
                "title": f"Fertilizer & Nutrient Plan: {inp.crop_name}",
                "data": res.model_dump()
            }

        elif tool_name == "compare_crops":
            crops = arguments.get("crops", ["tomato", "potato"])
            res = CropComparisonService.compare_crops(
                crop_names=crops,
                area_acres=Decimal(str(arguments.get("area_acres", 1.0))),
                soil_type=arguments.get("soil_type", "Loam"),
                location=arguments.get("location", "")
            )
            return {
                "card_type": "comparison_card",
                "title": f"Crop Comparison ({', '.join(crops)})",
                "data": res.model_dump()
            }

        elif tool_name == "search_agricultural_rag":
            q_in = RAGQueryInput(
                query=arguments.get("query", "crop disease management"),
                crop=arguments.get("crop"),
                language=arguments.get("language"),
                intent=arguments.get("intent"),
                state=arguments.get("state"),
                district=arguments.get("district"),
                location=arguments.get("location") if isinstance(arguments.get("location"), dict) else None,
                top_k=int(arguments.get("top_k", 5))
            )
            res = AgriculturalRAGService.search(q_in)
            return {
                "card_type": "rag_evidence_card",
                "title": "Verified ICAR Agricultural Research Evidence",
                "data": res.model_dump()
            }

        elif tool_name == "get_current_weather" or tool_name == "get_farm_weekly_advisory":
            loc = arguments.get("location") or "Farm Location"
            lat = arguments.get("lat")
            lon = arguments.get("lon")
            res = await WeatherService.get_weather(location=loc, lat=lat, lon=lon)
            return {
                "card_type": "weather_card",
                "title": f"Weather Advisory: {loc} ({res.freshness})",
                "data": res.model_dump()
            }

        elif tool_name == "get_mandi_prices":
            commodity = arguments.get("commodity", arguments.get("crop", "Potato"))
            loc = arguments.get("location", arguments.get("district", ""))
            st = arguments.get("state", "")
            m_name = arguments.get("market")
            res = await MarketService.get_mandi_prices(commodity=commodity, state=st, district=loc, market_name=m_name)
            return {
                "card_type": "market_card",
                "title": f"Mandi Net Realization: {commodity} ({res.freshness})",
                "data": res.model_dump()
            }

        elif tool_name == "calculate_profit":
            crop = arguments.get("crop_name") or arguments.get("crop") or "Crop"
            raw_area = arguments.get("land_area") or arguments.get("area_acres")
            area = Decimal(str(raw_area)) if raw_area is not None else None
            area_unit = arguments.get("area_unit", "acre")

            raw_y = arguments.get("expected_yield") or arguments.get("expected_yield_quintals_per_acre")
            y_val = Decimal(str(raw_y)) if raw_y is not None else None

            raw_p = arguments.get("expected_market_price") or arguments.get("expected_market_price_per_quintal")
            p_val = Decimal(str(raw_p)) if raw_p is not None else None

            raw_cost = arguments.get("cultivation_cost_total")
            cost_total = Decimal(str(raw_cost)) if raw_cost is not None else None

            req = ProfitCalculationRequest(
                crop_name=crop,
                land_area=area,
                area_acres=area,
                area_unit=area_unit,
                seed_cost=Decimal(str(arguments["seed_cost"])) if "seed_cost" in arguments and arguments["seed_cost"] is not None else None,
                fertilizer_cost=Decimal(str(arguments["fertilizer_cost"])) if "fertilizer_cost" in arguments and arguments["fertilizer_cost"] is not None else None,
                pesticide_cost=Decimal(str(arguments["pesticide_cost"])) if "pesticide_cost" in arguments and arguments["pesticide_cost"] is not None else None,
                labour_cost=Decimal(str(arguments["labour_cost"])) if "labour_cost" in arguments and arguments["labour_cost"] is not None else None,
                irrigation_cost=Decimal(str(arguments["irrigation_cost"])) if "irrigation_cost" in arguments and arguments["irrigation_cost"] is not None else None,
                machinery_cost=Decimal(str(arguments["machinery_cost"])) if "machinery_cost" in arguments and arguments["machinery_cost"] is not None else None,
                other_cost=Decimal(str(arguments["other_cost"])) if "other_cost" in arguments and arguments["other_cost"] is not None else None,
                cultivation_cost_total=cost_total,
                expected_yield=y_val,
                expected_yield_quintals_per_acre=y_val,
                yield_unit=arguments.get("yield_unit", "quintal"),
                expected_market_price=p_val,
                expected_market_price_per_quintal=p_val,
                price_unit=arguments.get("price_unit", "rupees_per_quintal"),
            )
            res = FinancialService.calculate_profit(req)
            return {
                "card_type": "profit_card",
                "title": f"Financial Plan: {req.crop_name}",
                "data": res.model_dump()
            }

        elif tool_name == "run_what_if_simulation":
            crop = arguments.get("crop_name") or arguments.get("crop") or "Crop"
            raw_area = arguments.get("land_area") or arguments.get("area_acres") or 1.0
            area = Decimal(str(raw_area))
            b_yield = Decimal(str(arguments.get("baseline_yield_quintals_per_acre") or arguments.get("expected_yield") or 10.0))
            b_price = Decimal(str(arguments.get("baseline_market_price_per_quintal") or arguments.get("expected_market_price") or 3000.0))
            b_cost = Decimal(str(arguments.get("baseline_cultivation_cost") or arguments.get("cultivation_cost_total") or 25000.0))

            req = SimulationRequest(
                crop_name=crop,
                area_acres=area,
                baseline_yield_quintals_per_acre=b_yield,
                baseline_market_price_per_quintal=b_price,
                baseline_cultivation_cost=b_cost,
                price_change_percent=Decimal(str(arguments.get("price_change_percent", 0.0))),
                yield_change_percent=Decimal(str(arguments.get("yield_change_percent", 0.0))),
                cost_change_percent=Decimal(str(arguments.get("cost_change_percent", 0.0))),
                fertilizer_cost_change_percent=Decimal(str(arguments.get("fertilizer_cost_change_percent", 0.0))),
                labour_cost_change_percent=Decimal(str(arguments.get("labour_cost_change_percent", 0.0))),
                area_change_percent=Decimal(str(arguments.get("area_change_percent", 0.0))),
                rainfall_change_percent=Decimal(str(arguments.get("rainfall_change_percent", 0.0))),
            )
            res = SimulationService.run_simulation(req)
            return {
                "card_type": "simulation_card",
                "title": f"What-If Simulation: {req.crop_name}",
                "data": res.model_dump()
            }

        elif tool_name == "assess_farm_risk":
            crop = arguments.get("crop_name") or arguments.get("crop") or "Crop"
            req = RiskAssessmentRequest(
                crop_name=crop,
                crop_stage=arguments.get("crop_stage", "flowering"),
                location=arguments.get("location", ""),
                area_acres=float(arguments.get("area_acres", 1.0)),
            )
            res = RiskAssessmentService.assess_risk(req)
            return {
                "card_type": "risk_card",
                "title": f"Farm Risk Assessment: {req.crop_name}",
                "data": res.model_dump()
            }

        elif tool_name == "get_daily_briefing":
            state = await FarmStateEngine.get_current_state()
            timeframe = arguments.get("timeframe", "today")
            if timeframe == "week":
                briefing = DailyFarmBriefingService.generate_week_briefing(state)
                return {
                    "card_type": "weekly_briefing_card",
                    "title": f"Weekly Farm Briefing: {state.active_crop}",
                    "data": briefing.model_dump()
                }
            else:
                briefing = DailyFarmBriefingService.generate_today_briefing(state)
                return {
                    "card_type": "daily_briefing_card",
                    "title": f"Today's Farm Briefing: {state.active_crop}",
                    "data": briefing.model_dump()
                }

        elif tool_name == "get_farm_changes":
            state = await FarmStateEngine.get_current_state()
            report = FarmChangeDetectionService.detect_changes(state)
            return {
                "card_type": "farm_changes_card",
                "title": "Farm Updates & Environmental Changes",
                "data": report.model_dump()
            }

        elif tool_name == "plan_season_crops":
            acres = float(arguments.get("area_acres", 3.0))
            season = arguments.get("season", "Kharif")
            plan = PersonalCropPlanner.plan_season(area_acres=acres, season=season)
            return {
                "card_type": "crop_planner_card",
                "title": f"Personal Crop Plan ({season})",
                "data": plan.model_dump()
            }

        elif tool_name == "record_farmer_decision":
            decision = arguments.get("decision", "grow soybean")
            crop = arguments.get("crop_name", "Soybean")
            FarmMemoryV2.add_memory(
                farmer_id="farmer_demo_1",
                category="DECISION",
                key="season_crop_decision",
                value=decision,
                source="farmer_explicit_statement"
            )
            plan = FarmPlanManager.create_or_update_plan(
                farmer_id="farmer_demo_1",
                farm_id="farm_1",
                crop_name=crop,
                area_acres=3.0
            )
            return {
                "card_type": "decision_recorded_card",
                "title": "Farmer Decision Confirmed",
                "data": {
                    "decision": decision,
                    "crop_name": crop,
                    "plan_id": plan.plan_id,
                    "status": "Farm Plan and Dynamic Tasks Initialized"
                }
            }
        elif tool_name == "diagnose_plant_disease":
            from app.services.vision.vision_service import VisionService
            crop = arguments.get("crop_name", "tomato")
            image_path = arguments.get("image_path")
            image_bytes = b""
            if image_path and os.path.exists(image_path):
                with open(image_path, "rb") as f:
                    image_bytes = f.read()
            analysis = await VisionService.analyze_leaf_image(image_bytes, crop_hint=crop)
            return {
                "card_type": "leaf_diagnosis_card",
                "title": f"Foliar Diagnosis: {analysis.crop_identified} ({analysis.common_name})",
                "data": analysis.model_dump()
            }

        else:
            return {"card_type": "generic_card", "data": arguments}
