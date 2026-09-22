"""Sheet and column definitions for lab-data.xlsx.

kind:
  id       unique ID (format-checked, duplicates highlighted red)
  text     free text
  textfmt  free text forced to text format (serials, asset tags)
  int      whole number >= 0 (cm, W, kg, counts)
  pct      whole number 0-100
  date     date
  list:X   dropdown from lists sheet, strict
  listw:X  dropdown from lists sheet, other values allowed with a warning
  ref:S    dropdown of IDs from sheet S; red if that ID doesn't exist
"""


def col(name, hint="", help="", req=False, kind="text", width=None):
    return dict(name=name, hint=hint, help=help, req=req, kind=kind, width=width)


ROOMS = [
    col("id", "e.g. LAB-A", "Unique room ID. Uppercase letters, digits, - and . only. Goes on the door label.", True, "id", 12),
    col("name", "human name", "", True, "text", 30),
    col("building", "", "", False, "text", 14),
    col("floor", "", "", False, "textfmt", 8),
    col("width", "cm, left-right (x)", "Overall interior size along the drawing's x axis (left to right), cm. Irregular room: its bounding box.", True, "int", 11),
    col("depth", "cm, top-bottom (y)", "Overall interior size along the drawing's y axis (top to bottom), cm. Irregular room: its bounding box.", True, "int", 11),
    col("ceiling", "cm", "Floor-to-ceiling height, cm. If it varies (beams, ducts), the lowest point.", True, "int", 10),
    col("shell", "file in rooms/", "Filename of the hand-drawn room outline in the rooms/ folder, e.g. LAB-A.svg.", True, "text", 14),
    col("cooling", "W, if known", "Cooling capacity of the room's HVAC in W, if facilities know it. Compared against the total equipment heat load.", False, "int", 10),
    col("sprinklers", "yes/no", "Sprinkler heads in the ceiling? Then nothing may reach higher than sprinkler_clearance (settings) below the ceiling.", False, "list:yesno", 10),
    col("notes", "", "", False, "text", 40),
]

