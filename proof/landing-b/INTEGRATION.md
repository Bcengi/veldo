# landing-b integration fixes

- VELDO-0254 x VELDO-0259: proof/VELDO-0254/fix-round-1-red-before.txt line 15 wrote the home directory in full; rewritten as "~" so 0259's personal-setup stage passes the merged evidence.
- VELDO-0247 x VELDO-0259: proof/VELDO-0247/suite-101_veldo_0208_landing_reuse.txt traceback lines wrote the home directory in full (6 lines); rewritten as "~" for 0259's personal-setup stage.
- VELDO-0127 x VELDO-0259 (via VELDO-0254's recapture): the retaken live captures name the capture's run directory under /run/user/<login uid>, which 0259's login_uid shape refuses; the uid is written as UID (/run/user/UID/) in both captures, evidence.problems judged identical before and after (none), qualify reproduced every file unchanged (qualify-output.txt, live-capture-output.txt).
- VELDO-0260 x VELDO-0241: suite 129_veldo_0260_checkout_in_step stubbed Line.service without domain, which 0241's workflow-revision Line.next (Line.process) reads; the stub now carries domain=DOMAIN (18 rows raised AttributeError; 44 of 44 after).
