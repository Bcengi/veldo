"""Observe the real stop's call boundary in suite 63's installed receiver copy.

A group-wide step cannot succeed without invoking its group operation. Waiting for
its runtime cap after that omission hides a conclusive failure behind an unrelated
timer. Forward every operation unchanged, then fail at the step's return event.
Only the fixture installs this observer; production never imports it.
"""


def observe_stop_boundary(stop_class):
    original = stop_class._step

    def step(self, stage, now):
        if stage not in ('terminate', 'kill'):
            return original(self, stage, now)
        group = self.group
        operation = getattr(group, stage)
        called = []
        # Preserve the instance's original attribute shape as well as its method.
        previous = vars(group).get(stage)
        had_own = stage in vars(group)

        def forward(*args, **kwargs):
            called.append(stage)
            return operation(*args, **kwargs)

        setattr(group, stage, forward)
        try:
            result = original(self, stage, now)
        finally:
            if had_own:
                setattr(group, stage, previous)
            else:
                delattr(group, stage)
        if not called:
            raise AssertionError('containment stop completed %s without the group operation' % stage)
        return result

    stop_class._step = step