PLACEABLES = [
    col("id", "BENCH-04, PED-01.D2", "Unique ID, printed on the physical label. Must NOT encode location: things move. Parts and drawers: PARENT.suffix, e.g. BENCH-04.A, PED-01.D2. Never reuse an ID.", True, "id", 14),
    col("name", "what people call it", "", True, "text", 30),
    col("category", "dropdown", "What kind of thing it is (lists sheet). Drives sensible defaults in the checks.", True, "list:category", 13),
    col("room", "dropdown", "The room it's in. Required on every row, children too, so you can filter by room.", True, "ref:rooms", 10),
    col("parent", "blank = in the room", "Blank for things standing in, or mounted on, the room itself. Otherwise the ID of what it sits on, under, in, or is part of.", False, "ref:placeables", 13),
    col("mount", "dropdown", "floor = stands on the floor. wall = fixed to a wall at height z. on = on top of parent. under = on the floor beneath parent (under-bench fridge, PC tower, pedestal); must be no taller than the parent's free_under. in = inside parent, no position (drawer, cabinet shelf). part = piece of a composed parent (bench legs).", True, "list:mount", 8),
    col("x", "cm, parent frame", "Parent origin to the nearest corner of this footprint, cm. In a room: from the left edge of the drawing. On a bench: from the bench's left end as you face it. Diagonal objects: the corner of their bounding box, so they're easier to drag in. Blank = not placed yet.", False, "int", 8),
    col("y", "cm, parent frame", "In a room: from the top edge of the drawing. On a bench: from the bench's back edge. Blank = not placed yet.", False, "int", 8),
    col("z", "cm, wall mounts", "Height of the underside above the floor, cm. Required for mount = wall; otherwise leave blank (floor = 0, on = top of parent).", False, "int", 8),
    col("faces", "blank = S", "Which way the front (the side you use) points: N, NE, E, SE, S, SW, W or NW. Diagonals are for pieces along a chamfered corner. In a room: N = top of the drawing, not compass north. For children it's relative to the parent: blank = same way as the parent.", False, "list:faces", 7),
    col("shape", "blank = rect", "rect (default), circle (w = diameter), group (composed: its 'part' children carry the geometry), or @name for a profile drawn in shapes/name.svg.", False, "listw:shape", 11),
    col("w", "cm, along front", "Width along the front face. Circle: diameter. Drawers/shelves (mount = in): internal usable width. Blank for groups.", False, "int", 8),
    col("d", "cm, front-back", "Depth front to back. Circle: same as w. Drawers/shelves: internal usable depth.", False, "int", 8),
    col("h", "cm", "Height. Drawers/shelves: internal usable height. Workspace: headroom needed above the bench.", False, "int", 8),
    col("free_under", "cm clear below", "Tables, desks and open-frame benches: clear height underneath, from the floor to the underside of the top or its rail. Anything up to that height can go under it. Blank = solid to the floor (cupboard base, instrument).", False, "int", 9),
    col("inner_w", "cm, inside", "Fume hoods, biosafety cabinets, gloveboxes, ovens: the working space inside, width along the front. Assumed centred left to right and flush with the front (the sash). Things can then be placed in it (mount = in, with x and y).", False, "int", 8),
    col("inner_d", "cm, inside", "Working space inside, front to back: from the sash to the rear baffle.", False, "int", 8),
    col("inner_h", "cm, inside", "Working space inside, height above the work surface (up to the sash opening, for a fume hood).", False, "int", 8),
    col("inner_z", "cm, work surface", "Height of the inside work surface above the floor (above the object's underside), cm.", False, "int", 8),
    col("clear_front", "cm", "Must stay free in front: standing room, drawer pull-out, door swing. Applies in the plane it sits in: bench surface for things on a bench, floor for things on the floor.", False, "int", 8),
    col("clear_back", "cm", "Behind: ventilation, cables, hoses.", False, "int", 8),
    col("clear_left", "cm, your left", "To your left as you face the front: hinge side, vents, access panels.", False, "int", 8),
    col("clear_right", "cm, your right", "To your right as you face the front.", False, "int", 8),
    col("clear_top", "cm, lids", "Headroom above: lids that open upwards, sashes, hot exhaust. Checked against shelves and the ceiling.", False, "int", 8),
    col("door", "hinge side", "Fridges, freezers, cabinets: which side the door is hinged on, as you face the front (left, right, both = double doors). The swing is kept clear in front, and door_gap (settings) beside the hinge so it opens fully.", False, "list:door", 8),
    col("fixed", "yes = can't move", "yes = plumbing, structure or safety equipment. The layout must work around it.", False, "list:yesno", 7),
    col("mobile", "yes = wheels", "yes = carts, pedestals on castors. Its position is its parking spot.", False, "list:yesno", 7),
    col("stackable", "things on top?", "May other things sit on top? Blank = category default (bench, desk, table, shelf, cabinet, cart: yes; the rest: no).", False, "list:yesno", 9),
    col("fill", "% full", "Containers only (drawer, shelf, cabinet, box): how full, 0-100, eyeballed. Finds consolidation opportunities.", False, "pct", 7),
    col("checked", "date", "Containers: date the contents were last verified against the items sheet. Shown in the directory.", False, "date", 11),
    col("decommissioned", "date it left", "Filled = it's gone. The row stays as a record (with its equipment row: asset tag, serial), but it's left out of the maps, the checks, the layout and the search. Its drawers and parts go with it. Anything still pointing at it is flagged, so nothing is left behind. Never reuse the ID.", False, "date", 12),
    col("tags", "tags; separated; by ;", "What it is or does, for the keep_apart sheet: vibrates, vibration-sensitive, emits-light, needs-dark, emi-source, emi-sensitive, heat-source, heat-sensitive, ignition-source, flammable, oxidiser, high-voltage, noisy, quiet. Its category counts as a tag too.", False, "text", 18),
    col("notes", "", "", False, "text", 40),
]

