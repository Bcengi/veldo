# VELDO-0188: open points

Written by the implementing agent on branch agent/claude/veldo-0188. Each point is either a place where the
specification and the code on main disagree, or a decision the owner has to make. Everything else in the
specification is built and checked by suite 113 (scripts/suites/113_veldo_0188_project_lines.py).

## 1. How faithful the AC1 rows are (REMAINING)

AC1's text asks the suite to run the INSTALLED service, activate a second project created through VELDO-0143's
provisioner and a third adopted through VELDO-0161, and require each first unit dispatched by the same process.
Suite 113 does something smaller:

- The authority service (control_service.Service) and its FactoryLoop run in the suite's own process over the
  VELDO-0152 fixture's store. The "same process" check is the loop object's identity and the pid across rows.
  The installed unit's ExecStart (control_service.py serve) is not started.
- Projects are activated by their owner's signed VELDO-0076 command. The provisioner (VELDO-0143) and the
  adoption effect (VELDO-0161) do not run. "Taken on" is simulated by setting what Service._take_on sets: the
  repository goes into service.repositories and its receiver configuration into
  config['receiver']['configs']. The store binding uses the real control_store.bind_repositories.
- The restart is a second Service and FactoryLoop over the same store, given the repositories the first one
  served. That stands in for serve's take_on() at start.
- The installation's receiver configuration (the one staffing reads) has adapters that name their engines. The
  Runner launches through a second configuration with the same adapter names and no engine binding, so the
  fake engine runs without a pinned binary or an account login. The account pool is bypassed: every line uses
  `fixture-account`. The author check uses the repository author configuration that VELDO-0143's own
  provisioner step writes (control_repository_creation.author) from the identity the store binds.

What a fully faithful row still needs: suite 110's provisioner and suite 109's adoption effect in front of a
served loop, with the installed service as its own process. Suite 110's fixture took about 10 minutes. Neither
suite is in this specification's footprint.

## 2. Where this keeps the work configuration's lines, against "the work configuration supplies a Line only for a served repository no project record names yet"

Followed strictly, the spec would turn existing suites on main red. Those suites are outside this footprint,
and the owner's rule 37191 says not to run them here. So the code keeps three kinds of earlier lines:

a. A repository the installed work configuration names keeps its line with the work configuration's roles
   whenever the store cannot staff it (no team and no default team, or a role that cannot be dispatched).
   Suite 83 (VELDO-0154) activates projects with no team on its configured repository and has no default team.
b. When the project of a repository the work configuration names is closed, that line offers nothing (no
   station, no re-run) but stays in the loop. Suite 110's activation/factory-canceled reads
   `canceled_loop.lines[REPO]` after the factory project is canceled.
c. VELDO-0143 gives a repository the service took on a line with the first line's roles. That happens through
   add_line, in the loop's constructor and in the new-project pass's activation. Such a line keeps its roles
   when the store cannot staff it AND its receiver adapters name no engine. Suites 92, 93 and 110 run receiver
   adapters with no `engine` field, which an installation's work check would refuse. Over adapters that do
   name engines, as VELDO-0185's setup writes them, the refusal stands: the line is set closing and the
   project is left without one. Suite 113's staff/refused-role and lines/restart rows check this.

Also, VELDO-0143's add_line in the new-project pass still adds a line outside a loop pass, immediately before
the journal pass it wakes. The next journal-woken pass then restages that line from the store.

Owner decision: accept a to c as they are, or extend this footprint to suites 83, 92, 93 and 110 (and to
proof/VELDO-0152/fixture.py where needed) so their fixtures name engines and stop reading a closed project's
line. After that, the three exceptions can be removed.

## 3. "the role's current capability configuration revision (VELDO-0162 AC1)"

This is read as the capability configuration reference the team role names: the revision that team revision
pins. VELDO-0185's work configuration does the same through the one shared function, control_team.line_roles.
It is not the head revision of that role's configuration. If the owner meant the head, line_roles would need
to read control_agent_config, and setup's work configuration would change with it.

## 4. Project cycles on the new lines (the second-registration risk)

The inventory flagged VELDO-0143 round 3: per-connection owners refuse a second registration. Because of that,
only the factory line builds project cycles. Suite 113 shows that units of the new projects are offered and
dispatched on their own lines. Each pass names `pm_cycles:deferred_to_factory_line` for every other line, as
on main. VELDO-0188's criteria do not ask for cycles on the new lines. Making them run there is the unlanded
multirepo PM-services decision (branch spec-veldo-multirepo), which this work does not touch.

## 5. Consumer suites not run here

These consumer suites were not run (owner rule 37191). The batch gate has to judge them: 83 (VELDO-0154),
86_veldo_0148, 86_veldo_0189, 92, 93, 96 (VELDO-0204), 106 (VELDO-0185) and 110 (VELDO-0143). Suite 106 is
affected because control_factory_setup_dispatch.work now calls control_team.line_roles. The output is the same
by construction, and suite 113's staff/one-mapping row compares the two.
