# The lab directory

[← Back to the README](../README.md)

```
python -m labmap site         # builds build/site/ (or double-click site.bat)
```

Copy the whole `build/site` folder to a shared drive; people open `index.html` in any browser. It needs no
server and no internet. It has:

- **Search** across items (and their synonyms and RS numbers), objects, sockets and the text of every SOP. Searching "allen key"
  finds the hex key set and says it's in `LAB-A › BENCH-04 › BENCH-04.A › PED-01 › PED-01.D2`.
- **A page per object**: its photo, where it is, a map with it highlighted, its reference photo ("how it should
  look"), what's on, under and in it, the items kept there, equipment details (owner, usage, which socket and
  circuit it's on), its SOPs, its forms and certificates with their status and expiry, its spare parts with stock
  and where to order them (RS number or supplier link), and what it's connected to.
- **Where it is, at a glance**: every object, drawer and socket page has a red *Show on map* button at the top.
  The map marks the spot with a pulsing red pin, an arrow and its name, drawn above everything else so a drawer
  under a bench is still easy to find, and the object itself flashes. Arriving from a search, the item's row
  flashes too. (With *reduce motion* switched on in Windows, nothing moves.)
- **Maps you can point at**: hovering highlights the object under the mouse (the innermost one, not the bench it
  stands on) and names it; clicking opens its page. Labels stay upright, fully inside their object with a margin,
  clear of each other and of whatever stands on top; each one is moved around its object before it's made
  smaller, and one that can't be shown at a readable size is left off (hover to see it).
- **Level views** above every map: *Everything*, *Floor* (what stands on the floor, including what's under the
  benches), *Bench tops* (benches, tables, desks and what stands on them) and *Walls and shelves* (wall-mounted
  things, and anything starting 120 cm up). The other levels fade and can't be clicked, so a freezer under a
  bench with an instrument on top can be picked in *Floor*. Each level gets its own labels. An object's page
  opens on its own level; otherwise the last one you picked is remembered. The check report has the same switch.
- **Sockets and taps** button next to the level views: shows every socket, strip, network port and gas, water or
  vacuum tap on the plan, with a dashed line from each device to what it's plugged into. A socket's number is how
  many are still free (green free, amber full, red "+2" = two plugs too many); taps and ports are circles with a
  letter (G gas, W water, V vacuum, A air, N network…). Hover over one to see its circuit and what it feeds; the
  lines light up. Click it to open its page, which opens with the sockets shown. Sockets without an x and y aren't
  drawn. The check report has the same button.
- **A page per socket, strip or tap** (which circuit, what's plugged in), per room (a clickable plan) and per SOP
  (with `[[ID]]` links working).
- A copy of the check report.

Photos are shrunk copies (your originals in `photos/` are never changed). Rebuild the site whenever the
spreadsheet, SOPs or photos change.
