"""Row helpers shared by the example data modules (all lengths in whole cm)."""
from datetime import date

D = date(2026, 9, 21)


def P(id, name, category, room, parent, mount, **kw):
    return dict(id=id, name=name, category=category, room=room, parent=parent, mount=mount, **kw)


def E(id, maker, model, owner, condition, plan, usage, source, workflow, plugs, plug_type, wt, wm, **kw):
    return dict(id=id, maker=maker, model=model, owner=owner, condition=condition, plan=plan, usage=usage,
                usage_source=source, workflow=workflow, plugs=plugs, plug_type=plug_type, watts_typ=wt,
                watts_max=wm, volts=230 if plug_type == "standard" else None, **kw)
