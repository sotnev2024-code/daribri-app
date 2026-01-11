"""
API Routes для геокодирования и автодополнения адресов.
"""

from fastapi import APIRouter, Query, HTTPException
from typing import List, Optional
import httpx
from ..config import settings

router = APIRouter()


@router.get("/autocomplete")
async def autocomplete_address(
    query: str = Query(..., description="Текст запроса для автодополнения"),
    city: str = Query(..., description="Город для ограничения поиска"),
    limit: int = Query(5, ge=1, le=10, description="Максимальное количество результатов")
):
    """
    Автодополнение адресов через Yandex Geocoder API.
    
    Использует серверный прокси для обхода проблем с CORS.
    """
    try:
        # Очищаем запрос от дублирования города
        query_clean = query.strip()
        query_lower = query_clean.lower()
        city_lower = city.lower()
        
        # Удаляем город из запроса, если он уже есть
        if city_lower in query_lower:
            query_clean = query_clean.replace(city_lower, "", 1).strip()
            query_clean = query_clean.lstrip(",").strip()
        
        # Формируем полный запрос для API
        if query_clean:
            full_query = f"{city}, {query_clean}"
        else:
            full_query = city
        
        # Запрос к Yandex Geocoder API
        import urllib.parse
        encoded_query = urllib.parse.quote(full_query)
        api_key_param = f"&apikey={settings.YANDEX_API_KEY}" if settings.YANDEX_API_KEY else ""
        url = f"https://geocode-maps.yandex.ru/1.x/?geocode={encoded_query}&format=json&results={limit}&kind=house{api_key_param}"
        
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(url)
            
            if response.status_code != 200:
                # Если Geocoder API не работает, пробуем Suggest API
                suggest_url = f"https://suggest-maps.yandex.ru/v1/suggest?text={encoded_query}&lang=ru_RU&results={limit}"
                suggest_response = await client.get(suggest_url)
                
                if suggest_response.status_code == 200:
                    suggest_data = suggest_response.json()
                    results = suggest_data.get("results", [])
                    
                    # Варианты написания городов для более гибкой проверки
                    city_aliases = {
                        'санкт-петербург': ['санкт-петербург', 'спб', 'с.-петербург', 'с-петербург', 'петербург', 'питер', 'ленинград'],
                        'москва': ['москва', 'мск', 'moscow'],
                        'казань': ['казань', 'kazan'],
                        'новосибирск': ['новосибирск'],
                        'екатеринбург': ['екатеринбург', 'свердловск', 'ekaterinburg'],
                        'нижний новгород': ['нижний новгород', 'н.новгород', 'н. новгород', 'нижний'],
                        'краснодар': ['краснодар'],
                        'сочи': ['сочи'],
                        'ростов-на-дону': ['ростов-на-дону', 'ростов на дону', 'ростов'],
                    }
                    
                    # Находим все допустимые варианты для текущего города
                    allowed_variants = [city_lower]
                    for main_city, aliases in city_aliases.items():
                        if city_lower == main_city or city_lower in aliases or main_city in city_lower or any(alias in city_lower for alias in aliases):
                            allowed_variants.extend([main_city] + aliases)
                            break
                    
                    # Фильтруем результаты по городу (с учетом вариантов написания)
                    filtered_results = []
                    for item in results:
                        title = item.get("title", {}).get("text", "")
                        subtitle = item.get("subtitle", {}).get("text", "")
                        address = f"{title}, {subtitle}".strip(", ")
                        
                        # Проверяем, что адрес в нужном городе
                        address_lower = address.lower()
                        if any(variant in address_lower for variant in allowed_variants):
                            filtered_results.append({
                                "text": address,
                                "title": title,
                                "description": subtitle
                            })
                    
                    return {"suggestions": filtered_results[:limit]}
                
                return {"suggestions": []}
            
            data = response.json()
            feature_members = data.get("response", {}).get("GeoObjectCollection", {}).get("featureMember", [])
            
            # Варианты написания городов для более гибкой проверки
            city_aliases = {
                'санкт-петербург': ['санкт-петербург', 'спб', 'с.-петербург', 'с-петербург', 'петербург', 'питер', 'ленинград'],
                'москва': ['москва', 'мск', 'moscow'],
                'казань': ['казань', 'kazan'],
                'новосибирск': ['новосибирск'],
                'екатеринбург': ['екатеринбург', 'свердловск', 'ekaterinburg'],
                'нижний новгород': ['нижний новгород', 'н.новгород', 'н. новгород', 'нижний'],
                'краснодар': ['краснодар'],
                'сочи': ['сочи'],
                'ростов-на-дону': ['ростов-на-дону', 'ростов на дону', 'ростов'],
            }
            
            # Находим все допустимые варианты для текущего города
            allowed_variants = [city_lower]
            for main_city, aliases in city_aliases.items():
                if city_lower == main_city or city_lower in aliases or main_city in city_lower or any(alias in city_lower for alias in aliases):
                    allowed_variants.extend([main_city] + aliases)
                    break
            
            suggestions = []
            for fm in feature_members:
                geo_object = fm.get("GeoObject", {})
                meta_data = geo_object.get("metaDataProperty", {}).get("GeocoderMetaData", {})
                address_text = meta_data.get("text", "")
                description = geo_object.get("description", "")
                
                # Проверяем, что адрес в нужном городе (с учетом вариантов написания)
                address_lower = address_text.lower()
                if any(variant in address_lower for variant in allowed_variants):
                    suggestions.append({
                        "text": address_text,
                        "title": address_text,
                        "description": description
                    })
            
            return {"suggestions": suggestions[:limit]}
            
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Timeout while fetching address suggestions")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching address suggestions: {str(e)}")


