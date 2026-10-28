# StationStrip and LineLamps

`StationStrip` shows where the unit is on the line: Ready, Claimed, Dispatch, Build, Verify, Review,
Land, Done (from the unit's `execution_unit` state), one lamp per station joined by a line, the current
one lit (`live` while the run runs, `here` otherwise, `done` at Done) and named in bold. States off the
line (Failed, Canceled, Waiting on authority) are named beside it with a stop or waiting lamp. Below
1100 px it is one line: the lamps, and only the current station's name (the others keep their names for
screen readers). The dispatch's own station (build, review) is in the run's headline, not here.

`LineLamps` is the same in miniature for list rows (8 px dots, `role="img"` named "At Build", "Done" or
"Off the line: Failed"), with the current station's name beside it.

Props: `unitState` (string or null), `station` (strip only), `live` (boolean).
