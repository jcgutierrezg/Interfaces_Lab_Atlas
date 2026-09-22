"""Services, circuits and links. Whole cm."""


def S(id, type, room, x, y, z, parent=None, **kw):
    return dict(id=id, type=type, room=room, parent=parent, x=x, y=y, z=z, **kw)


def O(id, room, x, y, z, circuit, sockets, parent=None, notes=None):
    return S(id, "outlet", room, x, y, z, parent, circuit=circuit, sockets=sockets, socket_type="standard",
             notes=notes)


SERVICES = [
    # --- LAB-A ---
    O("OUT-01", "LAB-A", 120, 0, 105, "DB2-C07", 2, notes="above the corner bench"),
    O("OUT-02", "LAB-A", 90, 0, 100, "DB2-C08", 4, parent="BENCH-02",
      notes="on the bench service spine: moves with BENCH-02"),
    O("OUT-03", "LAB-A", 75, 540, 30, "DB2-C09", 1, notes="dedicated freezer socket"),
    O("OUT-04", "LAB-A", 360, 540, 30, "DB2-C07", 2, notes="behind the desk"),
    O("OUT-05", "LAB-A", 140, 10, 100, "DB2-C10", 4, parent="HOOD-01", notes="fume hood service panel"),
    O("OUT-06", "LAB-A", 560, 0, 105, "DB2-C10", 4, notes="above the sink bench"),
    O("OUT-07", "LAB-A", 90, 45, 0, "DB2-C11", 2, parent="TBL-01", notes="floor box under the table"),
    S("STRIP-01", "strip", "LAB-A", 20, 5, 0, parent="DESK-01", fed_by="OUT-04", sockets=6,
      socket_type="standard", notes="under the desk"),
    S("STRIP-05", "strip", "LAB-A", 110, 45, 0, parent="TBL-01", fed_by="OUT-07", sockets=6,
      socket_type="standard", notes="table strip for the microscope and the SMU stack"),
    S("NET-01", "network", "LAB-A", 340, 540, 30, sockets=2, medium="1 GbE"),
    # --- LAB-B ---
    O("OUT-08", "LAB-B", 200, 0, 105, "DB3-C01", 4, notes="above the optics bench"),
    O("OUT-09", "LAB-B", 560, 0, 105, "DB3-C02", 4, notes="UPS-backed, above the solar simulator"),
    O("OUT-10", "LAB-B", 100, 0, 100, "DB3-C03", 2, parent="BENCH-11.C", notes="bench service spine"),
    O("OUT-11", "LAB-B", 60, 0, 130, "DB3-C04", 4, parent="BENCH-13.B", notes="on the raised tier"),
    O("OUT-12", "LAB-B", 20, 0, 100, "DB3-C01", 4, parent="BENCH-14.C", notes="island service spine"),
    O("OUT-13", "LAB-B", 200, 600, 30, "DB3-C05", 2, notes="by the write-up table"),
    S("STRIP-02", "strip", "LAB-B", 50, 10, 0, parent="BENCH-11.A", fed_by="OUT-09", sockets=6,
      socket_type="standard", notes="under the measurement bench"),
    S("STRIP-03", "strip", "LAB-B", 20, 10, 0, parent="BENCH-11.C", fed_by="STRIP-02", sockets=4,
      socket_type="standard", notes="EXAMPLE PROBLEM: plugged into another strip"),
    S("STRIP-04", "strip", "LAB-B", 120, 10, 0, parent="BENCH-13.A", fed_by="OUT-11", sockets=6,
      socket_type="standard", notes="under the cryostat bench"),
    S("NET-02", "network", "LAB-B", 300, 0, 30, sockets=2, medium="1 GbE"),
    S("NET-03", "network", "LAB-B", 620, 0, 30, sockets=4, medium="1 GbE"),
]


def C(id, backed="none", notes=None):
    return dict(id=id, panel=id.split("-")[0].replace("DB", "DB-"), rating_a=16, volts=230, phase=1, rcd="yes",
                backed=backed, notes=notes)


CIRCUITS = [
    C("DB2-C07", notes="sockets on the top and bottom walls"),
    C("DB2-C08", notes="window bench spine"),
    C("DB2-C09", "generator", "dedicated freezer circuit"),
    C("DB2-C10", notes="hood panel and sink bench"),
    C("DB2-C11", notes="table floor box"),
    C("DB3-C01", notes="optics bench and island"),
    C("DB3-C02", "ups", "measurement bench, on the building UPS"),
    C("DB3-C03", notes="right-hand bench spine"),
    C("DB3-C04", notes="cryostat bench"),
    C("DB3-C05", notes="write-up area"),
]


def L(a, b, type, max_len=None, notes=None):
    return {"from": a, "to": b, "type": type, "max_len": max_len, "notes": notes}


LINKS = [
    L("PC-01", "SPEC-01", "usb", 500, "EXAMPLE PROBLEM: about 8 m of cable by any sensible route"),
    L("PC-01", "BAL-01", "serial", notes="blank max_len = type default (15 m)"),
    L("PC-01", "MON-01", "video"),
    L("GAS-01", "HOOD-01", "gas-line", 1000, "links are not only cables: tubing counts too"),
    L("LAP-02", "MIC-01", "usb"),
    L("LAP-02", "SMU-01", "usb"),
    L("SMU-01", "SMU-02", "gpib", notes="GPIB daisy chain"),
    L("SMU-02", "SMU-03", "gpib", notes="GPIB daisy chain"),
    L("PC-02", "PRB-01", "triax", notes="low-current measurement leads to the probes"),
    L("PC-02", "SUN-01", "usb"),
    L("PC-02", "MON-02", "video"),
    L("VAC-02", "PRB-01", "vacuum-line", 300, "vacuum chuck"),
    L("N2G-01", "GB-01", "gas-line", 1500, "for the glovebox when it arrives"),
    L("LAS-01", "PRB-01", "fiber", notes="laser light to the probe station"),
    L("PC-03", "CRYO-01", "ethernet"),
    L("PC-03", "MON-03", "video"),
    L("GAS-03", "CRYO-01", "gas-line", 1000, "helium for the cold head"),
    L("GAS-04", "CRYO-01", "gas-line", 1000, "N2 purge of the window"),
    L("LAP-01", "FTIR-01", "usb"),
]