@router.get("/reverse")
async def reverse_geocode(
    lat: float = Query(..., description="Широта"),
    lng: float = Query(..., description="Долгота"),
    city: Optional[str] = Query(None, description="Город для проверки адреса")
):
    """
    Обратное геокодирование: получение адреса по координатам через Yandex Geocoder API.
    """
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        logger.info(f"[GEOCODE] Reverse geocoding request: lat={lat}, lng={lng}, city={city}")
        
        # ВАЖНО: Yandex Geocoder API ожидает формат: долгота, широта (lng,lat)
        # Frontend передает: lat (широта), lng (долгота) - стандартный порядок
        # Для Yandex API нужно передать в порядке: lng,lat
        
        api_key_param = f"&apikey={settings.YANDEX_API_KEY}" if settings.YANDEX_API_KEY else ""
        # Yandex Geocoder API ожидает: долгота, широта (lng,lat)
        url = f"https://geocode-maps.yandex.ru/1.x/?geocode={lng},{lat}&format=json&results=1{api_key_param}"
        
        logger.info(f"[GEOCODE] Requesting Yandex API: {url.replace(settings.YANDEX_API_KEY, 'API_KEY_HIDDEN') if settings.YANDEX_API_KEY else url}")
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url)
            
            logger.info(f"[GEOCODE] Yandex API response status: {response.status_code}")
            
            if response.status_code != 200:
                error_text = response.text[:200] if response.text else "No error details"
                logger.error(f"[GEOCODE] Yandex API error: {response.status_code}, {error_text}")
                return {
                    "address": None,
                    "error": f"Unable to get address from coordinates (status: {response.status_code})",
                    "is_valid": False
                }
            
            data = response.json()
            
            # Проверяем структуру ответа
            response_obj = data.get("response", {})
            if not response_obj:
                logger.warn("[GEOCODE] No 'response' in Yandex API answer")
                return {
                    "address": None,
                    "error": "Invalid response from geocoding service",
                    "is_valid": False
                }
            
            geo_collection = response_obj.get("GeoObjectCollection", {})
            feature_members = geo_collection.get("featureMember", [])
            
            if not feature_members:
                logger.warn(f"[GEOCODE] No featureMember found for coordinates: {lng},{lat}")
                return {
                    "address": None,
                    "error": "No address found for coordinates",
                    "is_valid": False
                }
            
            geo_object = feature_members[0].get("GeoObject", {})
            if not geo_object:
                logger.warn("[GEOCODE] No GeoObject in featureMember")
                return {
                    "address": None,
                    "error": "Invalid geocoding response structure",
                    "is_valid": False
                }
            
            # Проверяем координаты из ответа Yandex
            point = geo_object.get("Point", {})
            if point:
                pos_str = point.get("pos", "")
                if pos_str:
                    pos_parts = pos_str.split()
                    if len(pos_parts) == 2:
                        response_lng = float(pos_parts[0])
                        response_lat = float(pos_parts[1])
                        logger.info(f"[GEOCODE] Yandex returned coordinates: lng={response_lng}, lat={response_lat} (requested: lng={lng}, lat={lat})")
            
            meta_data = geo_object.get("metaDataProperty", {}).get("GeocoderMetaData", {})
            address_text = meta_data.get("text", "")
            
            if not address_text:
                logger.warn("[GEOCODE] No address text in response")
                return {
                    "address": None,
                    "error": "Empty address in response",
                    "is_valid": False
                }
            
            logger.info(f"[GEOCODE] Found address: {address_text}")
            
            # Проверяем, что адрес в нужном городе, если указан
            is_valid = True
            if city:
                address_lower = address_text.lower()
                city_lower = city.lower()
                
                # Варианты написания городов для более гибкой проверки
                city_aliases = {
                    'санкт-петербург': ['санкт-петербург', 'спб', 'с.-петербург', 'с-петербург', 'петербург', 'питер', 'ленинград'],
                    'москва': ['москва', 'мск', 'moscow'],
                    'казань': ['казань', 'kazan'],
                    'новосибирск': ['новосибирск'],
                    'екатеринбург': ['екатеринбург', 'свердловск', 'ekaterinburg'],
                    'нижний новгород': ['нижний новгород', 'н.новгород', 'н. новгород', 'нижний'],
                    'краснодар': ['краснодар'],
                    'сочи': ['сочи'],
                    'ростов-на-дону': ['ростов-на-дону', 'ростов на дону', 'ростов'],
                }
                
                # Находим все допустимые варианты для текущего города
                allowed_variants = [city_lower]
                for main_city, aliases in city_aliases.items():
                    if city_lower == main_city or city_lower in aliases or main_city in city_lower or any(alias in city_lower for alias in aliases):
                        allowed_variants.extend([main_city] + aliases)
                        break
                
                # Проверяем, содержит ли адрес хотя бы один вариант названия города
                is_valid = any(variant in address_lower for variant in allowed_variants)
                logger.info(f"[GEOCODE] Address validation: is_valid={is_valid}, city={city}, address={address_text}, allowed_variants={allowed_variants}")
            
            return {
                "address": address_text,
                "is_valid": is_valid,
                "coordinates": {
                    "lat": lat,
                    "lng": lng
                }
            }
            
    except httpx.TimeoutException as e:
        logger.error(f"[GEOCODE] Timeout while reverse geocoding: {e}")
        raise HTTPException(status_code=504, detail="Timeout while reverse geocoding")
    except Exception as e:
        logger.error(f"[GEOCODE] Error reverse geocoding: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error reverse geocoding: {str(e)}")