EQUIPMENT = [
    col("id", "placeable ID", "Must exist on the placeables sheet. One row per piece of equipment: anything with a plug, a booking, a serial number or an owner. Benches and drawers don't need a row.", True, "ref:placeables", 14),
    col("maker", "", "", False, "text", 16),
    col("model", "", "", False, "text", 16),
    col("serial", "stored as text", "Stored as text so Excel doesn't mangle long numbers.", False, "textfmt", 14),
    col("asset_tag", "stored as text", "Your institution's inventory number, if any. Stored as text so leading zeros survive.", False, "textfmt", 12),
    col("owner", "person or group", "Who is responsible for it / who to ask.", False, "text", 16),
    col("condition", "dropdown", "", False, "list:condition", 10),
    col("plan", "dropdown", "What happens to it in the reorganisation. Fill this FIRST: removing things beats rearranging them. new = arriving, needs a spot.", False, "list:plan", 10),
    col("usage", "dropdown", "How often it is actually used.", False, "list:usage", 9),
    col("usage_source", "dropdown", "How you know. tally = tally sheet on the instrument; booking = booking system or logs; estimate = someone's guess (least reliable).", False, "list:usage_source", 10),
    col("workflow", "group tag", "Free tag for things that should stay near each other, e.g. sample-prep, imaging. The check reports how spread out each group is.", False, "text", 13),
    col("plugs", "count", "Number of mains plugs. Separately plugged units with their own footprint (pump, chiller) should be their own placeables.", False, "int", 7),
    col("plug_type", "dropdown", "", False, "listw:plug_type", 11),
    col("watts_typ", "W, typical", "Typical running power, W. If the nameplate only gives amps: W = V x A.", False, "int", 9),
    col("watts_max", "W, peak", "Nameplate or peak power, W. Motors and compressors spike at start-up.", False, "int", 9),
    col("volts", "V", "", False, "int", 7),
    col("critical", "yes = never off", "yes = must never lose power: freezers, incubators, long unattended runs. Flagged if it shares a circuit or RCD with heavy, intermittent loads.", False, "list:yesno", 9),
    col("weight", "kg, optional", "For information only: shown in the directory, handy for moving day. Leave blank if you don't know.", False, "int", 8),
    col("outlet", "blank = nearest", "Outlet or strip it's plugged into (services sheet). Blank = the check assumes the nearest one.", False, "ref:services", 11),
    col("needs", "exhaust; gas:N2; ...", "Services other than power it needs within utility_reach (settings), separated by ;: gas, vacuum, air, water, drain, network, exhaust. Add :medium to be specific, e.g. gas:N2. A link on the links sheet (gas-line, water-line, exhaust, ethernet) also counts.", False, "text", 16),
    col("manual", "link or path", "", False, "text", 20),
    col("notes", "", "", False, "text", 40),
]

SERVICES = [
    col("id", "OUT-01, STRIP-01", "Unique ID. Put it on a label next to the socket/tap too.", True, "id", 12),
    col("type", "dropdown", "", True, "list:service_type", 10),
    col("room", "dropdown", "", True, "ref:rooms", 10),
    col("parent", "blank = on a wall", "Blank = fixed to the room (wall, floor, ceiling). Otherwise the placeable it's mounted on, e.g. a bench service spine; it then moves with that bench.", False, "ref:placeables", 13),
    col("x", "cm, parent frame", "Same frame as placeables: in a room from the drawing's left edge; on a bench from its left end as you face it.", False, "int", 8),
    col("y", "cm, parent frame", "In a room from the drawing's top edge; on a bench from its back edge.", False, "int", 8),
    col("z", "cm above floor", "", False, "int", 8),
    col("circuit", "outlets", "Circuit ID from the circuits sheet. Outlets only: strips inherit it from fed_by.", False, "ref:circuits", 11),
    col("fed_by", "strips", "Power strips: the outlet (or strip) it's plugged into. Strip-into-strip gets flagged.", False, "ref:services", 11),
    col("sockets", "count", "", False, "int", 8),
    col("rating_a", "A, strips/sockets", "Most current the socket or strip may carry, amps (often 13 A for a strip, 16 A or 10 A for a socket). A UPS: its VA rating ÷ volts. Blank = not checked; the circuit still is.", False, "int", 9),
    col("socket_type", "dropdown", "", False, "listw:plug_type", 11),
    col("medium", "gas taps etc.", "What comes out: N2, Ar, compressed air, vacuum, DI water, 10 GbE...", False, "text", 12),
    col("notes", "", "", False, "text", 40),
]

