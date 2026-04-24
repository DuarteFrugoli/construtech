import math
import logging
from typing import List, Optional, Tuple
from core.models import Room, HouseSpecs, Door

logger = logging.getLogger(__name__)

class RuleBasedLayoutGenerator:
    def __init__(self):
        pass

    _ROOM_AREA_RANGES = {
        "Living Room": (18.0, 28.0),
        "Kitchen": (8.0, 14.0),
        "Bedroom": (9.0, 14.0),
        "Master Bedroom": (14.0, 20.0),
        "Bathroom": (3.2, 5.5),
        "Dining Room": (10.0, 16.0),
        "Garage": (15.0, 20.0),
        "Home Office": (7.0, 10.0),
        "Dependência": (6.0, 9.0),
        "Varanda": (6.0, 12.0),
        "Lavabo": (1.8, 3.0),
        "Área Gourmet": (12.0, 18.0),
        "Área de Serviço": (4.0, 7.0),
    }

    _ROOM_ASPECT_RANGES = {
        "Living Room": (1.1, 1.6),
        "Kitchen": (1.1, 1.5),
        "Bedroom": (1.1, 1.4),
        "Master Bedroom": (1.1, 1.4),
        "Bathroom": (1.4, 2.2),
        "Dining Room": (1.1, 1.6),
        "Garage": (1.6, 2.0),
        "Home Office": (1.1, 1.4),
        "Dependência": (1.1, 1.5),
        "Varanda": (2.0, 3.0),
        "Lavabo": (1.4, 2.0),
        "Área Gourmet": (1.2, 1.8),
        "Área de Serviço": (1.4, 2.2),
    }

    # ── Zone classification ───────────────────────────────────────────────────
    # Zones (fine-grained): social, circulation, bathroom, bedroom, private, service
    _SOCIAL_KEYWORDS   = {"living", "kitchen", "dining", "gourmet", "varanda", "lavabo"}
    _SERVICE_KEYWORDS  = {"garage", "garagem", "serviço", "servico", "área de serviço", "area de servico"}

    # Compatibility matrix — default for unknown pairs is 0.
    # Hard-incompatible pairs (bedroom↔social, bedroom↔bedroom) get large negatives
    # so find_best_position skips them unless no other valid spot exists.
    _ZONE_COMPATIBILITY = {
        # same-zone
        ("social",      "social"):       3,
        ("bathroom",    "bathroom"):      1,
        ("bedroom",     "bedroom"):       0,  # shared wall is fine; doors are blocked by the door-logic below
        ("service",     "service"):       2,
        # corridor transitions
        ("circulation", "social"):        4,
        ("social",      "circulation"):   4,
        ("circulation", "bedroom"):       6,
        ("bedroom",     "circulation"):   6,
        ("circulation", "bathroom"):      3,
        ("bathroom",    "circulation"):   3,
        ("circulation", "private"):       2,
        ("private",     "circulation"):   2,
        ("circulation", "service"):       1,
        ("service",     "circulation"):   1,
        # bedroom neighbours
        ("bedroom",     "bathroom"):      4,  # quarto ao lado de banheiro = ótimo
        ("bathroom",    "bedroom"):       4,
        ("bedroom",     "private"):       1,
        ("private",     "bedroom"):       1,
        # cross-zone penalties
        ("bedroom",     "social"):      -12,  # NUNCA quarto↔sala/cozinha
        ("social",      "bedroom"):     -12,
        ("bathroom",    "social"):       -5,
        ("social",      "bathroom"):     -5,
        ("social",      "service"):      -4,
        ("service",     "social"):       -4,
        ("bedroom",     "service"):      -6,
        ("service",     "bedroom"):      -6,
        ("private",     "service"):      -2,
        ("service",     "private"):      -2,
    }
    # Threshold below which a position is considered architecturally unacceptable.
    # The algorithm will still use it as last resort if nothing better exists.
    _INCOMPATIBLE_THRESHOLD = -4

    _ZONE_ORDER = {"social": 0, "circulation": 1, "bedroom": 2, "bathroom": 3, "private": 4, "service": 5}

    def _get_zone(self, room_name: str) -> str:
        """Classify a room into a fine-grained functional zone."""
        name = room_name.lower()
        if any(k in name for k in ("corredor", "hall", "corridor")):
            return "circulation"
        if name == "lavabo":
            return "social"
        if "bathroom" in name or name == "lavabo":
            return "bathroom"
        if "bedroom" in name:
            return "bedroom"
        if any(k in name for k in self._SOCIAL_KEYWORDS):
            return "social"
        if any(k in name for k in ("home office", "dependência", "dependencia")):
            return "private"
        if any(k in name for k in self._SERVICE_KEYWORDS):
            return "service"
        return "social"

    def _suite_bathroom_name(self, suite_index: int) -> str:
        return f"Suite Bathroom {suite_index + 1}"

    def _is_suite_bathroom(self, room_name: str) -> bool:
        return room_name.startswith("Suite Bathroom ")

    def _is_social_bathroom(self, room_name: str) -> bool:
        return self._get_zone(room_name) == "bathroom" and not self._is_suite_bathroom(room_name)

    def _suite_index(self, room_name: str) -> Optional[int]:
        if room_name == "Master Bedroom":
            return 0
        if room_name == "Bedroom":
            return 0
        if room_name.startswith("Bedroom "):
            return int(room_name.split(" ")[-1]) - 1
        if room_name.startswith("Suite Bathroom "):
            return int(room_name.split(" ")[-1]) - 1
        return None

    def _build_private_sequence(
        self,
        bedrooms: List[Room],
        suite_bathrooms: List[Room],
        social_bathrooms: List[Room],
        private: List[Room],
    ) -> List[Room]:
        sequence: List[Room] = []
        for bedroom in bedrooms:
            sequence.append(bedroom)
        sequence.extend(social_bathrooms)
        sequence.extend(private)
        return sequence

    def _interpolate(self, value_range: Tuple[float, float], bias: float) -> float:
        low, high = value_range
        return low + (high - low) * bias

    def _size_bias(self, specs: HouseSpecs) -> float:
        """Convert built area allowance into a 0..1 sizing bias.

        The lot allowance is only an upper envelope; it should not force the
        room program to balloon unrealistically.
        """
        return max(0.0, min(1.0, (specs.built_area - 90.0) / 180.0))

    def _dimensions_from_area(self, area: float, aspect_ratio: float) -> Tuple[float, float]:
        short_side = math.sqrt(area / aspect_ratio)
        long_side = area / short_side
        return short_side, long_side

    def _room_dimensions(self, room_name: str, specs: HouseSpecs) -> Tuple[float, float]:
        area_range = self._ROOM_AREA_RANGES.get(room_name, (8.0, 12.0))
        ratio_range = self._ROOM_ASPECT_RANGES.get(room_name, (1.1, 1.5))
        area = self._interpolate(area_range, self._size_bias(specs))
        aspect_ratio = self._interpolate(ratio_range, 0.5)
        return self._dimensions_from_area(area, aspect_ratio)

    def generate_layout(self, specs: HouseSpecs) -> List[Room]:
        """Generate a rule-based room layout"""
        rooms = []

        def add_room(room_name: str, size_name: str | None = None):
            width, height = self._room_dimensions(size_name or room_name, specs)
            rooms.append(Room(room_name, width, height, 0, 0))

        terrain_ratio = specs.terrain_width / specs.terrain_height
        
        if terrain_ratio > 1.5:
            house_width = specs.terrain_width * 0.8
            house_height = specs.built_area / house_width
        elif terrain_ratio < 0.67:
            house_height = specs.terrain_height * 0.8
            house_width = specs.built_area / house_height
        else:
            house_width = math.sqrt(specs.built_area) * 0.9
            house_height = specs.built_area / house_width

        logger.debug(f"Initial house dimensions: {house_width:.0f} x {house_height:.0f}")

        if specs.has_living_room:
            add_room("Living Room")

        if specs.has_kitchen:
            add_room("Kitchen")

        for i in range(specs.num_bedrooms):
            if i == 0 and specs.num_bedrooms > 1:
                name = "Master Bedroom"
                size_name = "Master Bedroom"
            else:
                name = f"Bedroom {i+1}" if specs.num_bedrooms > 1 else "Bedroom"
                size_name = "Bedroom"
            add_room(name, size_name)
        
        # Add social/shared bathrooms
        for i in range(specs.num_social_bathrooms):
            name = f"Bathroom {i+1}" if specs.num_social_bathrooms > 1 else "Bathroom"
            add_room(name, "Bathroom")

        # Add suite bathrooms attached to the first N bedrooms.
        for i in range(specs.num_suites):
            add_room(self._suite_bathroom_name(i), "Bathroom")
        
        if specs.has_dining_room:
            add_room("Dining Room")
        
        if specs.has_garage:
            add_room("Garage")

        if specs.has_home_office:
            add_room("Home Office")

        if specs.has_dependencia:
            add_room("Dependência")

        if specs.has_varanda:
            add_room("Varanda")

        if specs.has_lavabo:
            add_room("Lavabo")

        if specs.has_area_gourmet:
            add_room("Área Gourmet")

        if specs.has_area_servico:
            add_room("Área de Serviço")
        
        # Treat built_area as an upper envelope, not a mandatory fill target.
        # We still upscale moderately so the footprint does not look undersized on larger lots.
        total_room_area = sum(room.area for room in rooms)
        corridor_area = 0.0
        room_area_budget = max(specs.built_area - corridor_area, 0.0)
        if total_room_area > 0:
            if total_room_area > room_area_budget > 0:
                target_area = room_area_budget
            else:
                target_area = min(
                    room_area_budget or total_room_area,
                    max(total_room_area * 1.35, (room_area_budget or total_room_area) * 0.45),
                )
            scale_factor = math.sqrt(target_area / total_room_area) if target_area > 0 else 1.0
            for room in rooms:
                room.width *= scale_factor
                room.height *= scale_factor

        logger.debug(
            f"Final area: {sum(r.area for r in rooms):.0f} m² "
            f"({(sum(r.area for r in rooms)/specs.total_area)*100:.1f}% of terrain)"
        )

        # Add corridor after scaling using the frontage actually needed by the rooms
        # that should open onto it, rather than stretching it across the full strip.
        if specs.num_bedrooms >= 2:
            corridor_width = 1.2
            corridor_frontage_rooms = [
                room for room in rooms
                if self._get_zone(room.name) in {"bedroom", "private"}
            ]
            social_bathrooms = [room for room in rooms if self._is_social_bathroom(room.name)]
            corridor_frontage_rooms.extend(social_bathrooms)
            frontage_dimension = (
                sum(room.width for room in corridor_frontage_rooms)
                if specs.terrain_height >= specs.terrain_width
                else sum(room.height for room in corridor_frontage_rooms)
            )
            corridor_length = max(4.8, frontage_dimension)
            rooms.append(Room("Corredor", corridor_width, corridor_length, 0, 0))

        return self._position_rooms(rooms, specs)

    def _position_rooms(self, rooms: List[Room], specs: HouseSpecs) -> List[Room]:
        """Zone-partitioned layout guaranteeing correct adjacencies by construction.

        Portrait terrain (height ≥ width) → horizontal strips front-to-back:
            [social rooms]  [corridor band 1.2m]  [bedrooms / bathrooms]  [service]

        Landscape terrain (width > height) → vertical columns left-to-right:
            [social]  [corridor strip 1.2m]  [bedrooms / bathrooms]  [service]
        """
        if not rooms:
            return rooms

        EPS = 1e-6

        # ── Zone buckets ──────────────────────────────────────────────────────
        def bucket(zone_name):
            return sorted([r for r in rooms if self._get_zone(r.name) == zone_name],
                          key=lambda r: -r.area)

        social    = bucket('social')
        corridor  = [r for r in rooms if self._get_zone(r.name) == 'circulation']
        bedrooms  = bucket('bedroom')
        bathrooms = bucket('bathroom')
        private   = bucket('private')
        service   = bucket('service')
        suite_bathrooms = [room for room in bathrooms if self._is_suite_bathroom(room.name)]
        social_bathrooms = [room for room in bathrooms if self._is_social_bathroom(room.name)]

        # ── Terrain usable bounds ─────────────────────────────────────────────
        is_portrait = specs.terrain_height >= specs.terrain_width
        if is_portrait:
            x0, y0 = specs.recuo_lateral, specs.recuo_frontal
            xmax   = specs.terrain_width  - specs.recuo_lateral
            ymax   = specs.terrain_height - specs.recuo_fundo
        else:
            x0, y0 = specs.recuo_frontal, specs.recuo_lateral
            xmax   = specs.terrain_width  - specs.recuo_fundo
            ymax   = specs.terrain_height - specs.recuo_lateral
        W = xmax - x0
        H = ymax - y0

        placed: List[Room] = []

        # ── Row-strip packer (left→right, wrapping) ───────────────────────────
        def pack_rows(room_list, sx, sy, sw, sh):
            """Place rooms in left-to-right rows within a strip.
            Returns the y coordinate of the bottom edge of the last row."""
            cx, cy, row_h = sx, sy, 0.0
            for r in room_list:
                # Rotate if the room is wider than the strip
                if r.width > sw + EPS and r.height <= sw + EPS:
                    r.width, r.height = r.height, r.width
                # Scale down if still too wide
                if r.width > sw:
                    r.height = r.height * sw / r.width
                    r.width  = sw
                # Wrap to new row if no horizontal space left
                if cx + r.width > sx + sw + EPS:
                    cy += row_h
                    cx, row_h = sx, 0.0
                # Skip if no vertical space left (report but don't abort)
                if cy + r.height > sy + sh + EPS:
                    avail = sy + sh - cy
                    if avail > 0.5:
                        scale_factor = avail / r.height
                        r.width *= scale_factor
                        r.height = avail
                    else:
                        logger.warning(f"Room '{r.name}' cannot fit in strip — skipping.")
                        continue
                r.x = cx
                r.y = cy
                placed.append(r)
                row_h = max(row_h, r.height)
                cx += r.width
            return cy + row_h

        # ── Column-strip packer (top→bottom, wrapping) ────────────────────────
        def pack_cols(room_list, sx, sy, sw, sh):
            """Place rooms in top-to-bottom columns within a strip.
            Returns the x coordinate of the right edge of the last column."""
            cx, cy, col_w = sx, sy, 0.0
            for r in room_list:
                # Rotate if taller than the strip height
                if r.height > sh + EPS and r.width <= sh + EPS:
                    r.width, r.height = r.height, r.width
                if r.height > sh:
                    r.width  = r.width * sh / r.height
                    r.height = sh
                # Wrap to new column if no vertical space left
                if cy + r.height > sy + sh + EPS:
                    cx += col_w
                    cy, col_w = sy, 0.0
                if cx + r.width > sx + sw + EPS:
                    remaining_w = sx + sw - cx
                    if remaining_w > 0.5:
                        scale_factor = remaining_w / r.width
                        r.width = remaining_w
                        r.height *= scale_factor
                    else:
                        logger.warning(f"Room '{r.name}' cannot fit in strip — skipping.")
                        continue
                r.x = cx
                r.y = cy
                placed.append(r)
                col_w = max(col_w, r.width)
                cy += r.height
            return cx + col_w

        # ── Place a corridor room as a thin band ──────────────────────────────
        def place_corridor_band(c, bx, by, bw, bh):
            """Orient corridor as a band: width=strip_span, height=1.2m (corridor width)."""
            band_thick = min(c.width, c.height)   # 1.2 m (the narrow dimension)
            band_length = min(max(c.width, c.height), bw)
            c.x = bx
            c.y = by
            c.width  = band_length
            c.height = min(band_thick, bh)
            placed.append(c)
            return by + c.height

        def place_corridor_strip(c, bx, by, bw, bh):
            """Orient corridor as a vertical strip: height=strip_span, width=1.2m."""
            strip_thick = min(c.width, c.height)
            strip_length = min(max(c.width, c.height), bh)
            c.x = bx
            c.y = by
            c.width  = min(strip_thick, bw)
            c.height = strip_length
            placed.append(c)
            return bx + c.width

        def overlaps_existing(room, x, y):
            for other in placed:
                if not (
                    x + room.width <= other.x + EPS or
                    x >= other.x + other.width - EPS or
                    y + room.height <= other.y + EPS or
                    y >= other.y + other.height - EPS
                ):
                    return True
            return False

        def place_suite_bathroom(room, bedroom, zone_x, zone_y, zone_w, zone_h, portrait):
            if portrait:
                candidates = [
                    (bedroom.x, bedroom.y + bedroom.height),
                    (bedroom.x + bedroom.width - room.width, bedroom.y + bedroom.height),
                    (bedroom.x + bedroom.width, bedroom.y),
                    (bedroom.x - room.width, bedroom.y),
                ]
            else:
                candidates = [
                    (bedroom.x + bedroom.width, bedroom.y),
                    (bedroom.x + bedroom.width, bedroom.y + bedroom.height - room.height),
                    (bedroom.x, bedroom.y + bedroom.height),
                    (bedroom.x, bedroom.y - room.height),
                ]

            for x, y in candidates:
                if x < zone_x - EPS or y < zone_y - EPS:
                    continue
                if x + room.width > zone_x + zone_w + EPS or y + room.height > zone_y + zone_h + EPS:
                    continue
                if overlaps_existing(room, x, y):
                    continue
                room.x = x
                room.y = y
                placed.append(room)
                return True

            logger.warning(f"Could not place suite bathroom '{room.name}' adjacent to '{bedroom.name}'.")
            return False

        # ── Main layout ───────────────────────────────────────────────────────
        private_all = self._build_private_sequence(bedrooms, suite_bathrooms, social_bathrooms, private)
        strip_span = W if is_portrait else H
        if corridor:
            corridor_length = max(corridor[0].width, corridor[0].height)
            social_min_span = max(
                (room.width if is_portrait else room.height) for room in social
            ) if social else 0.0
            strip_span = min(strip_span, max(corridor_length, social_min_span))

        if is_portrait:
            # Social zone → corridor band → private zone → service
            social_end = pack_rows(social, x0, y0, strip_span, H)

            if corridor:
                corr_end = place_corridor_band(corridor[0], x0, social_end, strip_span, ymax - social_end)
            else:
                corr_end = social_end

            priv_h = ymax - corr_end
            private_zone = (x0, corr_end, strip_span, priv_h)
            if private_all and priv_h > 0.5:
                priv_end = pack_rows(private_all, x0, corr_end, strip_span, priv_h)
            else:
                priv_end = corr_end

            svc_h = ymax - priv_end
            if service and svc_h > 0.5:
                pack_rows(service, x0, priv_end, strip_span, svc_h)

        else:
            # Social zone → corridor strip → private zone → service
            social_end = pack_cols(social, x0, y0, W, strip_span)

            if corridor:
                corr_end = place_corridor_strip(corridor[0], social_end, y0, xmax - social_end, strip_span)
            else:
                corr_end = social_end

            priv_w = xmax - corr_end
            private_zone = (corr_end, y0, priv_w, strip_span)
            if private_all and priv_w > 0.5:
                priv_end = pack_cols(private_all, corr_end, y0, priv_w, strip_span)
            else:
                priv_end = corr_end

            svc_w = xmax - priv_end
            if service and svc_w > 0.5:
                pack_cols(service, priv_end, y0, svc_w, strip_span)

        if suite_bathrooms:
            suite_bedrooms = {
                self._suite_index(room.name): room
                for room in bedrooms
                if self._suite_index(room.name) is not None
            }
            zone_x, zone_y, zone_w, zone_h = private_zone
            for suite_bathroom in suite_bathrooms:
                suite_index = self._suite_index(suite_bathroom.name)
                bedroom = suite_bedrooms.get(suite_index)
                if bedroom is None:
                    logger.warning(f"Could not find matching suite bedroom for '{suite_bathroom.name}'.")
                    continue
                place_suite_bathroom(suite_bathroom, bedroom, zone_x, zone_y, zone_w, zone_h, is_portrait)

        # ── Add doors between adjacent compatible rooms ────────────────────────
        door_size = min(W, H) * 0.08

        def bedroom_has_suite(room):
            suite_index = self._suite_index(room.name)
            return suite_index is not None and suite_index < specs.num_suites

        def door_limit(room):
            if self._is_suite_bathroom(room.name) or self._is_social_bathroom(room.name):
                return 1
            zone = self._get_zone(room.name)
            if zone == "bedroom":
                return 2 if bedroom_has_suite(room) else 1
            if zone in {"private", "service"}:
                return 1
            return None

        def should_add_door(room1, room2):
            zone1 = self._get_zone(room1.name)
            zone2 = self._get_zone(room2.name)

            if self._ZONE_COMPATIBILITY.get((zone1, zone2), 0) < 0:
                return False

            limit1 = door_limit(room1)
            if limit1 is not None and len(room1.doors) >= limit1:
                return False
            limit2 = door_limit(room2)
            if limit2 is not None and len(room2.doors) >= limit2:
                return False

            if self._is_suite_bathroom(room1.name) or self._is_suite_bathroom(room2.name):
                return (
                    zone1 == "bedroom"
                    and self._is_suite_bathroom(room2.name)
                    and self._suite_index(room1.name) == self._suite_index(room2.name)
                ) or (
                    zone2 == "bedroom"
                    and self._is_suite_bathroom(room1.name)
                    and self._suite_index(room1.name) == self._suite_index(room2.name)
                )

            if self._is_social_bathroom(room1.name) or self._is_social_bathroom(room2.name):
                if corridor:
                    return "circulation" in {zone1, zone2}
                return "social" in {zone1, zone2}

            if zone1 == "bedroom" and zone2 == "bedroom":
                return False

            if "circulation" in {zone1, zone2}:
                return True

            if zone1 == "social" and zone2 == "social":
                return True

            if not corridor and {zone1, zone2} in ({"social", "bedroom"}, {"social", "bathroom"}, {"social", "private"}, {"social", "service"}):
                return True

            return False

        for i, r1 in enumerate(placed):
            for r2 in placed[i + 1:]:
                if not should_add_door(r1, r2):
                    continue
                # Right of r1 == Left of r2
                if abs(r1.x + r1.width - r2.x) < EPS:
                    shared = max(0.0, min(r1.y + r1.height, r2.y + r2.height) - max(r1.y, r2.y))
                    if shared > door_size:
                        dy = max(r1.y, r2.y) + shared / 2
                        d  = Door(x=r1.x + r1.width, y=dy,
                                  width=door_size, height=door_size, is_horizontal=False)
                        r1.doors.append(d); r2.doors.append(d)
                # Bottom of r1 == Top of r2
                elif abs(r1.y + r1.height - r2.y) < EPS:
                    shared = max(0.0, min(r1.x + r1.width, r2.x + r2.width) - max(r1.x, r2.x))
                    if shared > door_size:
                        dx = max(r1.x, r2.x) + shared / 2
                        d  = Door(x=dx, y=r1.y + r1.height,
                                  width=door_size, height=door_size, is_horizontal=True)
                        r1.doors.append(d); r2.doors.append(d)

        return placed
