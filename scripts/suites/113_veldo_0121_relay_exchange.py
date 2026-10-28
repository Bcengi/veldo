"""VELDO-0121: four independent exchange checks generated from one state model."""


def _v121_exchange():
    import importlib.util
    path = ROOT / 'scripts/fixtures/relay_exchange.py'
    spec = importlib.util.spec_from_file_location('relay_exchange121', path)
    fixture = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fixture)
    source = (ROOT / '.veldo/control_relay.py').read_text()
    report = fixture.qualify(source)
    copies_match = source == (ROOT / 'engine/.veldo/control_relay.py').read_text()
    for criterion, name in fixture.ROWS.items():
        expect('VELDO-0121 ' + criterion + ' ' + name,
               report['rows'][name] and copies_match)
    print('VELDO-0121 cells expected=%s executed=%s incomplete=%s valid=%s' % (
        report['expected'], report['executed'], report['incomplete'], report['valid']))
    if not all(report['rows'].values()):
        print('VELDO-0121 failed rows: %s' % [k for k, v in report['rows'].items() if not v])


_v121_exchange()