CIRCUITS = [
    col("id", "e.g. DB2-C07", "Circuit ID as written on the distribution board, prefixed with the board name.", True, "id", 12),
    col("panel", "board name", "", True, "text", 12),
    col("rating_a", "A", "Breaker rating, amps.", True, "int", 9),
    col("volts", "V", "", True, "int", 7),
    col("phase", "1 or 3", "", False, "list:phase", 7),
    col("rcd", "yes/no", "Protected by an RCD/GFCI? One trip takes out everything on it.", False, "list:yesno", 7),
    col("backed", "dropdown", "none, ups or generator.", False, "list:backed", 10),
    col("notes", "", "", False, "text", 40),
]

LINKS = [
    col("from", "ID", "Usually the computer or supply end (PC, gas cylinder, chiller).", True, "ref:placeables", 13),
    col("to", "ID", "The instrument / consumer end.", True, "ref:placeables", 13),
    col("type", "dropdown", "", True, "list:link_type", 11),
    col("max_len", "cm, blank = default", "Longest cable or tubing that works for this link, cm. Blank = default for the type (lists sheet).", False, "int", 10),
    col("notes", "", "", False, "text", 40),
]

ITEMS = [
    col("id", "I-0001", "Just number them. Not printed on labels; used to name photos (photos/I-0001.jpg).", True, "id", 9),
    col("name", "what people call it", "", True, "text", 32),
    col("synonyms", "other names; separated; by ;", "Every other name people might search for: slang, brand names, other languages. This is what makes search work.", False, "text", 32),
    col("container", "drawer/shelf/box ID", "Where it lives: ID of a drawer, shelf, cabinet or box on the placeables sheet. Blank if it's kept outside these labs: fill elsewhere instead.", False, "ref:placeables", 14),
    col("elsewhere", "if not in these labs", "Only for things kept outside the mapped rooms, e.g. Main stores, cage 3. Shown as the location instead of a map.", False, "text", 20),
    col("qty", "optional", "Anything goes: 3, ~20, 2 boxes. For a required spare (min_qty filled), the first number is the stock count, and blank counts as none.", False, "text", 9),
    col("min_qty", "spares: keep at least", "Fill this to make it a required spare: fewer in stock gives a warning, none in stock a louder one. Blank = not tracked.", False, "int", 10),
    col("category", "dropdown", "", False, "list:item_category", 12),
    col("spare_for", "IDs; separated; by ;", "Equipment this is a spare or replacement part for, separated by ;. It's listed under Spare parts on each of their pages.", False, "text", 16),
    col("rs_part", "e.g. 123-4567", "RS Components stock number. The directory turns it into a link to RS.", False, "textfmt", 11),
    col("buy_link", "URL", "Where to order it from, if not RS (or as well): a supplier or manufacturer page.", False, "text", 30),
    col("owner", "", "", False, "text", 14),
    col("notes", "", "", False, "text", 40),
]

