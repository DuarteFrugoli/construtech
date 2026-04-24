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
        "Escritório": (7.0, 10.0),
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
        "Escritório": (1.1, 1.4),
        "Dependência": (1.1, 1.5),
        "Varanda": (2.0, 3.0),
        "Lavabo": (1.4, 2.0),
        "Área Gourmet": (1.2, 1.8),
        "Área de Serviço": (1.4, 2.2),
    }

    # ── Zone classification ───────────────────────────────────────────────────
    # Zones (fine-grained): social, circulation, bathroom, bedroom, private, service
    _SOCIAL_KEYWORDS   = {"living", "kitchen", "dining", "gourmet", "varanda", "lavabo"}
    _SERVICE_KEYWORDS  = {"serviço", "servico", "área de serviço", "area de servico"}

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
        # Named suites (e.g. "Suite 2") are bedroom zone
        if name.startswith("suite ") and "bathroom" not in name:
            return "bedroom"
        if any(k in name for k in self._SOCIAL_KEYWORDS):
            return "social"
        if any(k in name for k in ("escritório", "escritorio", "dependência", "dependencia")):
            return "private"
        if any(k in name for k in self._SERVICE_KEYWORDS):
            return "service"
        return "social"

    def _suite_bathroom_name(self, suite_index: int) -> str:
        return f"Suite Bathroom {suite_index + 1}"

    def _is_suite_bathroom(self, room_name: str) -> bool:
        return room_name == "Suite Bathroom" or room_name.startswith("Suite Bathroom ")

    def _is_social_bathroom(self, room_name: str) -> bool:
        return self._get_zone(room_name) == "bathroom" and not self._is_suite_bathroom(room_name)

    def _suite_index(self, room_name: str) -> Optional[int]:
        if room_name == "Master Bedroom":
            return 0
        if room_name == "Bedroom":
            return 0
        if room_name == "Suite Bathroom":
            return 0
        if room_name.startswith("Suite Bathroom "):
            return int(room_name.split(" ")[-1]) - 1
        # Named suite bedrooms (e.g. "Suite 2")
        if room_name.startswith("Suite "):
            return int(room_name.split(" ")[-1]) - 1
        if room_name.startswith("Bedroom "):
            return int(room_name.split(" ")[-1]) - 1
        return None

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

        if specs.has_living_room:
            add_room("Living Room")

        if specs.has_kitchen:
            add_room("Kitchen")

        for i in range(specs.num_bedrooms):
            if i == 0 and specs.num_bedrooms > 1:
                name = "Master Bedroom"
                size_name = "Master Bedroom"
            elif i > 0 and i < specs.num_suites:
                # Bedrooms with a suite bathroom get a suite name
                name = f"Suite {i + 1}"
                size_name = "Bedroom"
            else:
                name = f"Bedroom {i+1}" if specs.num_bedrooms > 1 else "Bedroom"
                size_name = "Bedroom"
            add_room(name, size_name)
        
        # Add social/shared bathrooms
        for i in range(specs.num_social_bathrooms):
            name = f"Bathroom {i+1}" if specs.num_social_bathrooms > 1 else "Bathroom"
            add_room(name, "Bathroom")

        # Add suite bathrooms attached to the first N bedrooms, in landscape orientation.
        for i in range(specs.num_suites):
            name = "Suite Bathroom" if specs.num_suites == 1 else self._suite_bathroom_name(i)
            w, h = self._room_dimensions("Bathroom", specs)
            rooms.append(Room(name, max(w, h), min(w, h), 0, 0))
        
        if specs.has_dining_room:
            add_room("Dining Room")
        
        if specs.has_garage:
            add_room("Garage")

        if specs.has_home_office:
            add_room("Escritório")

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
        
        # Scale only the "depth" dimension (height for portrait, width for landscape)
        # so the house fills ~88% of the usable terrain depth.
        # Widths are left untouched so social rooms continue to fit side-by-side.
        is_portrait_gs = specs.terrain_height >= specs.terrain_width
        if is_portrait_gs:
            depth_usable = specs.terrain_height - specs.recuo_frontal - specs.recuo_fundo
            nat_social_depth  = max((r.height for r in rooms if self._get_zone(r.name) == 'social'),  default=0.0)
            nat_private_depth = max((r.height for r in rooms if self._get_zone(r.name) == 'bedroom'), default=0.0)
        else:
            depth_usable = specs.terrain_width - specs.recuo_frontal - specs.recuo_fundo
            nat_social_depth  = max((r.width for r in rooms if self._get_zone(r.name) == 'social'),  default=0.0)
            nat_private_depth = max((r.width for r in rooms if self._get_zone(r.name) == 'bedroom'), default=0.0)

        nat_house_depth = nat_social_depth + 1.2 + nat_private_depth  # 1.2 m corridor
        if nat_house_depth > 0 and depth_usable > nat_house_depth:
            depth_scale = min(1.5, depth_usable * 0.88 / nat_house_depth)
            for room in rooms:
                if is_portrait_gs:
                    room.height *= depth_scale
                else:
                    room.width *= depth_scale

        # Enforce minimum dimensions so rooms remain architecturally valid
        # even on small terrains where the scale factor compressed everything.
        _MIN_DIM = {
            "Living Room":    (3.0, 3.5),
            "Kitchen":        (2.4, 2.8),
            "Master Bedroom": (3.0, 3.2),
            "Bedroom":        (2.5, 2.8),
            "Bathroom":       (1.5, 2.2),
            "Dining Room":    (2.5, 3.0),
            "Garage":         (2.8, 5.0),
        }
        for room in rooms:
            # Find the applicable min key (handles "Suite 2", "Bedroom 3", etc.)
            min_key = room.name
            if room.name not in _MIN_DIM:
                if "bedroom" in room.name.lower() or "suite" in room.name.lower() and "bathroom" not in room.name.lower():
                    min_key = "Master Bedroom" if "master" in room.name.lower() else "Bedroom"
                elif "bathroom" in room.name.lower():
                    min_key = "Bathroom"
            if min_key in _MIN_DIM:
                min_short, min_long = _MIN_DIM[min_key]
                short = min(room.width, room.height)
                long_ = max(room.width, room.height)
                was_portrait = room.height >= room.width
                short = max(short, min_short)
                long_ = max(long_, min_long)
                if was_portrait:
                    room.width, room.height = short, long_
                else:
                    room.width, room.height = long_, short

        logger.debug(
            f"Final area: {sum(r.area for r in rooms):.0f} m² "
            f"({(sum(r.area for r in rooms)/specs.total_area)*100:.1f}% of terrain)"
        )

        # Add corridor after scaling using the frontage actually needed by the rooms
        # that should open onto it, rather than stretching it across the full strip.
        # A corridor is needed whenever there are bedrooms AND a social bathroom
        # (regardless of bedroom count) so the social bathroom always has a valid exit.
        needs_corridor = specs.num_bedrooms >= 2 or (
            specs.num_bedrooms >= 1 and specs.num_social_bathrooms >= 1
        )
        if needs_corridor:
            corridor_width = 1.2
            corridor_frontage_rooms = [
                room for room in rooms
                if self._get_zone(room.name) in {"bedroom", "private"}
                or self._is_social_bathroom(room.name)
                or self._is_suite_bathroom(room.name)
            ]
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
            # Try positions adjacent to the bedroom in preference order.
            # Also try with the room rotated 90° so narrow terrains have more options.
            def candidates_for(r):
                if portrait:
                    return [
                        (bedroom.x + bedroom.width, bedroom.y),
                        (bedroom.x + bedroom.width, bedroom.y + bedroom.height - r.height),
                        (bedroom.x - r.width, bedroom.y),
                        (bedroom.x - r.width, bedroom.y + bedroom.height - r.height),
                        (bedroom.x, bedroom.y + bedroom.height),
                        (bedroom.x + bedroom.width - r.width, bedroom.y + bedroom.height),
                        (bedroom.x, bedroom.y - r.height),
                    ]
                else:
                    return [
                        (bedroom.x + bedroom.width, bedroom.y),
                        (bedroom.x + bedroom.width, bedroom.y + bedroom.height - r.height),
                        (bedroom.x, bedroom.y + bedroom.height),
                        (bedroom.x + bedroom.width - r.width, bedroom.y + bedroom.height),
                        (bedroom.x - r.width, bedroom.y),
                        (bedroom.x, bedroom.y - r.height),
                    ]

            for rotated in (False, True):
                if rotated:
                    room.width, room.height = room.height, room.width
                for x, y in candidates_for(room):
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
        # Bedrooms first, then other private rooms (e.g. home office).
        # Suite and social bathrooms are placed separately after pack_rows.
        private_all = bedrooms + private
        # strip_span is the full usable width (portrait) or height (landscape).
        # We no longer clip it to corridor_length so rooms spread across the terrain.
        strip_span = W if is_portrait else H

        if is_portrait:
            # Social zone → corridor band → private zone → service
            # Cap each social room's width so the social zone fills the strip in
            # two columns (living room beside kitchen) rather than one tall column.
            # Target: each room takes at most 60% of the strip width so the next
            # room wraps beside it rather than below it.
            # Safety cap: no single room should be wider than the strip.
            # With scale_factor ≤ 1.0 this rarely triggers, but keeps things
            # safe if, say, a living room is already larger than the strip.
            for r in social:
                if r.width > strip_span + EPS:
                    r.height *= r.width / strip_span
                    r.width = strip_span

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

        zone_x, zone_y, zone_w, zone_h = private_zone

        if suite_bathrooms:
            suite_bedrooms = {
                self._suite_index(room.name): room
                for room in bedrooms
                if self._suite_index(room.name) is not None
            }
            for suite_bathroom in suite_bathrooms:
                suite_index = self._suite_index(suite_bathroom.name)
                bedroom = suite_bedrooms.get(suite_index)
                if bedroom is None:
                    logger.warning(f"Could not find matching suite bedroom for '{suite_bathroom.name}'.")
                    continue
                place_suite_bathroom(suite_bathroom, bedroom, zone_x, zone_y, zone_w, zone_h, is_portrait)

        # Place social bathrooms AFTER suite bathrooms so they fill remaining space
        # and never block the suite bathroom from sitting next to its bedroom.
        if social_bathrooms:
            def place_social_bath(room):
                """Place social bathroom adjacent to corridor (preferred) or social zone.
                Never place it next to a suite bathroom — that's architecturally wrong."""
                for rotated in (False, True):
                    if rotated:
                        room.width, room.height = room.height, room.width

                    # Priority 1: adjacent to corridor
                    # Priority 2 (no corridor): adjacent to social zone rooms
                    # Priority 3 (last resort): adjacent to bedroom/private (but NEVER suite bathroom)
                    priority_groups = []

                    if corridor:
                        corr_candidates = []
                        for p in placed:
                            if self._get_zone(p.name) == "circulation":
                                corr_candidates += [
                                    (p.x + p.width, p.y),
                                    (p.x + p.width, p.y + p.height - room.height),
                                    (p.x - room.width, p.y),
                                    (p.x - room.width, p.y + p.height - room.height),
                                    (p.x, p.y - room.height),
                                    (p.x + p.width - room.width, p.y - room.height),
                                    (p.x, p.y + p.height),
                                    (p.x + p.width - room.width, p.y + p.height),
                                ]
                            # Also try right of private zone rooms to fill gaps next to corridor
                            elif self._get_zone(p.name) in {"bedroom", "private"} and not self._is_suite_bathroom(p.name):
                                corr_candidates += [
                                    (p.x + p.width, p.y),
                                    (p.x + p.width, p.y + p.height - room.height),
                                ]
                        priority_groups.append(corr_candidates)
                    else:
                        # No corridor: prefer adjacent to social zone
                        social_candidates = []
                        for p in placed:
                            if self._get_zone(p.name) == "social":
                                social_candidates += [
                                    (p.x + p.width, p.y),
                                    (p.x + p.width, p.y + p.height - room.height),
                                    (p.x - room.width, p.y),
                                    (p.x - room.width, p.y + p.height - room.height),
                                    (p.x, p.y - room.height),
                                    (p.x + p.width - room.width, p.y - room.height),
                                    (p.x, p.y + p.height),
                                    (p.x + p.width - room.width, p.y + p.height),
                                ]
                        priority_groups.append(social_candidates)
                        # Fallback: adjacent to bedroom/private, NOT suite bathroom
                        fallback_candidates = []
                        for p in placed:
                            p_zone = self._get_zone(p.name)
                            if p_zone in {"bedroom", "private"} and not self._is_suite_bathroom(p.name):
                                fallback_candidates += [
                                    (p.x + p.width, p.y),
                                    (p.x + p.width, p.y + p.height - room.height),
                                    (p.x, p.y + p.height),
                                    (p.x + p.width - room.width, p.y + p.height),
                                ]
                        priority_groups.append(fallback_candidates)

                    for candidates in priority_groups:
                        candidates.sort(key=lambda pt: (round(pt[1], 1), pt[0]))
                        for x, y in candidates:
                            # When no corridor the bathroom can sit in the social zone boundary too
                            min_y = y0 if not corridor else zone_y
                            if y < min_y - EPS or y + room.height > ymax + EPS:
                                continue
                            if x < x0 - EPS or x + room.width > xmax + EPS:
                                continue
                            if overlaps_existing(room, x, y):
                                continue
                            room.x, room.y = x, y
                            placed.append(room)
                            return True

                logger.warning(f"Could not place social bathroom '{room.name}' in private zone.")
                return False

            for sb in social_bathrooms:
                place_social_bath(sb)

        # ── Add doors between adjacent compatible rooms ────────────────────────
        door_size = min(W, H) * 0.08

        def bedroom_has_suite(room):
            suite_index = self._suite_index(room.name)
            return suite_index is not None and suite_index < specs.num_suites

        def door_limit(room):
            if self._is_suite_bathroom(room.name) or self._is_social_bathroom(room.name):
                return 1
            # Garage gets exactly one interior door
            if "garage" in room.name.lower() or "garagem" in room.name.lower():
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

            # Door-limit check first (applies to all room types)
            limit1 = door_limit(room1)
            if limit1 is not None and len(room1.doors) >= limit1:
                return False
            limit2 = door_limit(room2)
            if limit2 is not None and len(room2.doors) >= limit2:
                return False

            # Suite bathrooms: only connect to their matched bedroom (override zone compat)
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

            # Social bathrooms: connect to corridor (preferred) or social zone when no corridor
            # This must be checked BEFORE zone-compatibility to allow social↔bathroom pairing.
            if self._is_social_bathroom(room1.name) or self._is_social_bathroom(room2.name):
                if corridor:
                    return "circulation" in {zone1, zone2}
                return "social" in {zone1, zone2}

            # General zone compatibility for all other room pairs
            if self._ZONE_COMPATIBILITY.get((zone1, zone2), 0) < 0:
                return False

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
