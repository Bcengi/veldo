# StationStrip and LineLamps

`StationStrip` shows where the unit is on the line: Ready, Claimed, Dispatch, Build, Verify, Review,
Land, Done (from the unit's `execution_unit` state), one lamp per station, the current one lit
(`live` while the run runs, `here` otherwise, `done` when completed), with the dispatch's station
(build, review, coordination) named below. States off the line (Failed, Canceled, Waiting on
authority) are named with a stop or waiting lamp. On a phone the station names collapse to lamps and
one "At Build" caption.

`LineLamps` is the same in miniature for list rows (8 px dots, `role="img"` named "At Build").

Props: `unitState` (string or null), `station` (strip only), `live` (boolean).