DOCUMENTS = [
    col("id", "COSHH-014, RA-003", "Unique ID, e.g. the form's own reference number.", True, "id", 13),
    col("type", "dropdown", "", True, "list:doc_type", 15),
    col("title", "", "", False, "text", 34),
    col("applies_to", "IDs; separated; by ;", "Everything it covers: equipment, benches, rooms or sockets, separated by ;. It shows on each of their pages.", True, "text", 22),
    col("status", "dropdown", "Anything other than approved is flagged as a warning.", True, "list:doc_status", 11),
    col("filled", "date", "When it was filled in or last reviewed.", False, "date", 11),
    col("expires", "date", "When it runs out. Past it = problem; within expiry_warning_days (settings) = warning.", False, "date", 11),
    col("approved_by", "", "", False, "text", 16),
    col("link", "URL or full file path", "Where the form itself lives: a web link, or a full path to a file on a shared drive.", False, "text", 40),
    col("notes", "", "", False, "text", 30),
]

KEEP_APART = [
    col("tag", "e.g. vibrates", "A tag used in the tags column of the placeables sheet, or a category (laser, door...).", True, "text", 22),
    col("away_from", "e.g. vibration-sensitive", "The tag it has to be kept away from.", True, "text", 22),
    col("distance", "cm", "Closest the two may be, edge to edge on the plan, cm.", True, "int", 9),
    col("level", "dropdown", "problem or warning.", True, "list:level", 9),
    col("why", "", "Shown in the report.", False, "text", 60),
]
DEFAULT_ROWS = {  # rows the empty template starts with too
    "keep_apart": [
        dict(tag="vibrates", away_from="vibration-sensitive", distance=100, level="warning",
             why="vacuum pumps, chillers and compressors shake probe stations, balances, microscopes and optics"),
        dict(tag="emits-light", away_from="needs-dark", distance=200, level="warning",
             why="stray light from solar simulators, lasers and lamps spoils dark and low-light measurements "
                 "(dark I-V, PL, EQE): keep apart, or behind curtains or in a dark box"),
        dict(tag="laser", away_from="door", distance=150, level="warning",
             why="class 3B / 4 beams away from doorways, or behind interlocked curtains"),
        dict(tag="emi-source", away_from="emi-sensitive", distance=150, level="warning",
             why="motors, RF and high-voltage supplies couple noise into low-current measurements"),
        dict(tag="ignition-source", away_from="flammable", distance=300, level="problem",
             why="hotplates, furnaces, sparks and high voltage (corona) away from solvents"),
        dict(tag="flammable", away_from="oxidiser", distance=300, level="problem",
             why="flammables and oxidisers are stored apart, or in separate cabinets"),
        dict(tag="heat-source", away_from="heat-sensitive", distance=50, level="warning",
             why="samples, gloveboxes and fridges struggle next to furnaces, hotplates and lamp housings"),
        dict(tag="noisy", away_from="quiet", distance=200, level="warning",
             why="desks and write-up areas away from pumps and compressors"),
    ],
}

# name, tab colour, freeze cell, rows to format, columns, collection pass
SHEETS = [
    ("rooms", "7F7F7F", "B3", 100, ROOMS, "Pass 1 - rooms"),
    ("placeables", "1F4E79", "C3", 1500, PLACEABLES, "Pass 2 - tape measure"),
    ("equipment", "2E75B6", "B3", 1000, EQUIPMENT, "Pass 0 + 3 - triage, nameplates"),
    ("services", "C55A11", "B3", 1000, SERVICES, "Pass 4 - sockets and taps"),
    ("circuits", "BF9000", "B3", 300, CIRCUITS, "Pass 4 - distribution board"),
    ("links", "548235", "C3", 500, LINKS, "Pass 5 - connections"),
    ("items", "7030A0", "C3", 5000, ITEMS, "Pass 6 - drawers"),
    ("documents", "B42318", "B3", 500, DOCUMENTS, "Any time - forms and certificates"),
    ("keep_apart", "595959", "A3", 100, KEEP_APART, "Rules - what to keep apart"),
]