@router.get("/geocode")
async def geocode_address(
    address: str = Query(..., description="Адрес для получения координат"),
    city: Optional[str] = Query(None, description="Город для ограничения поиска")
):
    """
    Прямое геокодирование: получение координат по адресу через Yandex Geocoder API.
    """
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        logger.info(f"[GEOCODE] Geocoding request: address={address}, city={city}")
        
        # Формируем запрос: если указан город, добавляем его к адресу
        if city and city.lower() not in address.lower():
            full_address = f"{city}, {address}"
        else:
            full_address = address
        
        logger.info(f"[GEOCODE] Full address for geocoding: {full_address}")
        
        # Запрос к Yandex Geocoder API
        import urllib.parse
        encoded_address = urllib.parse.quote(full_address)
        api_key_param = f"&apikey={settings.YANDEX_API_KEY}" if settings.YANDEX_API_KEY else ""
        url = f"https://geocode-maps.yandex.ru/1.x/?geocode={encoded_address}&format=json&results=1{api_key_param}"
        
        logger.info(f"[GEOCODE] Requesting Yandex API: {url.replace(settings.YANDEX_API_KEY, 'API_KEY_HIDDEN') if settings.YANDEX_API_KEY else url}")
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url)
            
            logger.info(f"[GEOCODE] Yandex API response status: {response.status_code}")
            
            if response.status_code != 200:
                error_text = response.text[:200] if response.text else "No error details"
                logger.error(f"[GEOCODE] Yandex API error: {response.status_code}, {error_text}")
                return {
                    "coordinates": None,
                    "address": address,
                    "error": "Unable to get coordinates for address"
                }
            
            data = response.json()
            feature_members = data.get("response", {}).get("GeoObjectCollection", {}).get("featureMember", [])
            
            if not feature_members:
                logger.warn(f"[GEOCODE] No featureMember found for address: {full_address}")
                return {
                    "coordinates": None,
                    "address": address,
                    "error": "Address not found"
                }
            
            geo_object = feature_members[0].get("GeoObject", {})
            point = geo_object.get("Point", {})
            pos = point.get("pos", "").split()  # Формат: "долгота широта" согласно документации Yandex
            
            if len(pos) != 2:
                logger.warn(f"[GEOCODE] Invalid coordinates format in response: {pos}")
                return {
                    "coordinates": None,
                    "address": address,
                    "error": "Invalid coordinates format"
                }
            
            # Yandex Geocoder API возвращает координаты в формате "долгота широта" (пробел между ними)
            # То есть pos[0] = долгота, pos[1] = широта
            lng = float(pos[0])  # Долгота
            lat = float(pos[1])  # Широта
            
            logger.info(f"[GEOCODE] Extracted coordinates from Yandex: lng={lng}, lat={lat} (format: lng,lat)")
            
            # Получаем полный адрес из ответа
            meta_data = geo_object.get("metaDataProperty", {}).get("GeocoderMetaData", {})
            full_address_text = meta_data.get("text", address)
            
            logger.info(f"[GEOCODE] Full address from Yandex: {full_address_text}")
            
            # Проверяем, что адрес в нужном городе, если указан
            is_valid = True
            if city:
                address_lower = full_address_text.lower()
                city_lower = city.lower()
                
                # Варианты написания городов для более гибкой проверки
                city_aliases = {
                    'санкт-петербург': ['санкт-петербург', 'спб', 'с.-петербург', 'с-петербург', 'петербург', 'питер', 'ленинград'],
                    'москва': ['москва', 'мск', 'moscow'],
                    'казань': ['казань', 'kazan'],
                    'новосибирск': ['новосибирск'],
                    'екатеринбург': ['екатеринбург', 'свердловск', 'ekaterinburg'],
                    'нижний новгород': ['нижний новгород', 'н.новгород', 'н. новгород', 'нижний'],
                    'краснодар': ['краснодар'],
                    'сочи': ['сочи'],
                    'ростов-на-дону': ['ростов-на-дону', 'ростов на дону', 'ростов'],
                }
                
                # Находим все допустимые варианты для текущего города
                allowed_variants = [city_lower]
                for main_city, aliases in city_aliases.items():
                    if city_lower == main_city or city_lower in aliases or main_city in city_lower or any(alias in city_lower for alias in aliases):
                        allowed_variants.extend([main_city] + aliases)
                        break
                
                # Проверяем, содержит ли адрес хотя бы один вариант названия города
                is_valid = any(variant in address_lower for variant in allowed_variants)
                logger.info(f"[GEOCODE] Address validation: is_valid={is_valid}, city={city}, allowed_variants={allowed_variants}")
            
            return {
                "coordinates": {
                    "lat": lat,  # Широта
                    "lng": lng   # Долгота
                },
                "address": full_address_text,
                "is_valid": is_valid
            }
            
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Timeout while geocoding")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error geocoding: {str(e)}")

